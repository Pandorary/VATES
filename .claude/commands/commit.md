提交并推送代码到 git 仓库。请执行以下步骤：

1. 先运行 `git status` 和 `git diff --stat` 查看变更
2. 根据变更内容自动生成合适的 commit message（遵循项目规范：chore/fix/feat 前缀，中文描述）
3. 执行 `python .claude/scripts/git_push.py "生成的commit message"`
