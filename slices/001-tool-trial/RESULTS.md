# Slice 001 results

Snapshots: QuickRPA backend **dev = `7fadfe3`** (1,390 .py) and
**pre-review = `220f7b3`** (`49d5dc8^`, 1,323 .py).
Raw outputs: `raw/` (local only, git-ignored). Harness: `measure.py`, `peek.py`, `sample.py`.

## ruff 0.17.2 — **KEEP**, with a curated rule set

| Measure | Result |
|---|---|
| Install | `uvx ruff@0.17.2`, native Windows, no problems |
| Run time | 0.5–0.8 s per snapshot |
| BOM files, folder with spaces | handled; no errors |
| Output | JSON (also SARIF) |
| Findings, default rules | dev 6,032 / pre 5,893 |
| Findings, our rule families* | dev 7,849 / pre 7,718 |

\* `F,I,N,BLE,C90,PLR2004,PLC0415,PLC2701,RUF052,S,DJ` with `--preview`.

**Defaults changed.** ruff 0.16 (July 2026) raised the default rule set from 59 to
413 rules; 0.17.2 enables 407. See LEARNINGS L-002.

### Sample of 19 findings in app code (2 per top rule): 9 real, 10 false alarms (47%)

Real: `I001` x2, `F401` x2, `RUF052` x2, `BLE001` x2 (real under D-010's
bare-except rule), `C901` x1 (better as a scorecard signal).
False alarms: `PLC0415` x2 (deliberate lazy imports; 3,758 hits), `PLR2004` x2
(tooling script; HTTP code in a test), `S106` x2 (test token; a message argument),
`S310` x1 (fixed https URL), `C901` x1 (tooling script), `N802` x2 (settings
convention; deliberate test name).

Every false alarm came from **rule choice or scope**, none from ruff misreading code.

### Replay: did it flag what Susheel later fixed? (pre-review snapshot)

| Susheel's fix | ruff at pre-review |
|---|---|
| `ca5c64e` `_password`, `_ip`, `_db_counter` used as normal variables | **yes**: `RUF052` users/api/users.py:247, 251, 343 |
| `198494c` dead login code "that would accept the wrong tokens" | **yes**: `F821` undefined `api_settings` at users/api/users.py:1459/1469/1473 (the code could never have run), plus `N806` for `for AuthToken in ...` |
| `81ca762` `AccessToken as _AT` alias | **yes**: `N814` users/api/users.py:1404 |
| AA-63 / AA-06 private helpers imported across modules | **partly**: `PLC2701` flags private imports (studio_workflow/api/auth.py:112, 180; users/api/users.py:1309), lost among 3,700+ `PLC0415` hits |
| `1f78697` import order in login / password-reset services | **yes**: `I001` |
| AA-15 `except Exception` turned into `str(exc)` reply | **flagged as blind except** (`BLE001` password_reset.py:223); the `str(exc)` leak itself needs our own rule |
| AA-65 raw JSON body reads, AA-75 profile-name validation, all security/logic bugs | **no** (as expected; project rules and behaviour tests) |

### Side finding: live bugs in today's dev (not healthkit work)

`F821` undefined `logger` in `studio_workflow/execution/execution_engine.py:811` and
`:4873`. Both are inside `except` blocks; `logger` is only defined locally elsewhere
(lines 1229, 4919). When those error paths run, the warning itself raises
`NameError` and replaces the original error. Third hit (`"NodeExecution"` in a quoted
type hint, :4806) is harmless at runtime. Reported to the owner; not fixed here.

### Verdict

**Keep ruff**: fast, native, no crashes, and it reproduced several of Susheel's
cleanup findings plus two live bugs. The gate must use a **curated rule set**, not
the defaults and not "everything":

- Gate: `F821`, `F401`, `F811`, `I001`, `RUF052`, `N806`, `N814`, `PLC2701`, `BLE001`
- Scorecard only (not blocking): `C901`
- Off: `PLC0415` (deliberate lazy imports in Django)
- Off in tests: `PLR2004`, `S105`/`S106`
- Exclude tooling folders (`.claude/`) from product scans

