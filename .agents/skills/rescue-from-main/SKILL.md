---
name: rescue-from-main
description: main/master에서 만든 변경사항을 안전하게 작업 브랜치로 옮긴 뒤 commit, push, draft PR까지 진행한다.
---

# rescue-from-main

`main`/`master`에서 실수로 작업한 변경사항을 내용 기반 작업 브랜치로 옮긴다. 자동 reset이나 강제 push는 하지 않는다.

## 절차

1. `git status --short --branch`, `git branch --show-current`, `git branch -vv`, `git remote -v`를 확인한다.
2. `gh auth status` 또는 `gh pr view`로 GitHub CLI 사용 가능 여부를 확인한다.
3. `git diff --stat`, `git diff --name-status`를 읽는다. staged 변경이 있으면 cached diff도 읽는다.
4. 변경분이 없고 현재 브랜치에만 push되지 않은 commit도 없으면 중단한다.
5. diff 내용에서 2-5개 단어의 kebab-case `{change-slug}`를 만든다. `fix`, `update`, `changes`, `misc`, `wip` 단독 이름은 쓰지 않는다.
6. Task ID가 명확하면 `task/{task-id}-{change-slug}`, 없으면 `work/{change-slug}`를 사용한다.
7. `git branch --list {branch}`와 `git ls-remote --heads origin {branch}`로 충돌을 확인하고, 필요하면 `-{n}` suffix를 붙인다.
8. 현재 브랜치가 `main`/`master`이고 uncommitted 변경이 있으면 `git switch -c {branch}`로 새 브랜치를 만든다.
9. 현재 브랜치가 `main`/`master`이고 upstream보다 앞선 local commit이 있으면 중단한다. 보존과 main 복구는 별도 승인 후 처리한다.
10. 이미 작업 브랜치면 브랜치명이 변경 내용과 맞는지 확인하고 진행한다.
11. 범위 밖 파일이 섞여 있지 않은지 확인한 뒤 `git add`로 stage한다.
12. Task가 있으면 `task {task-id}: {summary}`, 없으면 `{summary}`로 commit한다.
13. `git push -u origin {branch}` 후 `gh pr create --draft`를 실행한다.
14. PR 본문에는 변경 요약, 검증 결과, Acceptance evidence, residual risk, 연결 이슈가 있으면 `Closes #N`을 포함한다.

## 제한

- `git reset --hard`, `git checkout --`, `git push --force`, `git push --force-with-lease`는 실행하지 않는다.
- 사용자 변경은 되돌리지 않는다.
- 인증, 권한, remote 오류는 원문을 요약하고 멈춘다.
- Acceptance evidence가 없으면 draft PR 본문에 미실행 사유를 적거나, 사용자가 요구한 경우 중단한다.
