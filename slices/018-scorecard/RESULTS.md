# Slice 018 results: the module scorecard

## What exists

`healthkit scorecard [folders] [--format text|json|markdown]` (`scorecard.py`,
`tools/pyscn.py`): one row of facts per module (the first folder of each path), the ones
needing attention first (too-complex functions, then problems, then size), and one trend
line with pyscn's overall score. No invented per-module grade. Test files and excluded
paths are left out. A tool that cannot run means no card (exit 2): a partial card would
look whole. README lists the command.

## Live: the whole QuickRPA clone (107 s, mostly the scan)

```
Module           Files  Lines  Too complex  Most complex                         Problems  Hints
studio_workflow  98     39239  42           validate_workflow_dag (68)           518       98
packages         251    54363  37           SanctionsScreenNode._run (31)        167       213
studio_robot     30     14322  16           run_robot_agent (61)                 218       34
commons          50     9507   9            render_value (19)                    60        42
studio_mcp       22     4951   4            apply_patch (56)                     33        19
...
users            35     5410   3            Command.handle (28)                  61        10
...
overall (pyscn): 86 (B)
```

`studio_workflow` and `studio_robot` are where the hard-to-change code is; `users` (the
module Susheel cleaned) has 3 too-complex functions. `packages` and `Bot Starter Kit` are
QuickRPA's by-design copies: they belong in its own `exclude`, not in healthkit.

## Found on the live run, fixed test-first

1. pyscn skips some folders (QuickRPA's `docs/`, `.claude/`) that healthkit checks, so
   rows showed 0 files beside real findings. Files and lines now come from healthkit's own
   list (non-blank lines).
2. pyscn reports each file's top-level code as a pseudo-function `<module>`; it was named
   the "most complex function" (`config`). Skipped now; a module with no function shows `-`.

## Verification

- Tests first (4 failing against a stub), then 7 green with the cases added for the
  ordering by need, suppressed findings, pyscn failing, another tool failing, and the two
  live-run fixes.
- Mutants **13 of 13** caught (against `tests/test_scorecard.py`).
- Full suite **186 passed**; lint clean. Source: `scorecard.py` + `tools/pyscn.py` 156 lines, `cli.py` +33.
