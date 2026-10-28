# Slice 016 results: the API pack with real IDs and more than one user

## What exists

- `[api.parameters]` in `.healthkit/config.toml`: real values (ids) for the API check,
  `"${VAR}"` read from the environment. Written into the run's own `schemathesis.toml` in
  the report folder; must be name = text or number.
- `--token-env` may be given several times. Two or more users: a temporary auth file
  (`users.wfc.json`, removed after every run, also when it fails) listing them as peers,
  and Schemathesis's cross-user read check (`ST402`) switched on. The summary says
  "users: N (cross-user reads checked)".
- `healthkit api` now honours `[[allow]]` (rule = the check code, path = "METHOD /route").
- README: both settings.

## Measured first (in Schemathesis 4.32.5's own code, then on a test API)

- `[parameters]` works for path, query and body values, `${VAR}` included.
- The cross-user check runs **only** when the users are listed as `peers` under
  `[auth.wfc]`; without it Schemathesis prints a warning and checks nothing.

## Live: the local QuickRPA stack (owner-approved test data)

Two test organisations made with the product's own `create_tenant` (`healthkit-tenant-a`,
`-b`), each with a robot and a workflow; email on the console backend. Same API, two runs:

| | Tenant A alone, no ids | A and B, with A's real ids |
|---|---|---|
| Operations tested only on the surface | 291 | **181** (110 more reached) |
| Findings | 5 | 5 |

New, reachable only with real ids (each read in the server log):
- `PUT /api/v1/workflows/{workflow_id}` with `{"name": null, ...}` → 500 `IntegrityError`
  (the same class as the user edit).
- `POST /api/v1/organizations/{org_pk}/workspaces/` with `Content-Type: multipart/form-data`
  and no boundary → 500 "Workspace creation failed and was rolled back" (expected 400/415;
  the family of Susheel's #21, form uploads crashing JSON routes).

Cross-user (ST402), one finding, read and judged by hand:
`GET /api/v1/agents/agent/{token}/status`: tenant B read the status of an agent tenant A
created. **Not an isolation bug:** the token in the path is the credential by design
(QuickRPA's `commons/request_safety.py` calls the route "bearer-equivalent"); Schemathesis
handed B a token taken from A's response. A project accepts such a route with `[[allow]]`
(added in this slice). One real smell for the team: the route **returns the token in its
own body** (`"token": t.token`), which it does not need to.

Tokens: neither user's token appeared in any output or report file; no auth file left.
Note: reports can contain secrets the API itself returns (here the agent token, test data
only), so a report folder is as private as the API.

## Verification

- Tests first on a two-user test API (`tests/fixtures/tenant_api.py`), each shown failing.
- Mutants **9 of 9** caught (against the two API test files).
- Full suite **172 passed**; lint clean. Source: about 75 lines changed (`apicheck.py`, `tools/schemathesis.py`, `config.py`).
