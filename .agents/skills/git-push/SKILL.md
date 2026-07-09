---
name: git-push
description: 현재 Git 브랜치를 안전하게 원격에 push한다. git push, upstream 설정, 작업 브랜치 게시 요청 시 사용.
---

# git-push

현재 브랜치를 원격에 push한다.

## 절차

1. `git status --short`, `git branch --show-current`, `git worktree list`를 확인한다.
2. 현재 브랜치가 `main`/`master`면 push하지 말고 사용자 확인을 받는다.
3. 커밋되지 않은 변경분이 있으면 push 대상이 아니므로 중단하고 보고한다.
4. 최근 RUN_REPORT에 fresh verification evidence와 review approval이 있는지 확인한다. 없으면 PR 가능 상태가 아니라고 보고한다.
5. upstream이 있으면 `git push`를 실행한다.
6. upstream이 없으면 `git push -u origin {current-branch}`를 실행한다.
7. push 결과와 PR 작성 가능 여부를 보고한다.

## 제한

- `--force`, `--force-with-lease`는 사용하지 않는다.
- 인증/권한/remote 오류는 원문을 요약하고 멈춘다.
- merge, PR, keep, discard 선택지는 사용자가 명시 요청할 때만 제시한다.
