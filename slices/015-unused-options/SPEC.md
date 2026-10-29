# Slice 015: options nobody sets

Status: **approved** (2026-10-28)

## Measured first

Susheel's #23 (AA-09, `beb9780`): `complete_login(..., enforce_mfa=True)` and
`apply_password_set(..., blacklist_refresh=True)` were switches no caller ever passed: the
"off" paths (no MFA, old sessions kept) were dead code and a bypass waiting to be used.

A prototype (scratch) that lists options with a default that no call in the repo passes:

- at `beb9780^`: **both switches found** (`enforce_mfa`: 3 calls; `blacklist_refresh`: 6).
- today's QuickRPA: 89 options; every 4th read by hand: **14 of 20 real**, 4 not (2 in the
  bot SDK `qrlib`, whose callers are outside the repo; 2 signatures a framework dictates),
  2 debatable. 70% (80% at most).

Skylos (unused functions) is not in this slice: whole repo only, ~3 minutes, a 122 MB
report (slice 001).

## Design

- In `review` and `scan`, advisory (D-023): a function option (a parameter with a default)
  that **no call in the project passes**, by keyword or by position.
- Calls are found by name across all project files, tests included (a test that sets an
  option is a caller). A function never called by name (a route, a hook) is skipped; so is
  one called anywhere with `*args` or `**kwargs` (cannot tell).
- The finding covers the signature: adding or changing an option shows it; an edit in the
  body does not.
- A project marks outside-called code (an SDK) with `[[allow]]`, rule `option-never-passed`.

## Tests

The AA-09 switch; passing by position or keyword counts; `*args`/`**kwargs` callers and
never-called functions are skipped; tests count as callers; functions in tests are not
checked; signature edits show it, body edits do not; an unparsable file is exit 2. Mutants.
