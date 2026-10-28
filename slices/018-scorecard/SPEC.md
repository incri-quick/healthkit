# Slice 018: the module scorecard

Status: **approved** (2026-10-28)

## Measured first

pyscn 1.33.0 on QuickRPA's app code: 3 seconds, nothing written into the project
(`--json --output -`), overall health 85 (B). Run per module, its grade hides what matters:
`studio_workflow` (44,716 lines, 42 too-complex functions, one at complexity 68) scores
87 B, the same as `analytics` (2,618 lines); the "worst" is `core` (74 C, 173 lines, nothing
risky). Its raw numbers are the useful part.

## Design

`healthkit scorecard [folders] [--format text|json|markdown]`: one row of facts per module
(the first folder of each Python file's path), no invented grade:

files, lines, too-complex functions (pyscn's high-risk count), the most complex function
(name and complexity), healthkit's problems and hints (the same tools as `scan`, baselined
ones included: debt is part of health).

- Sorted so the modules that need attention come first: too-complex functions, then
  problems, then size.
- One line for pyscn's overall score, to follow the trend.
- One pyscn run for the folders plus one scan: seconds. Test files and excluded paths are
  left out of both. It never runs project commands.
- Exit 0 with a scorecard, 2 when a tool could not run (never a partial card shown as whole).

## Tests

A made-up project with two modules (one with a too-complex function and a problem): rows,
order and numbers; JSON and Markdown; test files left out; pyscn missing is exit 2. Mutants.
