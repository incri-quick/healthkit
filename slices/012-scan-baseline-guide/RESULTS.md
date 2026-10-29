# Slice 012 results: scan a folder, a baseline, and a usage guide

## What exists

- `healthkit scan <folder> ...`: every line of the Python files in the folders, same
  tools as `review` (ruff, Opengrep, import-linter, Django pack, copies). Never runs the
  project's `[[check]]` commands, and says so. `# noqa` hits are counted ("suppressed: N").
- `healthkit baseline <folder> ...`: writes `.healthkit/baseline.json`. Findings are
  remembered by tool, rule, file and line text (indentation set aside), with counts, so
  moved or re-indented code still matches and a second copy is new. Other folders' entries
  are kept. Nothing is written when a tool could not run.
- `scan` and `review` hide baselined findings ("baselined: N"); `scan` also counts "fixed
  since the baseline: N". `review` cannot (it sees changed lines only).
- README rewritten as the usage guide: install, commands, what results and exit codes
  mean, the `.healthkit/` folder, the miss log, and instructions for an AI assistant.

## Live run: QuickRPA `users/` (throwaway clone, team config)

```
healthkit scan: 92 finding(s) in 102 file(s) | ran: ruff, opengrep, import-linter, django, copies | project checks are not run by scan | worth a look: 2 | suppressed: 3
exit=1   (6 seconds)
```

| Rule | Count |
|---|---|
| ruff I001 (import order) | 36 |
| ruff F401 (unused import) | 19 |
| ruff BLE001 (catch-all `except`) | 18 |
| ruff PLC2701 (private import) | 8 |
| ruff N806, RUF052, F811 | 5, 3, 2 |
| opengrep raw-json-body | 1 (`users/api/users.py:572`, still there) |
| django soft-delete-read (advisory) | 1 |
| copies copy-same-name (advisory) | 1 (`_user_to_dict`) |

Every 5th finding plus each rare one, read by hand (22): all 22 claims are true;
**19 worth a change**, 3 debatable (two catch-alls that may be deliberate, the advisory
robot count). 55 of the 92 are import tidy-ups that `ruff --fix` does on its own.

Then:

```
healthkit: baseline written: 94 finding(s) in 102 file(s)
healthkit scan: no known problems in 102 file(s) | ... | suppressed: 3 | baselined: 94
```

## The guide, followed from scratch

A new empty project, healthkit run through `uvx --from <repo>` (the same install as
`uv tool install`, without changing the machine): `--help`, `scan` (1 finding, exit 1),
`baseline`, `scan` again (baselined: 1, exit 0), and `review` on a branch that adds a
second unused import (only the new one shown, exit 1). Each step did what the guide says.

## Found while building

- A test's premise was wrong: trailing spaces added to "change" a line created a real new
  finding (ruff I001), and the baseline rightly did not hide it. The realistic "changed but
  the same" case is re-indentation; the test now uses that, and a second test pins that a
  line which now says something else is shown.

## Verification

- Tests first: 14 failing before any code, then 16 green (two added on the way).
- Mutants **13 of 13** caught (run against `tests/test_scan.py`).
- Full suite **147 passed** (4 min 5 s); lint clean.
- Source: about 170 lines (`baseline.py` 85, `cli.py` +83 −7); the guide does not count.
