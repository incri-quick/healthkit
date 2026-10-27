# Slice 010: routes nobody calls (D-021 step 4, part 1)

Status: **approved** (2026-10-27), including decisions 1-3

## Goal

List the API routes that no client calls. A route nobody calls is code to maintain, a door
to attack, and often a second copy of a door that is used. In the replay these were 4 of
the 13 "knowledge" misses: AA-35 (`PATCH /users/change-password/`), AA-42
(`POST /verifytoken/`, which also gave wrong answers), AA-58 (a second, unused Studio
sign-in), AA-61 (five auth routes with no caller). No tool in slice 001 can see this:
static dead-code tools count a route registered by a decorator as used.

## Design (generic, any backend with an OpenAPI description, D-022)

```
healthkit routes --schema <url|file> --callers <folder> [--callers <folder> ...]
```

- **Routes** come from the OpenAPI description (the API pack's input, any language).
- **Callers** are folders of client code: a web frontend, a desktop agent, a bot SDK,
  scripts. healthkit only reads their text; nothing is run.
- **A route is "called" when some caller file contains its path**, matched by its fixed
  parts: `/robots/{pk}/export/` matches `` `/robots/${id}/export/` ``,
  `"/robots/" + id + "/export/"`, or `'/robots/%s/export/' % id`. A base prefix the
  clients keep in one constant (`/api/v1`) is not required in the same string.
- **Output:** one line per uncalled route (method and path), and a summary
  ("N of M routes have no known caller in K files"). Exit 0 / 1 / 2 as elsewhere.
- **Project knowledge stays in the project** (D-022): routes called from outside
  (webhooks, OAuth callbacks, health checks, a public API) are `[[allow]]` entries with a
  reason, rule `route-no-caller`, path = the route.
- Whole-API and multi-repo: a separate command on the slow path (D-014), not in `review`.

## Failure modes (each gets a test)

1. A caller folder that does not exist or holds no files → exit 2, never "every route
   unused" or "none".
2. A schema that cannot be read → exit 2.
3. Path parameters written any of the ways above → matched.
4. A route whose fixed parts appear only as a longer path (`/robots/` inside
   `/robots/{pk}/run/`) is **not** counted as called by that longer one.
5. Methods: a path called with GET does not prove the PATCH on it is used. **Measured
   first**: if clients do not show the method near the path often enough to tell, the check
   works per path and says so in its output.
6. Caller files in `node_modules`, build output, or the backend's own tests do not count.

## Tests from real cases

At each fix's parent, with the client repos as they were on that date (read with
`git archive`, the repos untouched): the routes retired by `11bfaa9` (AA-35), `3a6ed4c`
(AA-42), `2e01db0` (AA-61) and AA-58's sign-in must be listed; a route the frontend
really calls must not be. Fixtures are real lines from the frontend and agent.

## Acceptance

- Tests first, shown failing; green; mutants.
- **Precision on today's QuickRPA** (frontend + agent + `qrlib/` as callers): every listed
  route classified (truly unused / called from outside / missed caller), 20 read by hand.
  Below 70%: advisory (D-023).
- Recall on the four incidents above, stated as found / missed.
- Under ~300 lines of source (D-016).

## Needs approval

1. **Routes from OpenAPI, callers by text search** in folders you name: generic, no
   project code run.
2. **A separate command** (`healthkit routes`), not part of the pre-push gate.
3. **For QuickRPA:** callers = frontend, agent, `qrlib/`, read-only; history read with
   `git archive`, never a checkout in your repos.
