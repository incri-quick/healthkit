# Slice 019: every user tested, and reads only unless asked

Status: **approved** (2026-10-29: "sure proceed" on the fixes from the school project's review)

## Why (a real outside test, 2026-10-28)

Another project ran `healthkit api` with two users (teacher, admin). It found 26 crashing
routes and a broken feature, and showed two flaws:

1. With two users, only the first was fuzzed; the second was used only for the cross-user
   comparison. 82 admin-only operations were never tested. Not documented.
2. It wrote destructively with no warning and no way to only read: it deactivated a user,
   reversed a payment and overwrote records.

## Measured first (Schemathesis 4.32.5, a scratch API that logs every request)

- `--include-method GET` alone is **not** read-only: the coverage phase still sent DELETE,
  POST, PUT, PATCH, TRACE (its "is this method refused?" probes), including a DELETE on a
  real delete route.
- `--include-method GET` plus `[phases.coverage] unexpected-methods = []`: **only GETs**
  reached the server, with the coverage and fuzzing phases still running.
- `--auth-wfc-user NAME` picks which auth-file identity is fuzzed.

## Design

1. **Reads only by default**: GET operations only and no method probes. The summary says
   "reads only". `--allow-writes` tests everything and the summary says it changed data.
2. **Every user fuzzed**: one run per `--token-env`, each identity named by its variable
   (`HK_ADMIN`), all listed as peers for the cross-user check. A finding names the users who
   hit it.
3. **Refused counted per user**. One user: as before (most operations refused = the token
   failed, exit 2). Several users: exit 2 only when a user's token works on nothing; a
   low-privilege user refused on most routes is normal and only listed.
4. README: both, plainly, including that writes change data.

## Tests

On a test API that logs every method: the default sends only GETs; `--allow-writes` sends
writes; with two users a crash only the second user can reach is found; refused routes are
listed per user; a token that works on nothing is exit 2. Mutants.
