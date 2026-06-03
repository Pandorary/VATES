"""Save Claude Code session transcript in /export format to .claude/logs/.

时间去重：如果最近 MIN_EXPORT_INTERVAL_MINUTES 分钟内已导出过，跳过。
设为 0 则每次都导出。
"""
import glob
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

MAX_TOOL_RESULT_LENGTH = 3000
MAX_TEXT_BLOCK_LENGTH = 50000
MIN_EXPORT_INTERVAL_MINUTES = 30  # 0 = 每次都导出

# Patterns to strip from user messages
STRIP_PATTERNS = [
    re.compile(r'<local-command-caveat>.*?</local-command-caveat>', re.DOTALL),
    re.compile(r'<command-name>[^<]*</command-name>'),
    re.compile(r'<command-message>[^<]*</command-message>'),
    re.compile(r'<command-args>[^<]*</command-args>'),
    re.compile(r'<local-command-stdout>.*?</local-command-stdout>', re.DOTALL),
    re.compile(r'<system-reminder>.*?</system-reminder>', re.DOTALL),
]

SKIP_TYPES = {
    "file-history-snapshot",
    "system",
}

SKIP_SUBTYPES = {
    "local_command",
    "stop_hook_summary",
    "turn_duration",
}


def strip_tags(text: str) -> str:
    for p in STRIP_PATTERNS:
        text = p.sub('', text)
    return text.strip()


def truncate(text: str, max_len: int = MAX_TOOL_RESULT_LENGTH) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + f"\n\n... [truncated, {len(text) - max_len} more chars]"


def tool_summary(name: str, inp: dict) -> str:
    """Short summary of tool input for display."""
    if name == "Read":
        fp = inp.get("file_path", "")
        return f"Read({fp})"
    elif name == "Write":
        fp = inp.get("file_path", "")
        return f"Write({fp})"
    elif name == "Edit":
        fp = inp.get("file_path", "")
        return f"Edit({fp})"
    elif name == "Bash":
        cmd = inp.get("command", "")
        desc = inp.get("description", cmd[:60])
        return f"Bash({desc})"
    elif name == "Grep":
        return f"Grep({inp.get('pattern', '')})"
    elif name == "Glob":
        return f"Glob({inp.get('pattern', '')})"
    elif name == "WebFetch":
        return f"WebFetch({inp.get('url', '')})"
    elif name == "WebSearch":
        return f"WebSearch({inp.get('query', '')})"
    elif name == "Agent":
        return f"Agent({inp.get('description', '')})"
    elif name == "Task":
        return f"Task({inp.get('subagent_type', '')})"
    else:
        return f"{name}"


def format_tool_result(block: dict) -> str:
    """Format a tool_result block."""
    content = block.get("content", "")
    if isinstance(content, list):
        content = "\n".join(str(c) for c in content)
    return truncate(str(content))


def convert_jsonl_to_export(src_path: str, dst_path: str) -> None:
    with open(src_path, encoding="utf-8") as f_src:
        lines = f_src.readlines()

    lines_out = []
    tool_use_map = {}  # tool_use_id -> name/summary
    version = ""

    def emit(line: str = ""):
        lines_out.append(line)

    for raw in lines:
        try:
            d = json.loads(raw)
        except json.JSONDecodeError:
            continue

        msg_type = d.get("type", "")
        subtype = d.get("subtype", "")

        # Track version from any message
        if d.get("version") and not version:
            version = d["version"]

        # Skip internal/meta types
        if msg_type in SKIP_TYPES:
            continue
        if msg_type == "system" and subtype in SKIP_SUBTYPES:
            continue

        # Skip meta user messages (command echo, caveats, etc.)
        if d.get("isMeta"):
            continue

        # --- USER messages ---
        if msg_type == "user":
            content = d.get("message", {}).get("content", "")

            # Content may be a string (plain text) or list (tool_result blocks)
            if isinstance(content, list):
                for block in content:
                    if block.get("type") == "tool_result":
                        tool_id = block.get("tool_use_id", "")
                        tool_name = tool_use_map.pop(tool_id, "?")
                        result = format_tool_result(block)
                        if result:
                            emit(f"  ⎿  Done ({tool_name})")
                            if len(result) < 500:
                                emit(f"     {result[:200]}")
                    # skip other user block types
                continue

            # Plain text user message
            text = strip_tags(str(content))
            if not text:
                continue

            emit(f"\n> {text}\n")

        # --- ASSISTANT messages ---
        elif msg_type == "assistant":
            blocks = d.get("message", {}).get("content", [])
            if not isinstance(blocks, list):
                continue

            for block in blocks:
                btype = block.get("type", "")

                if btype == "thinking":
                    # Show placeholder like the UI does
                    sig = block.get("signature", "")[:12]
                    emit(f"  (thinking... {sig}... ctrl+o to expand)")

                elif btype == "tool_use":
                    name = block.get("name", "?")
                    tid = block.get("id", "")
                    inp = block.get("input", {})
                    summary = tool_summary(name, inp)
                    tool_use_map[tid] = summary
                    emit(f"\n● {summary}")

                elif btype == "text":
                    text = block.get("text", "")
                    if text:
                        text = truncate(text, MAX_TEXT_BLOCK_LENGTH)
                        # Add ● prefix to first line, indent continuation
                        for i, line in enumerate(text.split("\n")):
                            if i == 0:
                                emit(f"\n● {line}")
                            else:
                                emit(f"  {line}")

    # Write header + body
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(dst_path, "w", encoding="utf-8") as f_out:
        f_out.write(f"╭─── Claude Code {version} ───────────────────────────────────────────────╮\n")
        f_out.write(f"│ Session exported: {ts}                                                  │\n")
        f_out.write(f"╰──────────────────────────────────────────────────────────────────────────╯\n")
        f_out.write("\n".join(lines_out))

    fname = os.path.basename(dst_path)
    print(json.dumps({"systemMessage": f"会话已导出: .claude/logs/{fname}"}))


def _get_latest_export_ts(logs_dir: str) -> datetime | None:
    """返回最近一次导出文件的时间，没有则返回 None。"""
    files = glob.glob(os.path.join(logs_dir, "conversation-*.txt"))
    if not files:
        return None
    latest = max(files, key=os.path.getmtime)
    return datetime.fromtimestamp(os.path.getmtime(latest), tz=timezone.utc)


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    logs_dir = os.path.join(project_root, ".claude", "logs")

    # --- 时间去重 ---
    if MIN_EXPORT_INTERVAL_MINUTES > 0:
        latest_ts = _get_latest_export_ts(logs_dir)
        if latest_ts is not None:
            elapsed = datetime.now(timezone.utc) - latest_ts
            if elapsed < timedelta(minutes=MIN_EXPORT_INTERVAL_MINUTES):
                sys.exit(0)  # 静默跳过

    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # stdin 不是合法 JSON，静默跳过
        sys.exit(0)
    session_id = data.get("session_id", "")

    if not session_id:
        sys.exit(0)

    home = os.path.expanduser("~")
    src = os.path.join(home, ".claude", "projects", "D--AI-vates", f"{session_id}.jsonl")

    if not os.path.exists(src):
        sys.exit(0)

    os.makedirs(logs_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    dst = os.path.join(logs_dir, f"conversation-{ts}.txt")

    convert_jsonl_to_export(src, dst)

    # 自动 stage 到 git
    import subprocess
    subprocess.run(
        ["git", "add", dst],
        cwd=project_root,
        capture_output=True,
    )


if __name__ == "__main__":
    main()
