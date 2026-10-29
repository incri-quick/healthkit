# Slice 019 results: every user tested, and reads only unless asked

## What changed

- `healthkit api` sends **only GET requests** unless `--allow-writes` is given. The
  summary says `reads only` or `writes on: this run may have changed data`.
- **One Schemathesis run per `--token-env`**, each run as that user (`--auth-wfc-user`),
  with every user listed as a peer for the cross-user check. Each user's run has its own
  folder under the report dir. A finding names the users who hit it:
  `GET /report: [schemathesis ST101] Server error (as HK_TOKEN_B)`.
- **Refused routes are listed per user**, and now include 403 as well as 401 (see below).
- One user: most routes refused means the token failed, so exit 2 (unchanged). Several
  users: exit 2 only when a user's token works on **nothing**.
- The same `--token-env` given twice is an error. The remote-host refusal message no
  longer claims the default run changes data.

## Found while building (measured, not in the spec)

Schemathesis's own `missing_auth` warning counts **401 only**. A plain user answered
403 on an admin route was silently counted as tested. That is exactly the school
project's case: a teacher token on admin routes. healthkit now also reads Schemathesis's
event log (`--report ndjson`), which records every response's status:

- A route counts as refused for a user if every request that carried that user's login
  got 401 or 403.
- Requests Schemathesis sends with no login on purpose (they carry no `Authorization`
  header) are ignored.
- Checked first: the log stores the token as `"[Filtered]"`. No token value is in it.

## Tests

`tests/test_api_safety.py`, 7 tests, against `tests/fixtures/tenant_api.py`. That test API
now has a POST route, an admin-only `GET /report` (user a gets 403, user b crashes it), and
an optional log of every request's method.

- default run: only GETs reach the server; `--allow-writes`: POST does;
- two users: the crash only the second user can reach is found and names that user only;
  the cross-user read (ST402) is still found;
- refused listed per user (user a's 403 on `/report`), none for user b;
- a token that works on nothing: exit 2, naming its variable;
- unit: with several users a plain user refused on 3 of 4 routes is fine, alone it is exit 2;
- unit: no-login probe requests are never counted as refusals.

Existing tests: slice 007's crashing routes are POSTs, so its helper now passes
`--allow-writes`. Slice 016's "accepted route" test also accepts the new `/report` crash,
which is not that test's subject.

All 7 tests failed before the code change.

## Mutants: 8 of 8 killed

Only the first user fuzzed · no GET filter · method probes left on · 403 not counted as
refused · the one-user majority rule used for several users · no-login probes counted ·
writes always on · users not named in findings.

## Live run

Not run on QuickRPA: its local stack was down, and the only stack running is the school
project's, which belongs to that project. The live proof is the school project's rerun
(planned next): reads only, admin and teacher tokens, and the admin-only operations should
now be tested.

## Full suite

193 passed (8 min), with `HEALTHKIT_OPENGREP` set.
