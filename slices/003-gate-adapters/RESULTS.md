# Slice 003 results

## What exists

`healthkit review` now runs all three pre-push gate tools (D-014): ruff, Opengrep
(built-in rules `exception-text-in-reply`, `raw-json-body`) and import-linter (contract
from `.healthkit/importlinter.ini`). The last line names the tools that ran and those
skipped. Source: 405 lines total, ~197 added (D-016).

## Real outputs captured before writing tests (L-006)

- **import-linter exits 1 both for a broken contract and for a config error**
  ("Could not find package..."). Only the text tells them apart. A guessed parser
  would have read a config error as "no broken links": a silent pass.
- import-linter wraps long lines to the terminal width, even inside `(l.32, \nl.963)`.
- Opengrep reports Windows paths with backslashes, prefixes rule ids with the rule
  file's path, and reports per-file errors (e.g. `Timeout`) inside its JSON with exit
  code 0.

Fixtures in `tests/fixtures/` are those real outputs.

## Evidence

- Tests written first, shown failing; 28/28 green (~60 s: real Opengrep and
  import-linter runs).
- **6 mutants, all caught** (`mutants.py`): Opengrep ignoring its errors list;
  Opengrep line off by one; import-linter not unwrapping; import-linter treating a
  config error as clean; import-linter ignoring package `__init__`; the CLI reporting a
  failed tool as a pass.
- Strict ruff and the formatter: clean.
- **QuickRPA, throwaway local clone** (dev `7fadfe3`, slice-001 contract in its
  `.healthkit/`; the backend repo itself untouched), base `220f7b3`:
  `74 finding(s) on changed lines in 215 file(s) | ran: ruff, opengrep, import-linter`,
  exit 1, ~8 s. The one Opengrep finding is `commons/payload.py:54`, the shared reader
  itself (allow-list needed, slice 004).
- **The quiet results checked, not assumed:** the known problems from slice 001
  (storage_buckets/services.py:164 and :288, reports/tasks.py:315,
  studio_robot/watchdog.py:410, run_readiness.py:159, workflow.py:4027) are all on lines
  **unchanged** in the range, so not reporting them is correct. payload.py:54 is on a
  changed line and was reported.

## Independent verification

A fresh agent reported CONFIRMED and "production-ready", but gave **no command
output** and skipped three of the cases it was asked to try. Those three were then run
by hand (throwaway repo, output kept in this session):

- **Three broken contracts at once**, names containing a colon and brackets, one of
  type `forbidden` (different output shape): each finding labelled with the right
  contract id. ✓
- **Importer in a namespace package** (`reports/` without `__init__.py`): mapped to
  `reports/run.py:2`. ✓
- **A changed file with a syntax error:** ruff reports `[ruff syntax]`; Opengrep lists
  the file under `paths.scanned` (no `skipped`), and its error-tolerant parser still
  matched `raw-json-body` on a line *after* the syntax error. So exit 1, not 2, is the
  correct answer. ✓

## Bugs found while building

1. **Files passed to ruff explicitly bypassed the project's own ruff excludes.**
   Found when healthkit flagged its own rule fixtures although its pyproject excludes
   them. Fixed with `--force-exclude`; real-case test added.
2. **An OS error running Opengrep was always shown as "not found".** Now the message
   names the path and the actual error.

## Known gaps (for slice 004)

- **healthkit on its own repo: 6 findings**, all Opengrep matches on the `# ruleid:`
  lines of the built-in rule fixtures, which exist to match. Needs healthkit-level
  exclusions. Acceptance item "clean on its own repo" is **not met** for this reason.
- `raw-json-body` flags the project's shared reader (`commons/payload.py`): needs an
  allow-list.
- Default exclusions (migrations) and a Django pack for `raw-json-body`.
- Tests take ~60 s because every end-to-end test runs the real tools.

## My mistakes in this slice

- A command chained the clone, `cd` and `export` with `&&`. The clone failed on
  Windows path length, so the run happened in the real backend (read-only; confirmed
  untouched) without Opengrep configured.
- I then blamed the adapter's "not found" message. A direct run showed Opengrep works;
  the message had been correct: the `export` never ran.

## Lesson

An adapter's real job is honesty about what did not run. The two most dangerous
behaviours found here (exit 1 meaning two different things; errors hidden in exit-0
JSON) would both have produced a pass that checked nothing.
