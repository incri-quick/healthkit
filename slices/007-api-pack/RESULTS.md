# Slice 007 results: the API pack, "never a 500"

## What exists

`healthkit api --schema <url|file> [--base-url] [--token-env NAME] [--max-examples N]
[--report-dir DIR] [--allow-remote-host HOST]`: sends every route generated good and bad
input through Schemathesis 4.32.5 (pinned, via `uvx`); any 500 is a finding. Local hosts
only by default; the token is read by variable name and never shown; reports go to a
report folder, never into the project.

Ride-along (own commit `8c4f76a`): `exception-text-in-reply` now catches error text inside
f-strings (AA-59) and skips `raise ... from exc` wrappers.

## Measured before coding (L-006)

| Behaviour | Consequence in the adapter |
|---|---|
| On Windows, console output crashes (cp1252) unless `PYTHONUTF8=1` | always set |
| The JSON run report lists failures by type with operations; no inputs | finding = operation + check; console log kept for `curl` reproductions |
| **No valid login: exit 0, "no failures"** (every request 401) | most operations refused → exit 2 |
| A token passed as a header is recorded `[Filtered]` | verified by a test over all output |
| It writes `.schemathesis/` and `.hypothesis/` into the folder it runs from, even in deterministic mode (and refuses `--generation-database` there) | runs from the report folder |

## QuickRPA local stack (owner's spare data, email switched to console first)

Throwaway superuser `healthkit-sweep@example.com`; token minted into an environment
variable, never printed. Email: the stack used **real Gmail SMTP**; the sweep was held until
the owner switched `EMAIL_BACKEND` to the console backend (verified in web and worker).

**479 operations, 13,652 generated requests, ~8 minutes. 6 routes answered 500**, each read
by hand from the server log via its `error_id`: **all 6 real, 0 artefacts**:

| Route | Input | Exception |
|---|---|---|
| `GET /api/v1/audit/logs` | `start_date=null` | `ValidationError` (unchecked date into the ORM) |
| `GET /api/v1/audit/statistics` | `days=1214695121413080576` | `OverflowError` |
| `GET /api/v1/robots/runs/paused/` | huge page / ids | `DataError: bigint out of range` |
| `POST /api/v1/mfa/confirm` | non-ASCII code | `TypeError: comparing strings with non-ASCII characters` |
| `POST /api/v1/nodetype` | a NUL byte in text | `DataError: unsupported Unicode escape` |
| `PUT /api/v1/users/{user_id}` | `{"is_active": null}` | `IntegrityError` (the AA-75 class, in the Studio user edit) |

Also: **18 operations answered only 401** (agent/bot token routes, MFA pending, and the
login routes themselves) and **305 had no valid sample data** (real IDs), so were tested
only on the surface. Token found 0 times in any output.

### Second run, through `healthkit api` itself (after the fixes below)

```
healthkit api --schema http://localhost:8000/api/v1/openapi.json \
  --token-env HEALTHKIT_API_TOKEN --max-examples 5 --report-dir <scratch>/qr-sweep2

GET /api/v1/audit/logs: [schemathesis ST101] Server error
GET /api/v1/audit/statistics: [schemathesis ST101] Server error
GET /api/v1/robots/runs/paused/: [schemathesis ST101] Server error
POST /api/v1/nodetype: [schemathesis ST101] Server error
not tested (refused by login): 18 operation(s)
  GET /api/v1/agents/agent/rpa-link-key
  ... (18 listed)
healthkit api: 4 route(s) answered with a server error in 479 operation(s) | shallow (no valid sample data): 304 | reports: ...
exit=1
```

Token found 0 times in stdout, stderr, the console log and the JSON report; no
`.schemathesis/` or `.hypothesis/` in the folder it ran from.

**4, not 6, and neither missing bug is fixed.** The first sweep changed the data: user
10126 (hit by the `PUT /users/{user_id}` crash) is now inactive, and the sweep user no
longer had a pending MFA setup, so both inputs were rejected before the crashing code
(listed under "schema validation mismatch"). Replayed by hand with the right state:

| Route | State set up | Answer | Exception (server log) |
|---|---|---|---|
| `POST /api/v1/mfa/confirm` | `POST /mfa/setup` first; code `"èI\x85â"` | 500 | `TypeError` at `users/services/mfa.py:222` (`hmac.compare_digest`) |
| `PUT /api/v1/users/{id}` | another active user; `{"is_active": null}` | 500 | `IntegrityError` (rolled back; user still active) |

So the run is not repeatable on a database it writes to (L-017): a lower count after a
re-run is not evidence of a fix until each missing finding is replayed.

## Bugs found while building

1. **First QuickRPA run hid all 6 crashes.** The adapter treated *any* 401 as "nothing
   tested" (exit 2). 18 of 479 operations use other login schemes. Fixed test-first: exit 2
   only when most operations are refused; otherwise the findings count, and the refused
   routes and the shallow count are printed.
2. `.schemathesis/` / `.hypothesis/` written into the user's project (fixed: run from the
   report folder; the database option was rejected by Schemathesis, whose message showed the
   real cause).
3. Windows console crash before any request (fixed: UTF-8).

## Process slip

The ride-along rule fix (`8c4f76a`) was committed before the owner saw its diff (CLAUDE.md
step 7). Reported at the time; diffs shown before every commit since.

## Lesson

One property ("never a 500") found 6 real crashes in an afternoon that no rule describes.
And a safeguard can be wrong the other way: "never a silent pass" became "never a pass",
which hid every result. Both directions need a test. Third: a tool that writes data
changes the next run's results, so comparisons need the same starting data.

## Open (not this slice)

- Restore a database snapshot before each sweep, so runs can be compared (L-017).
- 305 operations were tested only on the surface: real IDs in a config file would let
  them reach the code behind the 404.
- `POST /api/v1/users/reset-password/` was rate limited (429) on the second run.
