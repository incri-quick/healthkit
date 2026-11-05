# Slice 024: quieter output, style folded, quoted type names as hints

Status: **approved** (2026-11-05, "proceed to phase 1"). Phase 1, item 2a (D-027).

## Why

Every source said the real findings drown (`FEEDBACK.md` 2d, row 2): the school project
("249 of the first 370 were import order and unused imports"), QuickRPA ("about 1,900 of
2,207 pure style"), and a teammate (the import-order finding has no fix command; ruff is
not on PATH). The school project also had 17 false "undefined name" alarms on
SQLAlchemy's quoted type names.

## Measured first (2026-11-05, both baselines, read only)

| Rule | QuickRPA (2,748) | School project (370) |
|---|---|---|
| I001 import order | 978 (36%) | 135 (36%) |
| F401 unused import | 347 (13%) | 114 (31%) |
| BLE001 `except Exception` | 429 (16%) | 55 (15%) |
| RUF052 `_name` used | 242 (9%) | 0 |
| F821 undefined name | 1 | 17 |

- **I001 + F401 are half of QuickRPA's findings and two thirds of the school project's.**
  Both are fixed mechanically by `ruff check --fix`.
- BLE001 is a deliberate policy question per site, and RUF052 caught a real bug (the
  login fixture in `tests/test_review.py`): neither is cosmetic, so neither is folded.
- All 17 school F821 are names inside a quoted type: `Mapped["Student"]`,
  `Optional["Teacher"]`, `_: "User"`. ruff places the column on the name, inside the
  quotes (a scratch file: `"Student"` at column 9 = the `S`; `"list[Pupil]"` at the `P`);
  an unquoted undefined name is never inside a string token.

## Design

1. **Style findings folded** (ruff I001 and F401) in `scan`'s `text` and `markdown`
   output: one line instead of one per finding.
   **Changed while building:** first folded in `review` too. That broke 25 older tests,
   and they showed why: in `review` the style findings sit on your own few changed lines,
   where the line number is the point ("unused import on line 6"). The volume was
   measured in `scan` (both numbers above are whole-module scans). So `review` lists them
   in full and adds the same fix line (a teammate's request); only `scan` folds. 3 older
   scan tests now read the JSON output, where every finding is still listed, for the same
   facts (file, line, rule). The folded line:
   `style: 249 finding(s), import order (I001) 135, unused imports (F401) 114, in 41
   file(s). Fix: uvx ruff@0.17.2 check --isolated --fix --select I001,F401 <targets>`.
   - Targets: in `review`, the files with style findings; in `scan`, the folders scanned.
     More than 10 files: the command names the first 10 and says how many more.
   - They are still problems: the exit code does not change, and the summary count
     includes them. Only how they are shown changes.
   - `json` and `github` list every finding as before (machines; inline PR annotations).
2. **F821 on a name inside a quoted type** becomes `worth a look` (advisory), with the
   message `... (inside a quoted type: often a forward reference resolved at runtime)`.
   An unquoted undefined name stays a problem.
3. README: both, plainly.

## Out of scope (slice 025 and 026)

Naming what `allowed` and `baselined` hide; naming the project checks `scan` skips; the
five small QuickRPA bugs.

## Failure modes, each with a test

- a file with only style findings (one folded line, exit 1);
- style and real findings mixed (real ones in full, style folded);
- more than 10 files with style findings (command lists 10, says how many more);
- `json` keeps every style finding;
- F821 in `"X"`, `Optional["X"]`, `"list[X]"` (advisory); F821 unquoted (problem);
- an f-string or a docstring that mentions the name is not mistaken for a type;
- a file that does not tokenize (a syntax error): F821 stays a problem, no crash.

## Acceptance

Tests shown failing first; mutants; full suite; live runs on QuickRPA and the school
project (read only), showing the folded line and the F821 change; line count against the
2,500 budget (asks again, D-028); a fresh-agent check (L-026).
