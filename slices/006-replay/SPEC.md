# Slice 006: the replay test

Status: **approved** (2026-10-27), including decisions 1-4

## Goal

Measure what healthkit is worth (D-008): for each finding in Susheel's users/auth code
review, run healthkit on the code **just before his fix** and ask whether it pointed at
the lines the fix changed. Result: a score, and every miss sorted into a D-017 kind
(pattern / structure / knowledge / behaviour), which becomes the rule backlog.

## Out of scope

A `healthkit replay` command (decide after seeing whether the harness is worth keeping),
other reviewers' findings, other modules, writing new rules.

## Ground truth (measured 2026-10-27)

- **AA-01..AA-35:** full write-ups in his review file, in QuickRPA history at
  `deafb68^:docs/code-review/reviews/users-auth-a-tokens-password.md`.
- **AA-36..AA-75:** defined only in his private notes (untracked on Oct 7); visible to us
  only through commit messages ("code review AA-44").
- **43 fix commits** say "code review AA-xx"; 52 distinct AA ids are mentioned, some
  only as follow-ups ("follow-ups AA-37, AA-38") or dropped/deferred.

## Design

1. **The answer key, `aa-fixes.toml`:** one entry per AA that has a fix: id, fix
   commit(s), one-line description, source (review file or commit message), D-017 kind.
   A script proposes it from commit messages; mentions like "follow-ups AA-37" are not
   fixes. **I review every entry by hand**; Susheel can correct it later. The kind is a
   judgement and is labelled as one.
2. **For each fix commit:** check out its parent in a throwaway worktree of the QuickRPA
   clone; run healthkit's three gate tools on the **whole files** the fix touched (not
   only changed lines: the problem existed before, it was not added by the fix).
3. **A hit** = a finding on a line the fix changed or removed (old side of the diff).
   For a fix that only **adds** lines (e.g. a missing check), a finding within 3 lines of
   the insertion point counts. The window is reported, so the reader can judge it.
4. **Two scores, because of contamination:** three of today's rules were written *from*
   these very incidents (`exception-text-in-reply` from AA-15, `raw-json-body` from
   AA-65, the layer contract from AA-06). Scoring them on their own source is circular.
   - Score A: all of today's rules.
   - Score B: excluding rules derived from this AA set: the honest "would it have
     caught them" number.
5. **Rules as of today**, with QuickRPA's `.healthkit/` from slices 003-005.
6. Reuses healthkit's adapters (`tools.*.run`) and config; adds no toolkit code.

## Failure modes (each gets a test or an explicit row in the results)

1. An AA mentioned only as a follow-up or deferred → not scored (listed as "no fix").
2. One AA fixed across several commits → scored once (hit if any fix commit is hit).
3. A fix commit that touches only tests/docs (a guard, not a fix) → listed, not scored
   as a miss.
4. A file renamed or deleted by the fix → the parent's path is used.
5. A tool error on an old snapshot → the AA is marked "not checked", never "miss".
6. The worktree is always the parent of the fix commit (asserted), never the fix itself.

## Acceptance

- `RESULTS.md`: per-AA table (id, kind, fix commit, hit/miss, which rule), Score A,
  Score B, the misses grouped by kind, and the rules a miss suggests.
- The harness re-runs from scratch and gives the same table.
- The answer key reviewed line by line; every judgement visible.
- A fresh agent re-derives 5 random rows by hand; disagreements reported.

## Needs approval

1. **Whole-file check on the parent of each fix**, hit = finding on the changed lines
   (±3 lines for pure insertions). The alternative (diff-only) cannot see problems that
   predate the fix, which is all of them.
2. **Two scores (A: all rules, B: excluding rules derived from these incidents).** Only B
   is quoted as "what healthkit is worth".
3. **The answer key is mine to draft and review**, using his review file for AA-01..35 and
   commit messages for 36+. Optional: ask Susheel for his current notes to firm up 36+.
4. **The harness stays in `slices/006-replay/`** as a measurement, not a command, until
   the result shows it is worth productising.

## Lesson this slice teaches

Measure against reality, and separate the training data from the test: a rule scored on
the incident it was written from proves nothing.
