# Slice 023 results: `review` never passes silently on uncommitted work

## What changed

- **`review --base X` stays committed-only, and never passes silently over uncommitted work:**
  - a reviewed file that also has uncommitted edits: **exit 2**, naming the files, with
    "Commit or stash them, or use --working-tree" (case D);
  - nothing committed, but uncommitted Python work: **exit 2**, "Use --working-tree"
    (case C; it used to say "nothing to review", exit 0);
  - other uncommitted Python files outside the review: listed as
    `not reviewed (uncommitted): N file(s): ...`, exit unchanged (case B).
- **New `--working-tree`:** the diff against the merge base, which gives the working
  tree's own line numbers (staged and unstaged together), plus every line of new,
  untracked, not-ignored files. The summary says
  `working tree (uncommitted changes included)`. Project checks still come from the base
  branch only.
- **Uncommitted `.healthkit/` changes need a human in both modes** (case E): tracked edits,
  deletions and untracked files under `.healthkit/` join "needs human approval".
- Files the project excludes never count as uncommitted work.
- `gitdiff.py`: `changed_lines(..., working_tree=)`, `untracked()`, `uncommitted()`;
  `files_touched_under()` includes uncommitted changes. `cli.py`: the flag and
  `_uncommitted_refusal()`.
- README: both modes, and the AI instructions (`--working-tree` before a commit, plain
  `review` before a push).

## Measured before coding

| Case | Before (c291c89) | After |
|---|---|---|
| A. committed problem, clean tree | found, exit 1 | same |
| B. plus an untracked new file with a problem | silently ignored | listed (default); reviewed (`--working-tree`) |
| C. the problem staged, not committed | "nothing to review", **exit 0** | exit 2 (default); found, exit 1 (`--working-tree`) |
| D. committed problem + an uncommitted edit above it | "no known problems", **exit 0** (missed) | exit 2 (default); found on its new line 9 (`--working-tree`) |
| E. committed problem + an uncommitted `.healthkit/` exclude hiding it | "nothing to review", **exit 0** | needs human approval |

D and E were not in the feedback: found while measuring C. D meant even a pre-push check
could miss a committed problem; E meant the referee could be changed quietly by not
committing (the outside reader's question).

## Live run: QuickRPA backend

A throwaway clone of the backend on `feat/hitl-robot-approvers` (94 changed Python
files vs `dev`), so the real working tree was never touched. (A first clone under the
scratchpad failed to check out: the path was too long for Windows. Recloned to `C:\tmp`.)

- Committed review, clean tree: exit 1, 2 findings, as before the slice.
- Plus an uncommitted `import colorsys` at the top of `agent/utils.py` (a file the branch
  changed):
  - default: **exit 2**, "1 changed file(s) also have uncommitted changes ...:
    agent/utils.py";
  - `--working-tree`: exit 1, the new `agent/utils.py:1` F401 and I001 found, and the
    branch's 2 original findings unchanged (a diff of the two finding lists shows only the
    additions).
- Plus an untracked `.healthkit/rules/zz-live-test.yaml`: listed under "needs human
  approval".
- About 23 s per run.

## Tests

`tests/test_review_working_tree.py`, 18 tests. 15 failed before the code; the 2 that
passed (case A, a clean branch) are the behaviour that must not change; 1 was added after
(an excluded uncommitted file never blocks a review).

## Mutants: 11 of 11 killed

Working tree diffed as commits · untracked files never added · last line of a new file
dropped · untracked not counted as uncommitted · uncommitted referee ignored · refusal
also in working-tree mode · dirty reviewed file allowed · nothing committed passes ·
others not listed · excluded files counted as dirty · working tree not said.

## Full suite

238 passed (10 min), with `HEALTHKIT_OPENGREP` set.

## Checklist (L-026)

- **Line count:** 2,505 non-blank lines in `src/` (was 2,456; +49). **5 over the 2,500
  budget (D-028): stop-and-ask, put to the owner,** who said "commit" with the count in
  front of them (2026-11-04). Taken as accepted for this slice; the next slice that grows
  the source asks again.
- **D-/L- entries:** none new needed; the slice follows D-027 phase 1 and D-018.
- **Fresh-agent check:** done, the first since slice 009 (L-026). A read-only verifier
  agent, asked to refute the 4 claims in throwaway repos, reported all 4 **confirmed**,
  including: a `git mv` rename then edited (exit 2), staged and untracked work with
  nothing committed (exit 2), spaces in names, a working-tree deletion (no crash), CRLF vs
  LF (no false "uncommitted"), and an uncommitted `.healthkit/config.toml` (exit 3 in both
  modes). Limits, stated plainly: its report quotes output only in part (L-001 asks for
  pasted runs), and it did not report on non-ASCII names, `.Healthkit/` in another case,
  a branch with no merge base, submodules or `.pyi` files. Those stay unverified.

## Uncertain

- On Windows, a file whose only difference is line endings may count as uncommitted (git
  decides; the live clone showed no such file).
- A repository with uncommitted work in many unrelated files gets a long
  `not reviewed (uncommitted)` line; names are not shortened.

## Lesson

A reported bug is worth measuring around, not just fixing: the reported case (C) led to
two worse ones (D, E) in ten minutes, both silent passes nobody had noticed.