## Opengrep 1.32.0 — **KEEP the engine; DROP the community rules**

| Measure | Result |
|---|---|
| Install | Native signed Windows build `opengrep_windows_x86.exe` (answers O-5). sha256 `ae715280…6826a5e`. Signature verified with `uvx sigstore verify github` (the `.cert` asset is base64-wrapped PEM; decode first) |
| Run time | Our 2 rules: 7–10 s. All 334 community Python rules: 72–83 s |
| Output | JSON (also SARIF) |
| Rule tests | `opengrep test` works with `# ruleid:` / `# ok:` fixtures. A deliberately broken rule failed its test (missing line 31), so a pass means something. Failure output is poor ("TODO: print(check_output_lines)") |

### Our own probe rules (`probes/`), fixtures from real incidents

| Rule | Pre-review (`220f7b3`) | Dev (`7fadfe3`) |
|---|---|---|
| `raw-json-body` (AA-65) | 12 hits: 11 in users/api/users.py + agent_api.py:435 | 3: commons/payload.py:54 (the shared reader itself: allow-list), users/api/users.py:572 (deliberate sign-out exception: allow-list), **agent_api.py:435 (a real copy still left)** |
| `exception-text-in-reply` v1 | 37 | 35; only ~4 of 25 app hits real (~16%): **failed the bar** |
| `exception-text-in-reply` v2 (built-in exceptions only) | 19, incl. **AA-15 password_reset.py:224** and **vault/services.py:115** (fixed later in `f0a3b4e`) | 8 app hits: 4 clearly real (storage_buckets/services.py:164, :288; reports/tasks.py:315; telegram_registration.py:62), 3 `ValueError` real-but-low, 1 false (utils.py:113 re-raise) |

v1 → v2 was done test-first: the real false alarm (`except SeatLimitExceeded` →
`HttpError(402, str(exc))`) was added as an `ok` fixture, shown failing, then the
rule was narrowed with a `metavariable-regex`. No existing expectation changed.

### Community rules (`opengrep-rules` @ `f1d2b56`, 334 Python rules)

- **Licence: Commons Clause.** It forbids selling a product or service whose value
  derives substantially from the rules, consulting and support included. healthkit
  must not bundle them.
- Dev: 640 findings (340 app code), 18 rules firing; 200 of those from
  `is-function-without-parentheses`, all noise (model fields, not functions).
- Sample of 20 in app code: **5 real (25%)**. Real: Django null conventions x3,
  one trivial FK access, one `open()` without encoding.
- **Timed out on the 4 largest files** (studio_workflow/api/workflow.py,
  studio_robot/api/robots.py, organization/api/organization.py, a seed command):
  the most important files were not analysed. Our own rules had no timeouts.

### Verdict

**Keep Opengrep as the engine for our own rules**: native on Windows, signed,
fast on targeted rules, real test support, and two short rules reproduced AA-15,
AA-65 and a later vault fix. **Drop the community rules**: 25% real, a licence we
cannot ship, and timeouts where it matters.

Lesson from the probe: a rule's first draft is a hypothesis.

## import-linter 2.15 — **KEEP**

| Measure | Result |
|---|---|
| Install | `uvx --from import-linter==2.15 lint-imports`, native Windows |
| Run time | 0.7–1.0 s (1,002–1,079 files, 2,560–2,780 dependencies) |
| Config | One contract file passed with `--config` (`probes/importlinter.ini`); target repo untouched |
| Output | Text only (no JSON/SARIF): **needs a small parser in its adapter** |
| Sees imports inside functions | Yes, which is where this codebase hides its layer breaks |

**Contract:** layers `api` above `services` in 6 apps (from AA-06).

**Prediction written before the first run:** pre-review fails with
`users.services.login -> users.api.users`; dev does not. **Confirmed exactly**
(pre: line 169; dev: gone).

