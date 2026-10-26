# Slice 002 results

## What exists

`healthkit review --base <ref>`: ruff (D-013 gate rules) on the Python files changed
since `<ref>`, findings kept only on changed lines, one finding format, exit
0 pass / 1 findings / 2 could not check.

| File | Lines | Role |
|---|---:|---|
| `src/healthkit/findings.py` | 22 | `Finding`, `ToolError` |
| `src/healthkit/gitdiff.py` | 71 | repo root, base check, changed lines from `git diff -U0` |
| `src/healthkit/tools/ruff.py` | 57 | ruff adapter, batched, explicit rule list |
| `src/healthkit/cli.py` | 57 | `review` command |
| `tests/` | 256 | 13 tests, throwaway git repos, fixtures from QuickRPA incidents |

## Evidence

- Tests written first and shown failing (import errors), then 13/13 green.
- **Mutation check:** two deliberately broken diff parsers (report every line;
  drop the deletion-only guard). The second survived at first: no fixture had a file
  changed only by deletion. Fixture added; both mutants now fail.
- Strict ruff (`ALL` minus `D`, `COM812`, `CPY001`) and the formatter: clean.
- **healthkit on its own changes:** 9 files, 0 findings, exit 0.
- **QuickRPA backend, read-only** (`git status` clean after):
  - base `HEAD~1` (1 commit): 2 files, 0 findings, exit 0, ~1 s.
  - base `220f7b3` (113 commits, Oct 6–26): 215 files, **73 findings**, exit 1, ~1 s.
    52 `I001`, 10 `PLC2701`, 9 `BLE001`, 3 `N806`, 1 `F401`.

## Bugs found while building (both caught by tests from reality)

1. **Paths with spaces were silently skipped.** git ends such paths with a TAB on
   the `+++` line; the parser kept it, so `bot.py\t` did not end in `.py`. The unit
   fixture had been typed by hand without the TAB, so it passed while the real-git
   test failed. Fixture replaced with real git output; parser fixed.
2. **Duplicate findings.** ruff 0.17.2 emits `PLC2701` once per name in a
   multi-name private import (QuickRPA commons/tests/test_permission_utilisation.py:479).
   Findings are now a set.

## Independent verification

A fresh agent tried to break the CLI with throwaway repos. It found one real gap:
**a changed `.pyi` type stub was skipped** ("nothing to review", exit 0), because the
CLI kept only `.py`. Reproduced as a failing test, fixed (`.py` and `.pyi`), 14/14 green.
(Its report said the spec listed `.pyi`; it did not: the idea came from its brief.)

It reported only the failure, not its other attempts, so three risky cases were
re-run by hand, all correct: a syntax error in a changed file (`[ruff syntax]`, exit
1), a non-ASCII file name (`café.py`, finding on the right line), and running from a
subfolder (same result).

**Known issue (cosmetic):** on this Windows console, `café.py` prints as `caf�.py`.
Matching is correct; console output encoding is not. For the reporting slice.

## Seen in the real run, for later slices (not fixed here)

- **Migrations:** `N806` on `Override = apps.get_model(...)` is the Django convention
  in generated migration files: false alarm. Exclude migrations by default.
- **Tests importing private helpers** (`PLC2701` in test files): a policy question
  for the project pack, not a defect.
- **Scripts under `docs/`** are reviewed too (`docs/dbmodelling-step1-checks.py`).
- Real ones worth passing on: an unused import in organization/api/organization.py:30,
  private helpers imported across apps (studio_robot/api/robots.py:1510,
  studio_workflow/api/workflow.py:2496), and bare `except Exception` blocks without a
  written reason (e.g. users/models.py:269).

## Budget

Over the old rule: 208 source + 269 tests against about 300. Raised with the owner;
accepted, and the rule changed to count source only (D-016).

## Lesson

A tracer bullet finds its bugs at the joins. Both bugs sat between layers (git's
output format → the parser; ruff's output → the finding list), not inside one.
