---
name: grill-me
description: 아이디어·기능 요청을 한 번에 한 질문씩 인터뷰해서 docs/PRD.md 초안까지 작성한다. 새 프로젝트/기능 착수, PRD 작성, "grill me" 요청 시 사용.
---

# grill-me

Codex용 PRD 인터뷰 스킬이다. `CLAUDE.md` 기획 규칙과 `.claude/skills/grill-me/SKILL.md`
의 기존 의도를 따른다. 인터뷰만 하고 끝내지 말고 `docs/PRD.md` 작성까지 완료한다.

## 절차

1. 먼저 `AGENTS.md`, `CLAUDE.md`, 기존 `docs/PRD.md`, `docs/templates/PRD.md`를 읽는다.
2. 코드베이스나 기존 문서로 답할 수 있는 내용은 직접 확인한다.
3. 사용자에게 질문은 한 번에 하나만 한다.
4. 모든 질문에는 권장 답과 이유를 함께 제시한다.
5. 목적, 제약, 대상 사용자, 핵심 기능 3±2개, Non-goals, 측정 가능한 성공 기준을 확인한다.
6. 구현 전 접근안 2-3개와 추천안을 짧게 비교한다. 사용자가 답하지 못하면 권장안을 임시 결정으로 둔다.
7. `docs/templates/PRD.md`를 기준으로 `docs/PRD.md`를 작성하고, 미확정 항목은 Open Questions에 남긴다.
8. 승인 후 UserFlow·DESIGN·Architecture 보완과 `$harness-plan` 실행을 안내한다.

## 기본값

- 산출 경로 기본값은 현재 프로젝트의 `docs/`다.
- 사용자가 응답하지 않거나 headless 환경이면, 이미 확정된 내용과 권장 답을 기준으로 초안을 쓰고 미확정 항목을 Open Questions에 남긴다.
