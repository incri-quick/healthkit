# Slice 022: how big was the leak, no personal data left behind, counts per kind

Status: **approved** (2026-10-29: "proceed", the LAST upgrade before healthkit goes to the
team; then the review gate is tested in real use)

## Why (the school project's slice 021 run, 76/100)

1. A 200 with empty data looked the same as a real leak: that project's AI probed every
   `must-refuse` finding by hand to tell "469 parents' details" from "an empty list".
2. The report folder held real personal data (every response, 469 parents' details) and
   stayed in the temp folder after the run.
3. "40 routes failed" mixed crashes, access leaks and cross-user reads.

## Measured first (Schemathesis 4.32.5, the test API)

The event log keeps each response body as `{"$base64": ...}` under `response.content`.
Decoded, it is the JSON the API answered.

## Design

1. A `must-refuse` finding says how big the largest 2xx answer was:
   `HK_TEACHER got 200 (469 records)`, or `(empty)`. Records: a JSON list counts its
   items; an object with a list inside (`{"items": [...], "total": 469}`) counts the
   longest list; any other object is 1 record; `{}` and `[]` are empty. A body that is
   not JSON shows no size. Only the count is printed, never the data.
2. Without `--report-dir`, the temp report folder is deleted when the run ends,
   failed runs included. The summary says so. With `--report-dir` the folder is kept,
   as asked.
3. The summary counts per kind: `server errors`, `access leaks`, `cross-user reads`,
   `other`, each only when non-zero.

## Tests

Unit: the record count for each body shape. On the test API: a policy finding shows its
size; with no `--report-dir` no report folder is left, also when the run fails; the
summary counts each kind. Mutants.
