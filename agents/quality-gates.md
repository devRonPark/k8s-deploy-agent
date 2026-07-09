---
name: quality-gates
description: "Claude Code plugins and Codex skills share these scope, YAGNI, review, and reporting gates."
role: quality-gate
allowed-tools: ["Read", "Grep", "Glob"]
---

# Quality Gates

This document turns the durable parts of ponytail and caveman into repository
rules that both Claude Code and Codex can apply. Claude Code may still receive
ponytail/caveman through plugins. Codex does not run those plugins automatically,
so Codex workflows must read and apply this file directly.

## Scope Gate

Run this before implementation and again whenever the work starts expanding.

1. Confirm the selected Task has one observable outcome, one main concern, a
   concrete DoD, and an Acceptance command or an explicit `-`.
2. Apply YAGNI: do not add frameworks, abstractions, configuration layers,
   helpers, files, or features that the Task does not need.
3. Reuse existing project patterns, standard library features, and installed
   dependencies before writing new machinery.
4. Keep edits inside the Task boundary. Avoid drive-by cleanup unless it is
   required to make the Task pass.
5. Split the Task before implementation if it mixes planning, runtime behavior,
   UI, infrastructure, docs, or test-system changes that can be verified
   independently.
6. For behavior changes, require TDD: see a failing test or failing Acceptance
   first, then make the smallest change that turns it green. Record exceptions
   for docs, config, generated code, and throwaway prototypes in RUN_REPORT.

Stop and re-plan when any of these is true:

- the Task needs three or more unrelated files to change for different reasons;
- the implementation needs more than one behavioral surface to be accepted;
- the Acceptance command cannot prove the DoD;
- a reusable abstraction is being added for only one current caller;
- a requested change depends on a still-`todo` Task not listed in `depends`.

Use implementer/reviewer subagents only as an optional gate for large Tasks or
high review risk. Do not add a subagent ledger or `.superpowers/` directory;
the state source remains `tasks/index.json` and `.harness/tasks/<task-key>/`.

## Review Gate

Use this before approving work.

1. Findings first. Lead with bugs, regressions, rule violations, missing
   Acceptance evidence, and test gaps.
2. Cite file and line evidence for each finding.
3. Split the verdict into `Spec compliance` and `Code quality`. If either has a
   blocker, the overall verdict is `REQUEST_CHANGES`.
4. Treat over-engineering as a review issue when it adds unused abstraction,
   expands scope, hides simple control flow, or makes future Tasks harder.
5. Verify that TDD evidence or a justified exception exists.
6. Verify that the recorded Acceptance command and relevant test suite ran after
   the implementation as fresh verification.
7. If there are no blockers, say so clearly and list only residual risk or test
   gaps that still matter.

Do not claim complete, fixed, passing, ready for PR, or approved before evidence
exists. Partial verification can support a progress update, but it cannot
support a completion claim.

## Reporting Gate

Use caveman-like compression without losing engineering facts.

- Keep routine status updates short.
- Put verification results before background explanation.
- Do not narrate obvious file edits.
- Do not include long general advice when a concrete command, file, or finding
  is available.
- Preserve precision for commands, paths, Task IDs, failing output, and review
  evidence.

## Claude/Codex Boundary

- Claude Code: ponytail/caveman plugins can enhance the session automatically.
  This file remains the repo-level rulebook for harness flows.
- Codex: no ponytail/caveman plugin auto-hook is assumed. `AGENTS.md` and
  `.agents/skills/*` must reference this file when planning, implementing, and
  reviewing.
- Do not create fake Codex plugin commands for ponytail/caveman. Use this file
  as the shared contract instead.
