---
description: Create a GitHub pull request from the current task branch with task and acceptance context.
allowed-tools: Bash(git status:*), Bash(git branch:*), Bash(git worktree:*), Bash(git log:*), Bash(gh pr create:*), Bash(gh pr view:*), Read
---

# /pr-create

절차 원본은 `.agents/skills/pr-create/SKILL.md`다. 이 command는 Claude Code 호출용 wrapper다.

1. `.agents/skills/pr-create/SKILL.md`를 읽고 같은 절차를 따른다.
2. `git status --short`, `git branch --show-current`, `git worktree list`를 먼저 확인한다.
3. TDD, fresh verification evidence와 리뷰 상태를 확인한다.
4. 기본은 draft PR이다. 연결 이슈가 있으면 `Closes #N`을 포함한다.
5. 인자: `$ARGUMENTS`
