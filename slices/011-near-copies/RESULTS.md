# Slice 011 results: copies, cut down to what earned its place

## What happened

The spec said: measure four candidate matchers on the real cases first, then decide. The
measurement (SPEC.md, "Measured") showed outside clone tools and healthkit's own
similarity engine find only exact copies, and that most "near-copy" incidents were not
copies in shape at all. Asked "is it worth it?", the honest answer was: not the engine;
two cheap checks are. The owner agreed; the slice shipped those two (~110 lines of source).

## What exists

1. **`copy-same-name`** (`tools/copies.py`, in `review`, advisory): a private module
   function the branch adds or changes, also defined at module level in other files →
   "`_x` is also defined in N other file(s), K different version(s): a.py, b.py, ...".
   Versions are compared by arguments + body, docstring ignored. Test files and excluded
   paths never count. The finding covers the whole function, so a body edit is enough
   (new: `Finding.end_line`; the review keeps a finding when any changed line is inside it).
2. **`cache-read-modify-write`** (built-in Opengrep rule): a cache value read and written
   back + 1 (`get` → `set(v + 1)`, `get(...) or 0`, `v += 1` → `set(v)`), the same key.

## The real cases, at their dates

| Case | Check | Result |
|---|---|---|
| AA-03 (`4cf0801^`) | rule | `users/services/password_reset.py:59` flagged; the atomic `cache_incr_window` not |
| D-015 (`7fadfe3`) | same-name | "`_get_workspace_or_404` is also defined in **8 other file(s), 3 different version(s)**" |

## Precision, every finding read by hand

**Rule:** QuickRPA 2 of 2 real; mulearnbackend and micromasters 0 hits.
The second QuickRPA hit was never in any review and **is live in `dev` today**:
`studio_vault/api/vault.py:158`, `_check_decrypt_rate`, the per-user throttle on **vault
secret decryption**: get, compare, `set(key, count + 1, timeout=60)`. Concurrent requests
pass the limit, and the TTL is rewritten on every hit (the window slides).

**Same-name:** every group in each project:

| Project | Groups | Real copies | Debatable | Coincidence |
|---|---|---|---|---|
| QuickRPA (dev) | 24 | 17 | 2 (`_next_version`, `_snapshot_metadata`: same pattern, different models) | 5 (`_text`, `_is_transient`, `_coerce_int`, `_cutoff`, `_result`) |
| mulearnbackend (unseen) | 11 | 11 | 0 | 0 |
| micromasters | 0 | | | |

QuickRPA 71% (79% if debatable count); mulearnbackend 100%. Stays advisory (D-023): the
second project with findings is one, and a shared name is a question, not proof.

Worth the team's attention (QuickRPA):
- **`_client_ip`**: two copies with **opposite** behaviour. `commons/audit.py` reads
  `X-Forwarded-For` (client-controlled); `studio_mcp/auth.py` deliberately does not. The
  shared `commons.ratelimit.client_ip` exists with a trust gate.
- `_get_workspace_or_404` (9 files, 3 versions) and `_get_workspace` (4 files, 3
  versions): the tenancy check, drifted.
- `_save_field` (vault credential writes) and `_scrub` (vault-reference scrubbing in the
  two exporters): security code in two versions each.
- `_get_robot_in_workspace`: the function incident `f0a3b4e` fixed, still in 2 files.

mulearnbackend: a whole image-utilities module copied, including its SSRF guards
(`_hostname_is_blocked`, `_url_is_safe_for_fetch`).

## Dropped (with the reason)

Near-copy similarity engine (1 of 4 cases; the drifted helper scored 0.02) and the
repeated-statement view (AA-64; ~179 reports per tree). Out of reach: AA-62's third sign-in.

## Verification

- Tests first, each shown failing (the copies tests against a stub; the rule through a
  review-level test, because `opengrep test` passed the fixture with **no rule file**: a
  new test now requires every fixture to have its rule).
- A real bug the tests caught: `True` passed positionally set `suppressed`, not `advisory`.
- Mutants **15 of 15** caught, each run against the tests that exercise its file; one
  survivor on the first run (methods) led to a stronger test.
- Full suite: **131 passed** (3 min 38 s); lint clean.
