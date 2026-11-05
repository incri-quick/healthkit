# Slice 027 results: project rules skip tests and keep their severity; callables

The last slice of phase 1 (D-027).

## What changed

- **Project rules skip test files** (the same test-file pattern as healthkit's own
  checks). A rule meant for tests opts in with `metadata: {healthkit-tests: true}`.
  healthkit's own rules are unchanged: they still check test files.
- **Project rules keep their severity:** `ERROR` is a problem; `WARNING` and `INFO` are
  "worth a look" (never failing the run). healthkit's own rules keep today's behaviour.
  Two of them are marked WARNING yet block, so honouring severity everywhere would have
  quietly weakened them. They are told apart by id: each built-in file is named after its
  rule.
- **A function handed over as a value is not "never passed":** an argument or keyword
  value in any call (`asyncio.to_thread(f, ...)`, `partial(f)`, `submit(f)`,
  `callback=f`) makes its calls unknowable, as `*args` already did. The file pre-filter
  now looks for the name, not `name(`: the `to_thread` file was never even read.
- **BOM: not fixed, not reproduced.** A BOM, and a BOM with a comment first line and CRLF,
  both work in Opengrep 1.32.0 and `healthkit scan`. Noted in `FEEDBACK.md`; needs the
  failing file.
- README: all three.

## Measured first

- QuickRPA's 8 project rules each repeat
  `paths: exclude: ["tests", "test_*.py", "tests.py", "tests_*.py"]`.
- Opengrep reports `extra.severity`; healthkit dropped it.
- healthkit's own rules: `raw-json-body` and `cache-read-modify-write` are WARNING and
  block.

## Live run: QuickRPA (a throwaway clone of `feat/hitl-robot-approvers`, baseline removed)

- **Rules:** `scan studio_robot studio_workflow` with the rules as written, then with
  **all 8 `paths: exclude` blocks deleted**: identical project-rule findings (7 and 7),
  none in a test file. QuickRPA can delete those blocks.
- **Callables:** to recreate the teammate's case, one test was added to the clone calling
  `execute_node(1, 2)` directly. The production call is
  `asyncio.to_thread(execute_node, ...)` in `execution_engine.py`.

  | healthkit | `option-never-passed` findings for `execute_node()` |
  |---|---|
  | `main` (before) | **7** ("parent_output", "input_params", "dispatch_seq", "encrypt_result_intent", "meta_out", ...) |
  | this slice | **0** |

  The teammate saw 5; the function has gained options since.
- The clone was removed.

## Tests

`tests/test_rules_and_options.py`, 10 tests. 4 failed before the code; the 4 that passed
are behaviour that must not change. Added after:
- 1 from a surviving mutant: healthkit's own rules still check test files;
- 1 from the fresh agent's finding: a project rule with a built-in id keeps its severity.

## A defect found by the fresh agent, fixed

healthkit's own rules were first told apart by id alone. **A project rule reusing a
built-in id (`raw-json-body`) was taken for healthkit's own**, so its `severity: WARNING`
was ignored and it failed the run. Listed here as "uncertain" before; the agent proved it
(its log: exit 1 where 0 was expected).

Fixed by where the rule comes from. Measured: Opengrep prefixes each rule id with its
folder's path, dot-separated:
- built-in: `C.Users.legio.Workspace.healthkit.src.healthkit.rules.raw-json-body`
- project: `healthkit.rules.raw-json-body`

healthkit's own rules are now recognised by their folder's prefix (`BUILT_IN_PREFIX`). A
test (shown failing first) and three mutants guard it.

## Mutants: 13 of 13 killed

Tests not skipped · opt-in ignored · built-in rules skip tests too (survived first;
killed by the added test) · severity ignored · built-in WARNING turns into a hint · ERROR
turns into a hint · built-in told by id again · everything built-in · nothing built-in ·
callables not counted · keyword values not counted · pre-filter wants a call · every
function silenced.

## Full suite

271 passed (11 min), with `HEALTHKIT_OPENGREP` set, after the id fix.

## Checklist (L-026)

- **Line count:** 2,649 non-blank lines in `src/` (was 2,617; +32). Over the 2,500 budget
  (D-028); the 3,000 proposal is still unanswered (the owner said "commit and push" with the count shown), so it is asked again.
- **D-/L- entries:** none new.
- **Fresh-agent check:** done, and for the first time worth it.
  - Told to log every command with its output to a file the owner can read, it did
    (263 lines). It found the defect above; its log was read before it was believed.
  - Its other two claims (tests skipped for project rules; callables silent) were
    confirmed in the log.
  - It staged files in the healthkit repo (`git add`) despite being told to stay
    read-only: no commit, branch unchanged, nothing lost, but a rule broken.
  - Its log and work folder were removed afterwards.
  - The log-file instruction works and should stay.

## Uncertain

- A name passed as a value silences the check even when it is a different thing with the
  same name (a variable `handler` in another file). The error is in the quiet direction,
  on an advisory rule.
