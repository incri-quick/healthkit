# Slice 027: project rules skip tests and keep their severity; callables passed along

Status: **approved** (2026-11-05, "proceed"). Phase 1, item 3, part 2 (D-027): the last
slice of phase 1.

## Why (`FEEDBACK.md` 2c-2 and 1, QuickRPA)

1. "Project rules scan test files ... so I had to repeat `paths: exclude` in all 8 rules.
   Rules should inherit the exclude, with tests excluded by default." 23 false hits before
   that.
2. "`severity` in a rule file is silently ignored. It should either be honoured or
   rejected with a warning."
3. "A BOM in a rule file breaks parsing; PowerShell adds one by default."
4. "`option-never-passed` said 5 options of `execute_node()` are 'always None/False'.
   Production calls it as `asyncio.to_thread(execute_node, …, execution_id=…,
   meta_out=…)` and passes every option."

## Measured first (Opengrep 1.32.0, healthkit 8cd14be, 2026-11-05)

- **Tests:** QuickRPA's 8 project rules each repeat
  `paths: exclude: ["tests", "test_*.py", "tests.py", "tests_*.py"]`. A scratch project
  rule matched both `a.py` and `tests/test_a.py`. healthkit's own Django, copies and
  options checks already skip test files (`config.TEST_FILE`); project rules do not.
  `exclude` in `config.toml` does apply to every tool (findings are filtered by it): what
  was missing is the test-file default.
- **Severity:** Opengrep reports each result's severity (`extra.severity`: ERROR, WARNING,
  INFO). healthkit drops it: every result is a problem. **Two of healthkit's own built-in
  rules are marked WARNING** (`raw-json-body`, `cache-read-modify-write`) yet block today,
  so honouring severity everywhere would quietly weaken them. Project rules only.
- **BOM: not reproduced.** A rule file with a BOM, with a BOM plus a comment first line
  and CRLF line endings: Opengrep and `healthkit scan` both read it and report the match.
  No fix without a failing case: asked of the QuickRPA session, noted in `FEEDBACK.md`.
- **Callables:** `options` counts direct calls only, and its file pre-filter looks for
  `name(`: a file that passes `execute_node` to `asyncio.to_thread` without calling it
  directly is never even read.

## Design

1. **Project rules skip test files** (the same `config.TEST_FILE` test as the built-in
   checks). A rule meant for tests says so: `metadata: {healthkit-tests: true}`.
   healthkit's own rules are unchanged.
2. **Project rules keep their severity:** ERROR is a problem; WARNING and INFO are "worth
   a look" (advisory: shown, never failing the run, D-023). healthkit's own rules keep
   today's behaviour; they are told apart by their ids (each built-in rule file is named
   after its rule id).
3. **A function passed along as a value** (an argument to any call, positional or
   keyword: `to_thread`, `partial`, `submit`, `sync_to_async`, a callback) makes its calls
   unknowable: `option-never-passed` stays silent for it, as it already does for calls
   with `*args` / `**kwargs`. The file pre-filter looks for the name, not `name(`.
4. README: the test-file default and the opt-in, severity, callables.

## Failure modes, each with a test

- a project rule matching in `tests/test_a.py` and `a.py`: only `a.py`;
- the same rule with `metadata: {healthkit-tests: true}`: both;
- a project rule with `severity: WARNING`: "worth a look", exit 0; with ERROR: a problem;
- healthkit's own WARNING rules (`raw-json-body`) still block;
- `asyncio.to_thread(execute_node, …)` in a file with no direct call: no
  `option-never-passed` for `execute_node`;
- a function passed as a keyword value (`callback=handler`): silent too;
- a function only ever called directly, missing an option: still reported (unchanged).

## Acceptance

Tests failing first; mutants; full suite; live on a QuickRPA clone: its rules with the 8
`paths: exclude` blocks removed give the same findings, and `execute_node`'s 5 false
options are gone; line count (budget asked again); a fresh-agent check, its cases re-run
by hand where it pastes no output.
