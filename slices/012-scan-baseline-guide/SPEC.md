# Slice 012: scan a folder, a baseline, and a usage guide

Status: **approved** (2026-10-28), including decisions 1-3

## Why

Today healthkit only checks the lines a branch changed. A person (or an AI assistant)
cannot point it at one module and ask "what is wrong here?". And once it can, old problems
will flood every report. This slice makes healthkit usable on its own, in any project.

## What it adds

### 1. `healthkit scan <folder> [<folder> ...]`

Checks **every line** of the Python files in the folders, with the same tools as `review`:
ruff, Opengrep, import-linter, the Django pack, the copies check.

- Findings print the same way as in `review`; advisory ones as `worth a look:`.
- Exit codes: 0 nothing found, 1 findings, 2 could not check.
- Excluded paths and `[[allow]]` entries are respected.
- A `# noqa` that hides a finding is counted in the summary ("suppressed: N"), not hidden.
- **It never runs the project's `[[check]]` commands.** `review` runs them from the base
  branch so a branch cannot run a new command; `scan` has no base, so it does not run
  them at all. The summary says so.

### 2. A baseline: `healthkit baseline [<folder> ...]`

Writes `.healthkit/baseline.json`: today's findings, so they stop showing up. After that,
`scan` and `review` show only **new** findings, plus a count: "baselined: N".

- A finding is remembered by **tool, rule, file and the text of its line**, not the line
  number, so it stays matched when code above it moves.
- If the same line text appears twice and only one was in the baseline, the second is new.
- A finding that is gone counts as "fixed since the baseline: N", so progress is visible.
- The baseline lives in `.healthkit/`, so changing it needs a person's approval in
  `review` (as every `.healthkit/` change already does, D-018).

### 3. A usage guide (README)

The README still says "no code yet". It becomes the guide:

- what healthkit is, and what it can never judge (logic, security, design: D-017)
- install, and each command (`review`, `scan`, `baseline`, `api`, `routes`)
- what the exit codes and "worth a look" mean
- the project's `.healthkit/` folder: settings, allow entries, own rules, own checks
- **instructions for an AI assistant**: how to run it, how to read results, what not to do
  (never edit `.healthkit/` to make a finding go away)
- **a miss log**: when a human or AI review finds something healthkit missed, one line in
  `.healthkit/misses.md` (date, file, what was missed, kind). Misses decide what to build next.

## Things that could go wrong (each gets a test)

1. `scan` on a folder that does not exist → exit 2, never "nothing found".
2. `scan` on a folder with no Python files → says "0 Python files", exit 0.
3. A baseline file that is broken → exit 2, never "all baselined".
4. Code moves down 10 lines → its baselined finding still matches.
5. A second copy of a baselined line → reported as new.
6. A fixed finding → counted as fixed, not silently forgotten.
7. `scan` never starts a `[[check]]` command.
8. A tool fails during `scan` → exit 2, the other tools' findings still shown.

## How we know it works

- Tests first, shown failing; mutants.
- **Live run:** `healthkit scan` on a real module (QuickRPA's `users/`, in the throwaway
  clone): every finding type counted, 20 read by hand, then `baseline`, then a rerun shows 0.
- The guide is checked by following it from scratch in an empty folder.
- Under ~300 lines of source; the guide does not count.

## Needs approval

1. `scan` uses the same tools as `review`, but **never runs project commands**.
2. The baseline matches by **line text**, not line numbers, and lives in `.healthkit/`.
3. The README becomes the guide, with an AI section and a miss log.
