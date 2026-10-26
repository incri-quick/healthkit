# Slice 002: review tracer bullet

Status: **approved** (2026-10-26), including Python >=3.10, uv + pyproject (hatchling), pytest, strict ruff

## Goal

The thinnest end-to-end version of the gate:

    healthkit review --base <ref>

runs ruff (the curated gate rules from D-013) on the Python files changed between
`<ref>` and `HEAD`, keeps only findings on **lines the branch changed**, prints them
in one finding format, and exits 1 if any remain, 0 if none.

## Out of scope (later slices)

Baseline/ratchet, Opengrep and import-linter adapters, config files, report
formats (Conventional Comments, SARIF), `--fix`, whole-repo tools, replay harness.

## Design

- Package `healthkit` (src layout), Python standard library only at runtime.
- `Finding`: tool, rule, path, line, message. One format for every tool from now on.
- Changed lines: `git diff --unified=0 --no-color <merge-base>...HEAD`, parsed for
  added/changed line numbers per file. Committed changes only (it is a pre-push gate).
- ruff runs through `uvx ruff@0.17.2` with an explicit `--select` (no reliance on
  ruff's changing defaults; see L-002), `--output-format json`, on changed files only.
- Subprocess calls take argument lists, never `shell=True`. Nothing is written to the
  target repo.

## Failure modes (each gets a test)

1. Not inside a git repo → clear error, exit 2.
2. `--base` ref does not exist → clear error, exit 2.
3. No changed Python files → "nothing to review", exit 0.
4. ruff / uvx not available, or ruff exits with an error → report it, exit 2. Never
   "0 findings" for a run that did not happen (L-004).
5. ruff output is not valid JSON → report it, exit 2.
6. Paths with spaces ("Bot Starter Kit"), Windows backslashes, CRLF files.
7. Renamed, deleted and binary files in the diff.
8. A file with a byte-order mark.
9. A finding on an unchanged line of a changed file → not reported.

## Tests from real cases

Fixture code comes from QuickRPA incidents, not invented examples:
- `_password = require_text(...)` then used (RUF052, fixed in `ca5c64e`): added by
  the branch → reported.
- The same file already containing an old violation on an untouched line → not
  reported.
- `api_settings` used but never imported (F821, the dead login code removed in
  `198494c`) → reported when the branch adds it.

Tests build throwaway git repos in a temp folder. Written first, shown failing.

## Acceptance

- All tests green; a deliberately broken diff parser makes them fail.
- Run on the QuickRPA backend with a real base: output and exit code pasted.
- healthkit run on its own repo: clean.
- Diff under ~300 lines including tests.

## Needs approval (dependencies; CLAUDE.md "stop and ask")

- **Python ≥ 3.10** for users; developed on 3.12.
- **Packaging: `uv` + `pyproject.toml`** (hatchling build backend).
- **Tests: pytest** (dev dependency only).
- **ruff for healthkit's own code**, strict from the first commit.

## Lesson this slice teaches

A tracer bullet: build the thinnest path through every layer first, then widen it.
Problems show up at the joins (git → files → tool → findings), not inside the layers.
