# Slice 010 results: routes nobody calls

## What exists

```
healthkit routes --schema <url|file> [--schema ...] --callers <folder|file> [--callers ...]
```

Routes come from OpenAPI (any backend language); callers are client code folders or single
files, read as text, never run. Output: `no caller: METHODS /path` per route, then
`N of M path(s) have no known caller in K client file(s) | matched per path, not per
method`. Exit 1 when any is listed, 2 when a schema or a callers folder cannot be read.
Routes called from outside (webhooks, docs) are `[[allow]]` entries, rule
`route-no-caller`, in the project's own config (D-022).

How a caller string is read (each rule from a real QuickRPA line, each with a test):
string literals only (comments and docs never count, AA-61); `${x}`, `{x}`, `%s`,
`$Api`, `$(x)`, `%X%` are placeholders; `"a/" + x + "/b"` is joined; a URL inside a
command line is found; a same-file constant is substituted (`${vaultPath}/vaults`); code
inside a `'''` template is read, docstring prose is not; tests, `node_modules`, build
output are skipped.

How it matches: a string that starts with fixed text names the route right below its API's
base (`/logout/` is `/api/v1/logout/`, never `/api/v1/auth/logout`). A string that starts
with a variable only has to match the route's end, and counts only when that end fits one
route (parameters lined up first; `/x/{slug}` and `/x/{slug}/` are one route).

## Measured first (L-006)

- Clients name the method beside the path in about 29% of path strings (322 of ~1,110 in
  the frontend): matching is per path, and the output says so.
- The frontend writes paths relative to an axios base and in template literals; the agent
  and installers use variables for scheme and host.

## The incidents: ground truth first

Schemas exported at each fix's parent (fresh container on a `git archive`), clients
archived as of that date:

| Incident | Route | Truth at that date | healthkit |
|---|---|---|---|
| AA-42 | `POST /api/v1/verifytoken/` | only in `HANDOVER.md` | **listed** |
| AA-61 | `POST /auth/logout`, `/check_refresh_token/`, `/token-encrypted/`, `/users/logout/blacklist/` | docs only; `token-encrypted` only in a JS comment | **all 4 listed** |
| AA-35 | `PATCH /users/change-password/` | **called**: `.patch("/users/change-password/", values)` in two frontend pages | not listed (correct) |
| AA-58 | `POST /api/v1/auth/login` | **called** by the agent's installer until its own fix, 6 s after the backend's | not listed (correct) |

**Recall: 5 of 5 truly uncalled routes listed; 2 of 2 called routes left alone.** Two of
the review's "unused" labels were wrong: AA-35 was a duplicate door that was in use, and
AA-58 was in use until the moment it was removed (L-020). AA-61 says "five"; the schema
shows four.

## Precision on today's QuickRPA (dev 7fadfe3)

Callers: frontend, agent, `qrlib/`, and the bot template
`studio_workflow/services/bot_export.py` (the generated bot calls the API too: project
config, not healthkit knowledge). Each sample of 20 was drawn from routes not read before,
and judged on the version **before** the fixes it led to:

| Sample | Claim right ("no caller in these clients") | Truly unused | Wrong, and the generic fix it led to |
|---|---|---|---|
| 1 | 17/20 (85%) | 17 | `$Api` in PowerShell; a URL inside a command line; a variable path prefix |
| 2 (held-out) | 16/20 (80%) | 16 | trailing-slash twins; same-file constants (×2); the bot template as a caller |
| 3 (held-out) | 18/20 (90%) | 17 (+1 fetched from docs) | a caller's `{}` should line up with a parameter first (×2) |

Above the 70% bar each time: this check is not advisory. Today: **100 of 401 paths have no
known caller** (full list: `quickrpa-no-caller-2026-10-27.txt`). A listed route is a
question for the team, not a verdict to delete.

Worth the team's attention:
- `PATCH /api/v1/users/me/updateprofile/`: the AA-75 crash route; no client calls it.
- `/api/v1/environments/{id}/recovery-key/import*`: unscoped doors the frontend's own
  comment says read the id as a workspace; the frontend uses the organisation-scoped ones.
- `POST /api/v1/media/upload-to-storage`: the agent's upload node calls
  `/media-api/v1/upload-to-storage`, a path this backend does not serve.
- The new `PATCH /api/v1/workflows/{id}/session-mode` (2026-10-26): no client yet.

## Known limits

- Per path, not per method: a GET caller does not prove the PATCH on that path is used.
- A path built from a function's result (`${ROBOT_ENV_URL(id)}/x`) or a variable from
  another file is read only by its end, which may be ambiguous.
- UI route strings that mirror API paths can credit an API route (errs towards "called").
- Strings without a `/` (`get("health")`) are ignored.

## Verification

- Full suite: 121 passed (before the two test fixes below); route tests: 13 passed.
- Mutants: **17 of 17 caught**, run against `tests/test_routes.py` (every mutant is in
  `routes.py`, which only those tests exercise; the full-suite run per mutant took ~3.5 min
  each and was stopped at mutant 4, which it had left applied: restored and checked).
- The first route-only run found 2 survivors, both weak tests: the test-file fixture used a
  literal id that could never match a parameter, and the `force` delete line shared a test
  with its trailing-slash twin. Both tests rewritten; then 17 of 17.
