# Slice 007: the API pack, "never a 500"

Status: **approved** (2026-10-27), including decisions 1-5

## Goal

Catch crashes on bad input **without writing a rule per bug** (D-017, D-021). healthkit
reads an API's OpenAPI description, sends every route well-formed and malformed input
(wrong types, huge strings, nulls, form bodies, broken JSON) through Schemathesis, and
reports every server error (5xx) as a finding with a reproduction.

In the replay (slice 006) this is the layer that would have caught AA-73 (a form upload
crashed 86 routes) and AA-75 (any type stored as a name), and possibly AA-40. No gate
rule can.

Also rides along (small, D-021): `exception-text-in-reply` misses error text inside an
f-string (`f"...{str(e)}"`, AA-59).

## Out of scope

The agent API (no schema, by design), running in the pre-push gate (too slow: D-014),
stateful multi-step scenarios (create then delete), auth flows beyond one bearer token.

## Design

- **A separate command:** `healthkit api --schema <url-or-file> --base-url <url>`. Whole
  API, slow path (D-014), not part of `review`.
- **Language-agnostic:** any backend with an OpenAPI description (D-004's API pack).
  healthkit never imports the target's code.
- **Schemathesis** runs as a pinned outside tool (`uvx schemathesis@<version>`), like ruff:
  not a healthkit dependency. Its output is converted to `Finding`s:
  `api: POST /api/v1/users/me/updateprofile/ -> 500 (body: {"first_name": 123})`.
- **Measure first (L-006):** capture Schemathesis's real report format, exit codes, and
  how it reports a run it could not complete, before writing the adapter.
- **Auth:** one bearer token, passed by the *name* of an environment variable
  (`--token-env HEALTHKIT_API_TOKEN`). healthkit never prints, logs or stores the value.
- Exit codes as `review`: 0 no 5xx found, 1 findings, 2 could not check.

## Safety (this slice sends real requests that create, change and delete data)

1. **Local targets only by default:** `localhost` / `127.0.0.1` / `::1`. Any other host is
   refused (exit 2) unless `--allow-remote-host <host>` names it explicitly.
2. **Never against a shared or production server.** The QuickRPA run uses a local stack
   with a throwaway database.
3. The token is read from the environment and never echoed; reports never contain it.
4. A request budget (`--max-examples`) and a time limit, so a run cannot go on forever.

## Failure modes (each gets a test)

1. Schema URL unreachable or not OpenAPI → exit 2, never "0 findings" (L-004).
2. A non-local base URL without `--allow-remote-host` → exit 2 before any request.
3. Schemathesis missing or crashing → exit 2.
4. A route that returns 500 on a wrong type → finding with method, path, input.
5. The same route failing many ways → one finding per route and status (no flood).
6. The token never appears in output, even when Schemathesis echoes headers.
7. Authentication fails (401 on everything) → reported as "could not check", not as a pass.

## Tests from real cases

A tiny local test API (standard library only, no framework) reproducing:
- **AA-73**: a JSON route that crashes (500) when sent a form upload.
- **AA-75**: a route that crashes when `first_name` is a number or 10,000 characters.
- A correct route that returns 400/422 for bad input → **no** finding.
Plus the f-string fixture from QuickRPA `2e01db0^:users/api/users.py:344` for the rule fix.

## Acceptance

- Tests first, shown failing; green; mutants (5xx detection, local-only check, token
  redaction), caught on green code.
- **QuickRPA local stack** (owner starts it; throwaway database): output pasted; every 5xx
  read by hand: real crash or harness artefact.
- Under ~300 lines of source (D-016).

## Needs approval

1. **URL-based and language-agnostic**, rather than loading Django in-process. Generic,
   but needs a running server.
2. **Local-only by default**, with an explicit flag for any other host. Never production.
3. **Schemathesis as the engine**, pinned and run through `uvx`; measured before coding.
4. **The QuickRPA run needs your local stack running with a throwaway database.** The
   sweep will create, change and delete records there. Which local stack, and who
   starts it, is your call; I will not start or reset anything without asking.
5. The f-string rule fix rides along in this slice as its own small commit.

## Lesson this slice teaches

Some bugs are found by a property ("the server never answers 500"), not by a rule. One
property covers bugs nobody has written down yet.
