---
description: Push the current branch safely after checking status, branch, and upstream.
allowed-tools: Bash(git status:*), Bash(git branch:*), Bash(git worktree:*), Bash(git remote:*), Bash(git push:*), Read
---

# /git-push

절차 원본은 `.agents/skills/git-push/SKILL.md`다. 이 command는 Claude Code 호출용 wrapper다.

1. `.agents/skills/git-push/SKILL.md`를 읽고 같은 절차를 따른다.
2. `git status --short`, `git branch --show-current`, `git worktree list`를 먼저 확인한다.
3. `main`/`master` push와 커밋되지 않은 변경분 push는 중단하고 보고한다.
4. fresh verification evidence와 review approval이 없으면 PR 가능 상태가 아니라고 보고한다.
5. `--force`, `--force-with-lease`는 사용하지 않는다.
6. 인자: `$ARGUMENTS`
