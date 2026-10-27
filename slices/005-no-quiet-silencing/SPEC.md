# Slice 005: the gate cannot be quietly silenced

Status: **approved** (2026-10-27), including decisions 1-3

## Goal

D-018 says the code-writing agent must not be able to quietly change the referee. Slice
004 guards `.healthkit/`, but three other doors were shown open (slice 004 RESULTS,
throwaway repo, one commit, three real findings hidden, no approval flag):

| Door | Effect today |
|---|---|
| `extend-exclude` in `pyproject.toml` `[tool.ruff]` | file skipped by ruff (healthkit honours project ruff excludes since slice 003) |
| `# noqa` / `# noqa: F401` on the line | ruff finding hidden |
| `# nosemgrep` on the line | Opengrep finding hidden |

After this slice: the project's own tool settings cannot switch healthkit's checks off,
and any suppression on a **changed line** reaches a human (exit 3), never a pass.

## Out of scope

Behaviour pack, report formats, stale allow entries, suppressions on unchanged lines
(existing ones are left alone: they are not part of this branch's change).

## Design

1. **ruff ignores the project's ruff settings** (`--isolated`). healthkit already lists
   its rules explicitly (L-002); exclusions now come only from `.healthkit/config.toml`,
   which needs a human. Replaces slice 003's `--force-exclude`.
   - Tradeoff: ruff's import-order rule (`I001`) may sort first-party imports
     differently without the project's isort settings. Measured on QuickRPA (it has no
     ruff config, so no change expected) and reported.
2. **A suppression on a changed line needs a human.** ruff runs twice (normal, and with
   `--ignore-noqa`); a finding that appears only in the second run, on a changed line, is
   reported as `needs human approval: <path>:<line> suppresses ruff <rule>`. Uses ruff's
   own `noqa` rules (including file-level `# ruff: noqa`) instead of re-implementing them.
3. **Opengrep likewise**, with `--disable-nosem`. Before writing code, capture whether
   its JSON marks ignored results (one run) or needs a second run (L-006).
4. **Opengrep's ignore files** (`.semgrepignore` / `.opengrepignore`): measure whether
   they hide explicitly passed files. If they do, disable them for the gate.
5. Suppressions count as "needs human approval": exit 3 if nothing else is wrong; real
   findings still exit 1; "could not check" still exits 2.

## Failure modes (each gets a test)

1. `extend-exclude` in `pyproject.toml` no longer hides a finding.
2. `# noqa: F401` added on a changed line → flagged, exit 3.
3. Bare `# noqa` (no codes) → flagged.
4. File-level `# ruff: noqa` added → its findings on changed lines flagged.
5. `# nosemgrep` added on a changed line → flagged.
6. An old `# noqa` on an unchanged line → not flagged.
7. A changed line that keeps an existing `# noqa` → flagged (the line is part of the
   change; a person decides whether the reason still holds).
8. An ignore file listing a changed file → still checked (if decision 4 confirms the door).
9. Suppression + a real finding elsewhere → exit 1, the suppression still listed.

## Tests from real cases

- The three silencing commits from the slice 004 repro, as one fixture each.
- QuickRPA's real justified suppression, `# noqa: BLE001 - refusing is the control;
  spending is cleanup` (users/api/users.py, refresh route): when its line changes it is
  flagged for a human, not failed and not passed.

## Acceptance

- Tests first, shown failing; green; mutants on each door, caught on green code (L-012).
- healthkit on itself: no findings; its own `# noqa` comments are on unchanged lines.
- The slice 004 three-door repro, re-run: all three reach a human.
- QuickRPA throwaway clone, base `220f7b3`: output pasted; any change in `I001` counts
  from `--isolated` explained.
- Under ~300 lines of source (D-016).

## Needs approval

1. **The project's ruff settings stop affecting the gate** (`--isolated`), reversing
   slice 003's `--force-exclude`. Exclusions belong in `.healthkit/config.toml` only.
2. **Suppressions on changed lines → "needs human approval" (exit 3)**, not a finding
   (exit 1) and not a pass. Justified suppressions stay possible; they just need a person.
3. **Two runs of ruff (and possibly Opengrep)** per review, to use the tools' own
   suppression rules rather than parsing comments ourselves. ruff costs under a second;
   Opengrep's cost is measured first.

## Lesson this slice teaches

A referee is every setting that can change a verdict, not only the folder named after
it. Each door found gets a test that walks through it.
