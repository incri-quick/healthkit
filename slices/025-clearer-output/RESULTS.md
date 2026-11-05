# Slice 025 results: say what was hidden, and which checks did not run

## What changed

- **`review` names every finding it hid on your changed lines**, above the summary:
  - `allowed: path:line: [tool rule] message (reason: <the [[allow]] reason>)`
  - `baselined: path:line: [tool rule] message`

  The summary counts (`allowed: N`, `baselined: N`) are unchanged. `json` gets a `hidden`
  list, with kind, finding and reason. `markdown` gets a "Hidden on the changed lines"
  section. `scan` keeps counts only, since its baseline can hold thousands.
- **`scan` names the project checks it skips**, and only when there are some:
  `project checks are not run by scan: tenancy guard, route table (run healthkit review)`.
  A project with no `[[check]]` no longer gets the line at all.
- README: `review` is for your own work, `scan` is the full sweep of a module (other
  people's code included); what the named hidden lines mean.
- Code:
  - `config.Settings.allowed_by()` returns the matching `[[allow]]`;
  - `baseline.split()` returns the remembered findings, not just their number;
  - `report.Report.hidden`;
  - `cli._hidden()`, a helper, so `_review` stays under the linter's statement limit
    instead of silencing it.

## One older test changed (owner said "commit" with it called out, 2026-11-05)

`test_project_settings.py::test_an_allowed_finding_is_counted_not_printed` (slice 004)
asserted the allowed finding is not printed at all. That is exactly what the teammate
asked to change. Its point, that an accepted finding never reads as a problem, is kept:
renamed `..._counted_and_labelled_never_reported`, it now asserts every line naming the
finding starts with `allowed: `, and the verdict is still "no known problems", exit 0.

## Live run: QuickRPA (a throwaway clone of `feat/hitl-robot-approvers` vs `dev`)

- **2 allowed findings, named with their reasons:**
  - `commons/cache_guard.py:95` BLE001 (the guarded cache seam);
  - `studio_robot/approval_briefing.py:66` `soft-delete-read` (R-11: the approver is
    briefed from the version that actually ran).
- **16 baselined findings, all named.** Most are "too complex" (C901) on functions the
  branch edited: `decide_run_approval` (20), `_execute_loop_node` (45),
  `compute_readiness` (34), `receive` (26). Before this slice the reviewer saw only
  "baselined: 16".
- The same branch showed 15 in slice 023's run: the other session added two HITL commits
  since then (checked with `git log`), not a healthkit change.

## Tests

`tests/test_clearer_output.py`, 7 tests. 5 failed before the code; "off your lines is not
listed" passed already, as it must. The Markdown test was added after the first mutant
plan, which had no way to catch Markdown losing the section.

## Mutants: 9 of 9 killed

Allow reason dropped · baselined not listed · every finding listed instead of your
lines · checks not named · checks line always printed · text hides them · json hides
them · markdown hides them · reason never shown.

## Full suite

256 passed (13 min), with `HEALTHKIT_OPENGREP` set.

## Checklist (L-026)

- **Line count:** 2,586 non-blank lines in `src/` (was 2,556; +30). Over the 2,500 budget
  (D-028); the 3,000 proposal is still unanswered (the owner said "commit" with the count shown), so it is asked again.
- **D-/L- entries:** none new.
- **Fresh-agent check:** done. Told that only pasted runs count, it pasted output for the
  4 claims (all confirmed, no defects), but listed its edge cases with ticks and no runs,
  and skipped one (`# noqa` on an allowed finding). Two were run by hand:
  - allowed **and** `# noqa`: shown as `allowed` with the first matching reason, exit 0.
    Fine: an approved `[[allow]]` already covers it.
  - **a third copy of a line the baseline remembers twice: `review` calls it
    "baselined", exit 0. A real silent pass, older than this slice** (slice 025 only
    made it visible by naming it). `review` matches the baseline against changed-line
    findings only, so the new copy takes a slot meant for the old copies on unchanged
    lines. `scan` gets it right (it sees all copies). Same root cause as the teammate's
    row 3 ("flagged an older, untouched copy instead of the new one"). Goes to slice
    026.

## Uncertain

- When two `[[allow]]` entries match one finding, the first one's reason is shown (asked
  of the fresh agent).
- A long reason makes a long line. Not shortened: the reason is the point.
