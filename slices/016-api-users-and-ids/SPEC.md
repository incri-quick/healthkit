# Slice 016: the API pack with real IDs and more than one user

Status: **approved** (2026-10-28), including test users on the owner's local stack

## Measured first (Schemathesis 4.32.5, read from its own code)

- `schemathesis.toml` `[parameters]`: fixed values by name or location (`workflow_id`,
  `path.workflow_id`, `body.refresh`), with `${VAR}` read from the environment.
- A Web Fuzzing Commons auth file (`--auth-wfc`) holds several identities.
- Check `object_level_authorization`: replays one identity's read of its own object as the
  others; a success where it should be refused is a finding (cross-tenant read).
- Check `ignored_auth`: a route that declares auth but answers without it.

Slice 007's QuickRPA sweep left 305 of 479 operations tested only on the surface (no valid
IDs), and Susheel's #10 (refresh answers 500 for a deactivated account) needs a second user.

## Design

1. The project lists real values in `.healthkit/config.toml`:
   `[api.parameters] workflow_id = "${HK_WORKFLOW_ID}"`. healthkit writes them into the
   run's own `schemathesis.toml` (in the report folder, never the project).
2. `--token-env` may be given several times, one per user. With one, as today. With two or
   more: a temporary auth file in the report folder (deleted after the run, never printed)
   and the cross-identity read check switched on.
3. Findings name the check: a 500 stays `not_a_server_error`; a cross-identity read is
   reported as its own rule.

## Safety

Unchanged: local hosts only; tokens by variable name, never printed or kept; the auth file
is removed even when the run fails.

## Acceptance

- Tests first, on the crashy test API: parameters reach a route that 404s without them; two
  users, one able to read the other's object, is reported; the token never appears in any
  output or leftover file.
- Live on the local QuickRPA stack: two test users in two organisations, each with a little
  data. Count operations past the surface with and without parameters; every cross-tenant
  finding read by hand and replayed.
- Mutants; under ~200 lines of source.
