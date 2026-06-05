"""提交并推送所有变更到 git 仓库。"""
import subprocess
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run(cmd: list[str]) -> bool:
    result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ {' '.join(cmd)}")
        print(result.stderr.strip())
        return False
    if result.stdout.strip():
        print(result.stdout.strip())
    return True


def main():
    if len(sys.argv) < 2:
        print("用法: py git_push.py <commit message>")
        print("示例: py git_push.py \"fix: 修复登录问题\"")
        sys.exit(1)

    msg = sys.argv[1]

    # 1. git add 所有变更
    print("📦 git add -A ...")
    if not run(["git", "add", "-A"]):
        sys.exit(1)

    # 2. 检查是否有东西可提交
    diff_result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=PROJECT_ROOT,
    )
    if diff_result.returncode == 0:
        print("⚠️  没有需要提交的变更")
        sys.exit(0)

    # 3. git commit
    print(f"📝 git commit -m \"{msg}\" ...")
    if not run(["git", "commit", "-m", msg]):
        sys.exit(1)

    # 4. git push
    print("🚀 git push ...")
    if not run(["git", "push"]):
        print("⚠️  push 失败，请检查网络后手动 git push")
        sys.exit(1)

    print("✅ 完成")


if __name__ == "__main__":
    main()
