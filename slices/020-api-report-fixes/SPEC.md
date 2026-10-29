# Slice 020: name the stateful route, list shallow routes, keep reports out of git

Status: **approved** (2026-10-29: "sure proceed" on the next steps after the school
project's second review, 68/100)

## Why (the school project's slice 019 run)

1. `Stateful tests: Server error` names no route. That one line hid `GET /assignments/`,
   a crash found nowhere else; the other project's AI found it only by reading the
   server log.
2. `shallow (no valid sample data): 8` does not say which 8 routes.
3. `--report-dir healthkit-api-report` inside the repo left 38 MB that is not git-ignored.
   One `git add .` would commit it (my own instructions had put it there).

## Measured first (that run's own report folder, read only)

- The JSON report's failure lists `"Stateful tests"` as one of its operations.
- The event log (`schemathesis-events.ndjson`, slice 019) records every failed check of
  the stateful phase with `failure_info.failure` = `code` (ST101), `title` and
  `operation`, the route's real name (`GET /staff-attendance`). Templated paths keep their
  template (`GET /exams/{exam_id}/schedules`).
- In that run the stateful failures were `GET /assignments/` (new), and `/leaves/`,
  `/notices/`, `/people/parents`, `/staff-attendance` (already named elsewhere).
- `warnings.missing_test_data` lists the shallow routes by name, per run (admin 4,
  teacher 8).

## Design

1. A `Stateful tests` finding is replaced by one finding per route the event log names.
   If the event log names none, the `Stateful tests` line stays: a failure is never
   dropped.
2. Shallow routes are listed like refused ones: per user when there are several.
3. Every run writes a `.gitignore` containing `*` into its report folder, so git ignores
   the folder wherever it is (the same trick as `.pytest_cache`).

## Tests

- Unit, on an event log in the measured format: the stateful route is named, a route
  already named is not doubled, and with no event log the `Stateful tests` line stays.
- On the test API: the shallow route is listed by name.
- A report folder inside a git repo: `git status` shows nothing from it after a run.
- Mutants. Live: run the new reading over the school run's own event logs (read only).
