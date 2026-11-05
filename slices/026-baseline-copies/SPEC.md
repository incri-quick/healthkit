# Slice 026: a new copy of a remembered line is never hidden

Status: **approved** (2026-11-05, "proceed"). Phase 1, item 3, part 1 (D-027). The other
small bugs (project rules, `severity`, BOM, callables) are slice 027.

## Why

- **Found by hand while checking slice 025:** the baseline remembers 2 copies of
  `import os` in a file; the branch adds a third. `review` names it `baselined`, exit 0. A
  silent pass, older than slice 025 (which only made it visible). In QuickRPA, where
  `except Exception as exc:` lines are baselined by the hundred, a new one is hidden the
  same way.
- **The teammate's row 3** (`FEEDBACK.md` 1): adding one more already-accepted line
  "flagged an older, untouched copy instead of the new one".

## Measured first (2026-11-05, by hand)

- Baseline: `pkg/a.py` remembers `import os` twice (lines 2 and 6). Branch adds a third
  at line 10. `review --base <baseline commit>`: `baselined: pkg/a.py:10 ...`, exit 0.
- Cause: `review` passes only the changed-line findings to `baseline.split`, so the new
  copy takes one of the two remembered slots; the two old copies, on unchanged lines,
  are never counted.
- The checkers already run on whole files, so every copy is in `run.findings`.

## Design

1. `review` matches the baseline against **every** finding in the reviewed files, giving
   the remembered slots to copies on unchanged lines first. Whatever is left on the
   changed lines is new. Then only changed-line findings are shown, as before.
   - more copies than remembered: the copies on changed lines are new;
   - the same number, one moved or re-indented: still remembered (existing behaviour).
2. A new finding whose line the baseline does remember, just fewer times, says so:
   `... (one more copy of a line the baseline remembers N time(s))`. In `scan`, which has
   no changed lines, this is the honest answer to "which copy is new" (the teammate's
   suggested wording).

## Failure modes, each with a test

- a third copy added to two remembered ones: reported on its own line, exit 1;
- a remembered line moved (same count): still remembered, exit 0;
- one old copy removed and one new one added elsewhere: remembered, exit 0;
- a copy added in a file that has none remembered: new, without the "one more copy" note;
- `scan` with one more copy than remembered: reported with the note.

## Acceptance

Tests failing first; mutants; full suite; the hand repro re-run; a live `review` on a
QuickRPA clone (baselined counts before and after); line count (budget asked again);
fresh-agent check, verdicts only with pasted runs.
