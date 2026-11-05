# Slice 023: `review` never passes silently on uncommitted work

Status: **approved** (2026-11-04, "proceed"). Phase 1, item 1 (D-027). Case E and design
point 3 were added after approval, from a measurement; they close the same silent pass.

## Why

The one problem every source reported (`FEEDBACK.md` 2d): the school project ("looks like
a pass"), QuickRPA twice ("the most dangerous one"; a script was written around it), a
teammate ("23 files, no problems" with 2 files uncommitted), and an outside reader.

## Measured first (healthkit c291c89, a throwaway repo, 2026-11-04)

| Case | Today |
|---|---|
| A. An unused import, committed | found, exit 1 (correct) |
| B. A, plus a new untracked file with a problem | the new file is silently ignored |
| C. The same unused import, staged but **not committed** | "nothing to review", **exit 0** |
| D. A, plus an **uncommitted** docstring added above it | **"no known problems", exit 0**: the committed problem is missed |

| E. A, plus an **uncommitted** `.healthkit/config.toml` with `exclude = ["a.py"]` | **"nothing to review", exit 0**, no "needs human approval" |

E was found after approval, while writing the tests: the settings are read from disk, but
only committed `.healthkit/` changes reach a human. So the referee **can** be changed
quietly, by not committing (the outside reader's question, `FEEDBACK.md` 2e).

D is worse than what was reported. The checkers read the file on disk, where the problem
moved from line 6 to 9, while `review` matched against the committed line numbers. So any
uncommitted edit in a changed file can hide a committed problem, even in a pre-push
check.

git gives the right answer for both needs:
- `git diff --unified=0 <merge-base>`, without `...HEAD`, gives the lines changed in the
  **working tree** (staged and unstaged together): here lines 1-3 and 6-10, exactly the
  docstring and the new function at their new places.
- `git ls-files --others --exclude-standard` lists new, untracked, not-ignored files
  (names with spaces included).

## Design

1. **`review --base X`, the default, stays committed-only** (enforcement judges commits;
   D-018, the outside reader's point), but it never passes silently:
   - If a file it reviews also has uncommitted changes, its committed lines cannot be
     checked (case D): **exit 2**, naming the files, with "commit or stash them, or use
     `--working-tree`".
   - If nothing committed is left to review but there is uncommitted Python work (case
     C): **exit 2**, "nothing committed to review; N uncommitted file(s): use
     `--working-tree`", instead of "nothing to review", exit 0.
   - Other uncommitted or untracked Python files, outside the review (case B): listed as
     `not reviewed (uncommitted): N file(s)`. The exit code is unchanged, because they are
     not part of what is pushed.
2. **`review --base X --working-tree`** checks the working tree against the base:
   - committed, staged and unstaged lines, from the diff against the merge base;
   - every line of a new, untracked, not-ignored file;
   - `.healthkit/` changes in the working tree, untracked ones included, still need a
     human (exit 3);
   - project checks still come from the base branch only (D-018);
   - the summary says `working tree (uncommitted changes included)`.
3. **Uncommitted `.healthkit/` changes need a human in both modes** (case E): tracked
   changes and untracked files under `.healthkit/` join the "needs human approval" list
   (exit 3, or exit 1/2 when those apply). The settings on disk are what ran, so they
   must be what a person approves.
4. A truly clean branch with nothing to review is still "nothing to review", exit 0.
5. README: both modes, plainly; the AI instructions use `--working-tree` before a commit
   and plain `review` before a push.

## Out of scope

- A pre-commit hook or file watcher (an outside reader and we agree: convenient, but no
  substitute for the commit-based gate).
- "Every finding in the files I touched" as its own mode (`FEEDBACK.md` row 4): with D
  fixed and C901 already spanning its function, `--working-tree` covers what that asked
  for. To revisit only if use shows otherwise.

## Failure modes, each with a test

- staged only; unstaged only; staged and then edited again;
- an untracked file whose name has a space; an untracked file in an ignored folder (never
  reviewed);
- an uncommitted deletion of a file (no lines, no crash);
- an untracked new rule file in `.healthkit/rules/` (`--working-tree`: needs approval);
- an unrelated dirty file next to a clean committed review (listed, exit unchanged);
- not a git repository, or an unknown base (exit 2, as today).

## Acceptance

Cases A-D above as tests, shown failing first. Mutants on each new rule. The full suite.
A live run on a real repository with uncommitted work: QuickRPA backend (read-only, its
own working tree). Line count reported (budget 2,500, D-028). A fresh agent tries to
refute the slice (rule 6, restarted per L-026).
