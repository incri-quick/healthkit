# Slice 001: tool trial

Status: **approved** (2026-10-26)

## Goal

Decide keep or drop for each candidate tool, using measurements on a real codebase
(QuickRPA backend). Produces a decision, not code.

## Candidates

ruff, Opengrep, import-linter, pyscn, Skylos, vulture.

## Out of scope

Adapters, rules, and any configuration beyond defaults plus one obvious setting per tool.

## Method (per tool)

1. Install on Windows; fall back to WSL or Docker if needed (answers O-5).
2. Run on the backend at `dev` and at `49d5dc8^` (before the users/auth review).
3. Record: install problems, run time, output format (JSON/SARIF), finding count.
4. Hand-check a sample of 20 findings: real or false alarm.
5. Check against known findings: does it flag anything matching the AA findings
   (copies, layering, dead code, raw JSON reads, imports)?

## Failure modes to watch

- Will not install on Windows
- Crashes on the 15 files that start with a byte-order mark
- Breaks on the folder with spaces in its name ("Bot Starter Kit")
- Floods thousands of findings
- Needs Django set up to run

## Keep a tool only if all hold

- Runs (natively or via WSL/Docker)
- Machine-readable output
- Finishes in under 5 minutes on the backend
- At least 50% of sampled findings are real
- Adds something no other kept tool covers

## Done when

`RESULTS.md` in this folder holds the table and raw-output pointers, and
`DECISIONS.md` gets D-013 with the keep/drop list.

## Lesson this slice teaches

Judge a tool by its false alarms, not its feature list.
