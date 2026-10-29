# Slice 022 results: how big was the leak, no personal data left behind, counts per kind

The last upgrade before healthkit goes to the team (2026-10-29).

## What changed

- **Leak size.** A `must-refuse` finding says how big the largest 2xx answer was:
  `HK_TEACHER got 200 (469 records)`, `(1 record)` or `(empty)`.
  - Records are counted from the answer bodies in the event log. A list counts its items;
    an object counts its longest list, or else 1; `{}`, `[]` and `null` count 0.
  - A body that is not JSON shows no size.
  - Only the count is kept, never the data.
- **No personal data left behind.** Without `--report-dir`, the temp report folder is
  deleted when the run ends, failed runs included. The summary says
  `reports: deleted (keep them: --report-dir)`. With `--report-dir` the folder is kept.
- **Counts per kind** in the summary: `server errors`, `access leaks`,
  `cross-user reads`, `other`, each shown only when non-zero.
- Internal: each user's run keeps its `Events` (statuses and sizes) instead of statuses
  alone.

## Live check

Not run on a real project. The school project's last report folder held real personal
data, and on my advice that project deleted it, so I did not read it. The size shown
here comes from the same event-log field measured on the test API. The team's first real
run is the live check.

## Tests

`tests/test_api_clarity.py`, 13 tests. The first 10 failed before the code; 3 were added
after, to close gaps the mutants would have exposed:

- record count for each answer shape (5 cases);
- a body that is not JSON has no count;
- a policy finding shows its size, and a kept folder is not reported as deleted;
- no report left behind without `--report-dir`, also when the run fails;
- the summary counts server errors, access leaks and cross-user reads apart;
- the largest 2xx answer wins, and a 404 body is ignored;
- `(empty)` and `(469 records)` wording.

## Mutants: 11 of 11 killed

List counted as 1 · object's list ignored · empty object counted as 1 · last answer,
not largest · non-2xx sizes kept · size not passed · empty worded as records · temp
kept · kept folder said deleted · cross-user counted as other · no counts.

## Full suite

220 passed (9 min), with `HEALTHKIT_OPENGREP` set. (The first run was cut off at 85% by a session restart, with no failure; the rerun passed in full.)