**Also found, still in dev (4 of 4 real):** `studio_robot.services` reaches its own
route file through chains whose last links import **private helpers from route files**:
`studio_robot/watchdog.py:410` (`_trigger_resume`),
`studio_robot/run_readiness.py:159` (`_get_active_version_setup_metadata`),
`studio_workflow/api/workflow.py:4027` (`_provision_robot_vaults`, across apps),
`studio_workflow/consumers.py:327` (`workflow_tenant_org`). Same pattern as AA-06 /
AA-63; the refactor done for `users` is still pending in `studio_robot`.

**Blind spot found:** `studio_workflow/services/` has no `__init__.py` (an accidental
namespace package), so import-linter rejects it as a layer and the largest app could
not be checked. A scorecard signal in its own right.

**Verdict: keep.** Exact on the known incident, 4/4 real on new findings, under a
second. It is the precise version of ruff's noisy `PLC0415` (3,758 hits): only the
imports that break a layer. Note for the adapter: text output, and namespace
packages must be reported, not silently skipped.

## pyscn 1.33.0 — **KEEP for the scorecard; not the gate's clone or dead-code finder**

| Measure | Result |
|---|---|
| Install | `uvx pyscn@1.33.0`, native Windows |
| Run time | 58–61 s for all analyses |
| Target untouched | Yes, with `--json --output -` (by default it writes `.pyscn/` into the target) |
| Output | JSON, 27 MB per run: complexity, clones, coupling (CBO), cohesion (LCOM), module dependencies, per-module quality, health score (dev: 86/100, B) |
| Default scope | 713 files: excludes tests and migrations (sensible) |

**"Dead code" means unreachable lines only** (after return/raise/break). It reported 0
at pre-review, where unused functions and `TenantMiddleware` existed. Not a
replacement for an unused-code finder.

**Clones: precise for exact copies, blind to near-copies.** All 9,436 pairs were
Type-1 (exact), although Type-2/4 are enabled. Run on just the four auth files (67
fragments, no approximate matching) it still found only one exact pair:
`obtain_token` vs `obtain_token_encrypted` failure handling (users/api/users.py
275-287 / 352-364), the duplicate sign-in routes later merged (AA-61/62). It missed
the near-copies Susheel fixed: change-password vs `apply_password_set` (AA-04), the
Studio sign-in (AA-58), cookie clearing (AA-64), and the 4-line JSON readers
(below its 8-line minimum).

**Dev app code: 18 exact-clone pairs (most of the 9,436 are node packages,
duplicated by design). Sample of 8: 7 real.** The big one:
`_get_workspace_or_404`, a tenancy check, exists in **9 route files in 3 different
versions** (6 identical, 2 of another, 1 with arguments swapped:
studio_agent/api/agent.py:598). pyscn found the 6 identical copies; the 3 drifted
ones needed a name search.

