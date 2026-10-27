# Slice 005 results

## What exists

The project's own tool settings and inline comments can no longer quietly switch the
gate off (D-018):

- **ruff runs `--isolated`**: the project's ruff settings are ignored. Exclusions come
  only from `.healthkit/config.toml`, which needs a human. Replaces slice 003's
  `--force-exclude`.
- **A suppression on a changed line needs a human** (exit 3), shown as
  `needs human approval: <path>:<line> suppresses <tool> <rule>`. ruff runs twice
  (honouring `# noqa`, and with `--ignore-noqa`); Opengrep runs once with
  `--disable-nosem` and reads `is_ignored`. The tools' own suppression rules decide.
- Suppressions on unchanged lines are left alone.

Source: 588 lines total, ~21 net added (D-016).

## Measured before coding (L-006)

| Question | Answer |
|---|---|
| Does `--isolated` stop pyproject from hiding a file? | yes |
| Does `--ignore-noqa` reveal `# noqa: X`, bare `# noqa`, file-level `# ruff: noqa`? | yes, all three |
| Does Opengrep mark `# nosemgrep` results? | yes: `--disable-nosem` returns them with `is_ignored: true`, so one run is enough |
| Can `.semgrepignore` / `.opengrepignore` hide an explicitly passed file? | **no**: suspected fourth door does not exist; test keeps it shut |
| Which project ruff settings actually hide a finding for explicit files? | **only `per-file-ignores`**; `ignore` is overridden by `--select`, `extend-exclude` by naming files |

## Evidence

- Tests first; 8 new suppression tests + 2 project-settings tests; one slice 003 test
  **reversed by decision 1** (project ruff excludes no longer honoured). 67/67 green.
- **6 mutants, all caught on green code.** The first round: the `--isolated` mutant
  **survived**, because the exclude test could not tell `--isolated` from "files named
  explicitly". Measuring showed `per-file-ignores` is the setting `--isolated` actually
  blocks; a test for it now kills the mutant.
- Strict ruff and formatter: clean.
- **The slice 004 attack, re-run with a fourth door added** (one commit): `extend-exclude`
  and `per-file-ignores` findings are now reported (a.py:2, p.py:2); `# noqa` and
  `# nosemgrep` reach a human (b.py:2, c.py:4). Exit 1.
- **QuickRPA throwaway clone**, base `220f7b3`: finding counts identical to slice 004
  (52 I001, 9 BLE001, 8 PLC2701, 1 N806, 1 F401; QuickRPA has no ruff config, so
  `--isolated` changes nothing, as predicted). **3 suppressions on changed lines**, all
  `# noqa: BLE001` with written reasons (commons/lockout.py:293, users/api/users.py:288,
  :554): exactly the case for a person to confirm. ~11 s (8 s before; second ruff run).
- **healthkit on itself:** no findings; exit 3 for its own config change (`slices/**`
  now excluded in `.healthkit/config.toml`, since pyproject no longer reaches the gate).

## Independent verification

The fresh agent reported CONFIRMED after "12 attempts", but showed only attempts 7-12,
and those re-tested the doors it had been told were already closed. None of the new
ideas it was given came back with output (L-010, third time). The three most dangerous
were run by hand:

- **`.gitattributes` with `*.py binary` or `*.py -diff`: a total bypass (fixed).** git
  showed no changed lines, so the gate said "nothing to review", exit 0. Same for a
  textconv driver. Fixed with `git diff --text --no-textconv`; three tests; two mutants;
  the manual attack re-run: F401 reported, exit 1.
- **ruff range comments** (`# ruff: disable[F401]` ... `enable`): already caught by
  `--ignore-noqa` (needs human approval).
- **Real code placed under `migrations/`: hidden by the default exclusion**, exit 0
  ("excluded: 1 file(s)" is shown). QuickRPA itself has one such module today:
  `users/migrations/_inert_permissions.py` (99 lines, real code, imported by tests).
  Proposed: narrow the default to Django-named files `**/migrations/[0-9][0-9][0-9][0-9]_*.py`
  (all 205 of QuickRPA's generated migrations match). Changes slice 004 decision 3:
  **awaiting the owner**.

Then, owner-approved (D-019): the default exclusion narrowed to Django-named migration
files. QuickRPA clone re-run, base `220f7b3`: 0 generated migration files reviewed;
`users/migrations/_inert_permissions.py` (changed in the range) now reviewed, 2 findings;
excluded 8 → 7 files, reviewed 207 → 208.

Final: 76/76 green; 10 mutants caught on green code.

## My mistakes in this slice

- The `logger` fixture: my edited copy of the real code called an undefined `log`; the
  gate correctly reported it. Fixture made faithful to the real module.
- I believed the exclude test covered `--isolated`; a surviving mutant showed it did not.

## Known gaps

- Suppressions in tools added later (and import-linter's `ignore_imports`, which lives in
  `.healthkit/` and is already flagged) need the same treatment when those tools arrive.
- A suppression for a rule **outside** the gate rule set is not seen (nothing to reveal).

## Lesson

A referee is every setting that can change a verdict. The door that mattered most
(`per-file-ignores`) was not one of the three found by hand; a surviving mutant pointed at it.
