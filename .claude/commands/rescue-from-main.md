---
description: Move accidental main/master work to a content-named branch, then commit, push, and open a draft PR.
allowed-tools: Bash(git status:*), Bash(git branch:*), Bash(git remote:*), Bash(git diff:*), Bash(git log:*), Bash(git ls-remote:*), Bash(git switch:*), Bash(git add:*), Bash(git commit:*), Bash(git push:*), Bash(gh auth status:*), Bash(gh pr create:*), Bash(gh pr view:*), Read
---

# /rescue-from-main

절차 원본은 `.agents/skills/rescue-from-main/SKILL.md`다. 이 command는 Claude Code 호출용 wrapper다.

1. `.agents/skills/rescue-from-main/SKILL.md`를 읽고 같은 절차를 따른다.
2. `git status --short --branch`, `git branch --show-current`, `git branch -vv`, `git remote -v`를 먼저 확인한다.
3. diff 내용을 근거로 `task/{task-id}-{change-slug}` 또는 `work/{change-slug}` 브랜치를 만든다.
4. `main`/`master` local commit은 자동 복구하지 않는다.
5. `git reset --hard`, `git checkout --`, 강제 push는 실행하지 않는다.
6. 인자: `$ARGUMENTS`
