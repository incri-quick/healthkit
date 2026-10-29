# Slice 006 results: the replay test

## The number

For each of Susheel's users/auth review findings with an explicit fix, healthkit (as of
slice 005) was run on the code **just before the fix**, on the whole Python files the
fix touched. 45 findings scored (4 test-only findings excluded).

| | Score | |
|---|---:|---|
| **Score B** (judged; rules written from these incidents excluded) | **9 / 45 (20%)** | the number to quote |
| Score A (judged; all rules) | 11 / 45 (24%) | |
| Raw line overlap | 29 / 45 | **not a score**: mostly coincidences |

Estimate before measuring (slice 001 discussion): ~27% found. Measured: 20-24%.

| Kind (D-017) | B / A / scored | Reading |
|---|---|---|
| pattern | **8 / 9 / 12** | healthkit's home ground |
| structure | 0 / 1 / 1 | only the contract written from AA-06 itself |
| knowledge | 0 / 0 / 13 | needs project-aware guards (Susheel's kind) |
| behaviour | 1 / 1 / 15 | out of scope by design; other layers |
| judgement | 0 / 0 / 4 | naming meaning, placement, wording |

## Caught (judged)

AA-13 `_pca` (RUF052) · AA-15 catch-all turned into the reply (BLE001 pointer; plus the
derived Opengrep rule) · AA-19 import hygiene (I001) · AA-32 dead code (F821) · AA-59
decryption error echoed (BLE001 pointer) · AA-63 private helpers imported from the route
file (PLC2701) · AA-67 `_password`/`_ip` (RUF052) · AA-69 `AccessToken as _AT` (N814) ·
AA-74 the swallow that hid revocation (BLE001 pointer). Derived-rule only: AA-06, AA-65.

## How the number was kept honest

1. **Coincidences removed by hand.** The first run counted any finding on a changed line:
   29/45. Reading the flagged lines showed most were unrelated (an unused import inside a
   behaviour fix; findings inside whole routes the fix deleted). Each AA now counts only
   with a rule that names the problem or points at the exact line where it is visible;
   every judgement is in `aa-fixes.toml` `[judged]` with the line it rests on.
2. **Contamination, two levels.**
   - Three rules were written *from* these incidents (AA-15, AA-65, AA-06): excluded from
     Score B.
   - **The ruff gate rules themselves were chosen in slice 001 partly by checking which
     ones hit Susheel's fixes** (RUF052 from `ca5c64e`). So even Score B is not fully
     out-of-sample. The clean test is his **next** module.
3. **Answer key corrected from the source:** Susheel's own message on `e65d779` says AA-63
   was resolved by removing the Studio sign-in, so `6834f76` was added to its fixes.
4. AA-36+ are known only from commit messages; their "kind" is a judgement from those.

## What the misses say: the rule backlog

| Gap | AAs | What would catch it | Effort |
|---|---|---|---|
| **Rule bug:** `exception-text-in-reply` misses text inside an f-string (`f"...{str(e)}"`) | AA-59 | widen the Opengrep pattern; fixture from 2e01db0^ users/api/users.py:344 | small |
| Hard-coded limits in `check_rate_limit(...)` | AA-66 | project Opengrep rule (literal ints in that call) | small |
| Spelling in user-facing strings | AA-68 | a spell-check tool (e.g. codespell) in the gate | trial needed |
| Missing docstrings / type hints | AA-20 | ruff `D`/`ANN` exist; not in the gate set (noise vs value) | decision |
| **Copies of a shared helper** (near-copies) | AA-03, AA-04, AA-62, AA-64 | D-015, still open; same-name search found the drifted tenancy helper | medium |
| Token types read outside their door | AA-01, AA-02, AA-27, AA-36 | Susheel's `auth_source_guard` (QuickRPA) already does this as a test; a healthkit knowledge-rule pack could host it | medium |
| Routes nobody calls | AA-35, AA-42, AA-58, AA-61 | cross-repo route-usage check (backend routes vs frontend/agent calls); logs stay human | medium |
| Flag arguments nobody passes | AA-09 | call-site analysis | larger |
| **500s on bad input** | AA-40, AA-73, AA-75 | **the API pack ("never a 500")**: no rule per bug needed | next slice |
| Races, limits, intent, wording | AA-26, 33, 37, 41, 43, 44, 47, 48, 50, 56, 60, 74 (partly) | tests, QA, people (D-017) | n/a |

## Verification

- Harness logic: 3 tests on real QuickRPA diffs (old-side lines; insertion window).
- The run is reproducible: `uv run --project . python slices/006-replay/replay.py <clone> <worktree>`
  (~2.5 minutes), giving `replay-output.md`.
- **A fresh agent re-derived 5 rows by hand, pasting its command output for each**
  (the stricter L-010 brief worked): AA-13, AA-59, AA-74 caught; AA-37, AA-03 missed.
  **5 of 5 agree.** One imprecision in its report, checked: for AA-37 it said no F401 sits
  on a changed line, but it scanned only `commons/token_auth.py`; the harness's F401 is
  `from ninja.security import HttpBearer` at `users/api/users.py:18`, an unused import in
  the import block the fix edited: coincidental, as judged, so the verdict stands.

## Lesson

A metric that looks good is the one to distrust first. Line overlap said 29/45; reading
the lines said 9/45. The measurement only became honest when every hit had to point at
the problem itself.
