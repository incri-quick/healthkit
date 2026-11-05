# Slice 026 results: a new copy of a remembered line is never hidden

## What changed

- **`review` matches the baseline against every finding in the reviewed files.** Copies on
  unchanged lines take the remembered slots first; whatever is left on the changed lines
  is new. Only changed-line findings are shown, as before (`cli._against_baseline`).
- **One copy too many says so:**
  `... (one more copy of a line the baseline remembers N time(s))`. Shown by `review` on
  the new copy's own line, and by `scan`, which cannot tell which copy is new (the
  teammate's suggested wording, `FEEDBACK.md` row 3) (`baseline.split`).
- A trap caught before the first run: a finding with the note is a changed copy, so
  filtering the result by set membership would have dropped exactly the finding this slice
  exists to report. The result is filtered by changed lines instead; a mutant now guards it
  ("noted copies dropped").

## Measured first (by hand, during slice 025)

`pkg/a.py` remembered `import os` twice; the branch added a third at line 10. `review`:
`baselined: pkg/a.py:10`, exit 0. The cause: only changed-line findings went to
`baseline.split`, so the new copy took an old copy's slot.

## Live run: QuickRPA (a throwaway clone of `feat/hitl-robot-approvers` vs `dev`)

- As the branch stood: 2 findings, allowed 2, baselined 16. The same as slice 025's run,
  so no false new findings on real code.
- Then one more `except Exception as exc:` appended to `studio_workflow/api/webhook.py`
  (the baseline remembers that line twice there), committed in the clone:
  `studio_workflow/api/webhook.py:484: [ruff BLE001] ... (one more copy of a line the
  baseline remembers 2 time(s))`. Findings 2 → 3, baselined still 16. Before this slice it
  would have been counted as baselined, exit unchanged.
- The clone was removed.

## Tests

`tests/test_baseline_copies.py`, 5 tests:
- a third copy (exit 1, on its line, with the note);
- a moved copy (still remembered);
- one copy removed and one added elsewhere (count kept);
- a copy in a file with none remembered (no note);
- `scan` with one copy too many (the note).

2 failed before the code; the 3 that passed are behaviour that must not change. One
assertion was tightened before the code was written.

## Mutants: 6 of 6 killed

Changed lines matched first · changed lines only, as before · noted copies dropped · no
note · note without the count · note on every new finding.

## Full suite

261 passed (13 min), with `HEALTHKIT_OPENGREP` set.

## Checklist (L-026)

- **Line count:** 2,617 non-blank lines in `src/` (was 2,586; +31). Over the 2,500 budget
  (D-028); the 3,000 proposal is still unanswered (the owner said "commit" with the count shown), so it is asked again.
- **D-/L- entries:** none new.
- **Fresh-agent check:** done; it reported all 4 claims and 6 edge cases confirmed, but
  pasted **no** command output, though its instructions said only pasted runs count. The
  third slice running that this agent did not. Its riskiest three edge cases were run by
  hand, all correct:
  - remembered once, two extra copies added: both reported on their own lines (6 and 10)
    with "remembers 1 time(s)", exit 1;
  - an extra copy with `# noqa: F401`: "needs human approval: pkg/a.py:6 suppresses ruff
    F401", exit 3, not reported as new;
  - an extra copy left uncommitted, `--working-tree`: reported with the note, exit 1.

  Pattern to act on: the fresh agent's report cannot be taken as evidence. Its value so
  far has been pointing at cases to run by hand. Proposed for the next catch-up: the
  verifier's instructions must ask for its commands in a file the owner can re-run, or the
  check is done by hand.

## Uncertain

- Which copy is "new" in `review` when several copies sit on changed lines (code moved
  and copied in one change): the ones matched last in file order. The count is always
  right; the line chosen can be either copy.