**Verdict: keep for the scorecard** (complexity, per-module quality, coupling, exact
clones; one JSON run gives most of M7's data). **Not enough for the gate:** near-copy
detection is the capability our #1 problem needs, and it did not deliver it here.
Exclude `packages/` (by-design duplication) and `tests.py` files.

## Skylos vs vulture — prediction written before running

Known dead code at pre-review (`220f7b3`), deleted later in `198494c` / `3eebb3f`:

| Symbol | References at pre-review | Expected |
|---|---|---|
| `CustomJWTAuthentication` (users/Authentication.py) | none | **both find it** |
| `token_session_auth_hash_is_valid`, `get_session_auth_hash_digest` (config/tokens.py) | only from dead code and an import | vulture misses (sees a reference); Skylos finds it **if** its "transitive" claim holds |
| `_get_validated_token`, `_get_user_from_token` (users/api/users.py) | none, but live functions with the **same names** exist in users/services/password_reset.py | vulture misses (name-based); Skylos unknown |
| `TenantMiddleware`, `_extract_org_id` | named in settings/base.py: it runs, its output is unread | **both miss**, correctly: useless is not unused |

## vulture 2.16 — **DROP**

| Measure | Result |
|---|---|
| Run time | ~10 s per snapshot |
| Output | Text lines (`path:line: unused X 'name' (NN% confidence)`) |
| Findings | dev 2,329 (1,522 in app code); 98% at the lowest confidence (60%) |
| Prediction | `CustomJWTAuthentication` found ✓; transitive and same-name cases missed ✓; **`TenantMiddleware` flagged ✗ (prediction wrong)**, because vulture ignores the settings string that registers it: right answer, wrong reason |
| Sample of 20 (app code) | **3 real (15%)**: an unused schema, an unused method, an unused import. Every sampled "unused function" was a live Ninja route; the rest were admin options, AppConfig, Meta, schema fields, Channels handlers, a model field |

Usable only with a hand-kept allow-list of every Django/Ninja/Channels convention.

## Skylos 5.1.0 — **KEEP, with `--no-grep-verify`, whole-repo runs only**

| Measure | Default | `--no-grep-verify` |
|---|---|---|
| Run time | 318–327 s (over the 5-min bar) | **175–200 s** |
| Reported unused functions / classes (dev) | **0 / 0** | 121 / 438 |
| Why | Its grep verification hit a 120-second budget, verified none of ~2,500 candidates, and **reported none** | |

Never uploads with `--no-upload`; wrote nothing into the target. JSON ~122 MB.

**Prediction check (pre-review, `--no-grep-verify`):** reports `CustomJWTAuthentication`
(90) ✓ and **both same-name traps** `_get_validated_token` (80), `_get_user_from_token`
(70) ✓, which vulture cannot tell apart from the live functions of the same name.
Correctly leaves `TenantMiddleware` alone (understands settings). Misses the
transitive pair, despite the "transitive" claim. **3 of 5 dead symbols vs vulture's 1.**

**Sample of 20 in dev app code: 14 real (70%).** Real: `subscription_action`,
module-level `broadcast_status`, `get_multi_for_workflow`, `IsAgent`, 4 unused schemas,
3 unused variables, 3 unused imports. False: calls through `self.` missed
(`_permission_expressions`, `_record_gate_call`), a direct call missed
(`invalidate_top_robots_cache`, analytics/cache.py:361), a polymorphic method, 2 test
classes in `tests_*.py` files.

**Verdict: keep** for whole-repo dead-code runs (nightly / on demand), with
`--no-grep-verify`, excluding `tests_*.py`. Not in the pre-push gate (3 minutes).
Worth a later look: `skylos done --base <branch>` claims to flag deleted tests and
loosened CI, which overlaps rule family 5.

---

## Summary: keep / drop

| Tool | Verdict | Where it runs | Real in sample | Reproduced known findings |
|---|---|---|---|---|
| ruff 0.17.2 | **keep**, curated rules | gate (changed files) | 47% raw; false alarms all from rule choice | `RUF052`, dead login code (`F821`), `_AT`, imports, bare except |
| Opengrep 1.32.0 | **keep engine**, own rules only | gate | own rule v2: 4–7 of 8 | AA-15, AA-65, a later vault fix |
| Opengrep community rules | **drop** | — | 25%; Commons Clause; timeouts | — |
| import-linter 2.15 | **keep** | gate | 4 of 4 | AA-06 exactly |
| pyscn 1.33.0 | **keep for scorecard** | whole repo | exact clones 7 of 8 | duplicate sign-in block; tenancy helper x6 |
| vulture 2.16 | **drop** | — | 15% | 1 of 5 dead symbols |
| Skylos 5.1.0 | **keep** (`--no-grep-verify`) | whole repo | 70% | 3 of 5 dead symbols |

**Open for the design:** near-copy detection still needs a solution. Candidates:
same-name functions across modules (that found the 3 drifted tenancy helpers),
and project rules that require the shared function. Run it on real code,
then narrow it test-first.
