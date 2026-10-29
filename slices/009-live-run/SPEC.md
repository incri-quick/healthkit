# Slice 009: the first live run on Susheel's next module (D-021 step 3)

Status: written **before any run** (pre-registered, L-016). Measurement only: no healthkit
code changes.

## Target

Susheel's unmerged work of 2026-10-26/27, five stacked branches on `dev` 7fadfe3:
`fix/quickstudio-branding-auth` (4 commits) ⊂ `fix/agent-gate-checks-routed-path` (6) ⊂
`fix/route-table-guard` (9) ⊂ `feat/version-for-platform-admins` (13) ⊂
`refactor/api-front-door-naming` (14 commits, 40 files). One review of the top branch
covers all of it. None of healthkit's rules was written from this code: the clean test.

## How it runs

In the throwaway QuickRPA clone, configured as the team would have it (base branch
`hk-base`: the `.healthkit/` with the import contract, the allow entry, the project rule,
and the `[[check]]` running QuickRPA's tenancy and auth guards on the branch's code).
The branch is merged onto `hk-base`, so the diff is exactly Susheel's 14 commits.

`healthkit review --base hk-base`, output pasted whole, with the time taken.

## How each result is judged (fixed now, before seeing any)

- **Blocking finding:** *real* if a careful reviewer would ask for a change on that line;
  *noise* otherwise. Judged by reading the flagged line and its function on the branch.
- **Advisory finding (`worth a look`):** *real* if a deleted row would be treated as live
  there, as in slice 008.
- **A failed `[[check]]`:** real if the guard names a line this branch changed; a guard
  failing on code the branch did not touch is noise for this branch (and a finding about
  `dev`).
- Debatable cases are reported as debatable and counted against healthkit (lower bound).
- Every "real" quotes the line. Nothing is called real without reading it.

## What is not measured here

- **Recall** (what healthkit missed) needs a human review of this work. When one exists
  (Susheel's own notes or the reviewer's), it is scored like slice 006.
- **The API pack:** it needs this branch running; the local stack runs `dev`.

## Rules for this slice

- **No rule changes during the run.** Ideas go to a list; changing a rule because of this
  result and then quoting this result would make it circular (D-020, L-016).
- The clone is read-only toward GitHub: no push, no comment on Susheel's branches.

Also rides along: the build-plan row M4 in DECISIONS.md still said slice 008 was "next".
