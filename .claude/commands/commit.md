# /commit — 提交并推送代码

按以下步骤提交并推送代码：

1. 运行 `git status` 和 `git diff` 查看变更内容
2. 根据变更自动生成 commit message，遵循项目规范：
   - 前缀：`feat`（新功能）、`fix`（修复）、`chore`（杂项/重构/文档）
   - 描述用中文，简洁明了
3. 运行 `python .claude/scripts/git_push.py "<commit message>"` 一键 add + commit + push
