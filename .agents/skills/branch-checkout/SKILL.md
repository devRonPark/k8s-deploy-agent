---
name: branch-checkout
description: 작업 전용 Git 브랜치를 만들거나 전환한다. 별도 브랜치 체크아웃, task 브랜치 생성, 브랜치 전환 요청 시 사용.
---

# branch-checkout

별도 작업 브랜치를 안전하게 만들거나 전환한다.

## 절차

1. `git status --short`, `git branch --show-current`, `git worktree list`, `git submodule status`를 확인한다.
2. 변경분이 있으면 요약하고, 전환해도 되는지 판단한다. 사용자 변경은 되돌리지 않는다.
3. worktree나 submodule 상태가 전환에 영향을 주면 먼저 보고한다.
4. 필요하면 baseline test 실행 여부를 사용자에게 보고한다. 실행하지 않았다면 "baseline test not run"으로 남긴다.
5. 필요하면 `git fetch origin`으로 원격 기준을 최신화한다.
6. 기존 브랜치면 `git switch {branch}`를 실행한다.
7. 새 브랜치면 `task/{task-id}-{short-slug}` 형식을 선호해 `git switch -c {branch}`를 실행한다.
8. 전환 후 현재 브랜치, worktree 상태, 남은 변경분을 보고한다.

## 제한

- `git reset --hard`, `git checkout --`, 강제 push는 실행하지 않는다.
- 브랜치명이 불명확하면 Task ID나 사용자 목적에서 짧은 이름을 제안한다.
