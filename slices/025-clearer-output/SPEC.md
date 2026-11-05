# Slice 025: say what was hidden, and which checks did not run

Status: **approved** (2026-11-05, "proceed to fixing"). Phase 1, item 2b (D-027).

## Why (`FEEDBACK.md` 2f, a teammate; 2b, the school project)

- "`allowed: 1` and `baselined: 1` in `review` don't name the finding, so I can't tell
  whether it's mine."
- "A baseline taken after a change hides that branch's own findings, without warning"
  (school project). Naming what the baseline hid on your lines makes that visible.
- "`project checks are not run by scan` doesn't say what those checks are or how to run
  them." It is also printed when a project has no checks at all.
- "`scan` kept reporting the same findings from someone else's merged work; `review
  --base` doesn't have this problem, so review should probably be the advertised default,
  with scan for full sweeps."

## Measured first

- `review` counts allowed findings (`len(on changed lines) - len(not allowed)`) and
  remembered ones (`baseline.split` returns only a count). Neither list survives to the
  report.
- `scan` prints "project checks are not run by scan" unconditionally.
- The counts are asserted by 9 existing tests; they stay as they are.

## Design

1. `review` lists, above the summary, every finding it hid on your changed lines:
   - `allowed: path:line: [tool rule] message (reason: <the [[allow]] reason>)`
   - `baselined: path:line: [tool rule] message`
   The summary counts `allowed: N`, `baselined: N` stay. `json` gets a `hidden` list
   (`kind` allowed or baselined, the finding, and the reason). `scan` keeps counts only
   (its baseline can hold thousands).
2. `scan` says `project checks are not run by scan: <names> (run healthkit review)` only
   when the project has `[[check]]` entries; nothing when it has none.
3. README: `review` is the check for your own work; `scan` is the full sweep of a module.

## Failure modes, each with a test

- an allowed finding on a changed line: named, with its reason;
- a baselined finding on a changed line (re-indented code): named;
- a finding allowed off the changed lines is not listed (review shows your lines only);
- `json` carries both kinds;
- `scan` with checks names them; `scan` without checks says nothing about them.

## Acceptance

Tests failing first; mutants; full suite; a live `review` on a QuickRPA clone branch
(it has `[[allow]]` entries and a baseline); line count against the budget (ask again,
D-028); fresh-agent check, its verdicts only with pasted runs (L-001).
