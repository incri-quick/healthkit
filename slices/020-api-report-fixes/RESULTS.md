# Slice 020 results: name the stateful route, list shallow routes, keep reports out of git

## What changed

- **Stateful failures name their route.** The report's `Stateful tests` line is replaced
  by one finding per route that the event log names. If the log names none, the line
  stays, so a failure is never dropped. A route already named elsewhere is not listed
  twice.
- **Shallow routes are listed**, per user when there are several, the same way as refused
  ones. The summary counts distinct routes.
- **Every report folder gets a `.gitignore` containing `*`**, so git ignores it wherever
  it is.
- Internal: one pass over the event log now gives both the response statuses (slice 019)
  and the stateful failures (`read_events`, `failures`).

## Live check (the school project's slice 019 run, its own report folder, read only)

| User | before | after | refused | shallow |
|---|---|---|---|---|
| admin | 18 incl. `Stateful tests` | 18, `Stateful tests` became `GET /assignments/` | 3 | 4 |
| teacher | 10 incl. `Stateful tests` | 10, `Stateful tests` became `GET /assignments/` | 31 | 8 |

`GET /assignments/` is exactly the crash that project's AI found only by reading its
server log. The refused counts, 3 and 31, match what it reported by hand.

## Tests

`tests/test_api_report.py`, 3 tests, all failing before the code:

- unit, on an event log in the measured format: the stateful route is named, a route
  already named is not doubled;
- unit: with no event log the `Stateful tests` line stays;
- on the test API, with the report folder inside a git repo: the shallow route is listed
  by name, and `git status` is clean after the run.

Changed: one slice 016 test asserted `/items/{item_id}` appeared nowhere in the output.
It now appears, correctly, in the shallow list, so the test asserts that no *finding*
names that route.

## Mutants: 5 of 5 killed

Stateful line kept · stateful line dropped even with no route named · duplicates kept ·
no `.gitignore` · shallow not listed.

Two conditions are kept on purpose although no test can catch their removal (they make no
difference today):

- the "stateful phase only" filter: other phases' failures are already in the report;
- the "failed check only" filter: a passing check carries no failure info.

## Full suite

196 passed (9 min), with `HEALTHKIT_OPENGREP` set.
