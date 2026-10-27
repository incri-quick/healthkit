# Learnings

What went wrong, or what surprised us, and what changed because of it.
Newest first.

---

## L-019 A negative result needs the same checking as a positive one (2026-10-27)

Two runtime probes of `soft-delete-read` findings came back "not a bug": an archived robot
was not listed, and a deleted file was refused. Both were bad setups: the test user could
not see the probe's workspace, and the file owner had no Studio access. Set up correctly,
the archived robot was listed.

**Changed:** before a probe counts as a refutation, it must show it reached the code in
question (the right user, the right tenant, the right status code for the right reason).

## L-018 A second project finds what the first cannot (2026-10-27)

`soft-delete-read` was tuned on QuickRPA, where models live in `models.py`. On the
second project (mulearnbackend, models in `db/*.py`) it found no models at all: a silent
zero, not an error. Precision also fell from what the tuned sample suggested: 25% on the
first read, 41% on QuickRPA's held-out findings, 55% on the second project.

**Changed:** D-022 holds in practice: a rule is measured on data it was not tuned on and on
a second project before it is called generic, and "found nothing" on a new project is
checked by hand before it is believed.

## L-017 A sweep that writes data changes what the next sweep can find (2026-10-27)

The second QuickRPA API sweep, same tool and settings, reported 4 crashes instead of 6.
Neither bug was fixed: the first sweep had deactivated the user one crashing input hit
and cleared the pending MFA setup the other needed. Replayed by hand with the right
state, both still answered 500 (`IntegrityError`, `TypeError`).

**Changed:** fewer API findings never means "fixed" until each missing one is replayed;
any before/after comparison of API runs needs the same starting data (a database
snapshot restored before each run).

## L-016 Distrust the metric that looks good (2026-10-27)

The replay's first metric, "a finding on a line the fix changed", gave 29/45. Reading
the flagged lines showed most were coincidences: an unused import inside a behaviour
fix, findings inside whole routes the fix deleted. Judged by whether the rule points at
the problem itself: 9/45. Also found: the ruff gate rules were chosen (slice 001) partly
by checking which hit these same fixes, so the replay is not fully out-of-sample.

**Changed:** every automated score gets a by-hand read of its hits before it is quoted;
selection data and test data are kept apart, and the next module is the clean test.

## L-015 Verifiers drift to what is easy to confirm (2026-10-27)

Told which doors were already closed and asked to try new ones, the slice 005 verifier
re-tested the closed doors, numbered its attempts 7-12, and reported nothing for the
new ideas. The first new idea run by hand (`.gitattributes`) was a total bypass.

**Changed:** a verification brief names the cases that must be attempted; the report is
checked case by case against that list, and missing cases are run by hand before any
verdict is accepted. Adversarial checks of the gate itself stay with a human-run repro.

## L-014 A test can guard the wrong door (2026-10-27)

The test "project ruff excludes cannot hide a finding" passed with and without
`--isolated`: naming files explicitly already defeats `extend-exclude`. The mutant that
removed `--isolated` survived, and measuring showed the setting it really blocks is
`per-file-ignores`, which no test covered.

**Changed:** when a mutant survives, measure what the mutated line actually protects
before writing the missing test.

## L-013 Read a verifier's "PASS" lines for what they imply (2026-10-27)

The slice 004 verifier listed ".Healthkit capitalized → filesystem finds it
(case-insensitive)" as a PASS. Followed through, it meant the config loads from a folder
the approval check never looks at: an agent could allow everything with exit 0. The
bypass was real, and it sat inside a line marked as passing.

**Changed:** every verifier PASS is read as a claim about behaviour and asked "so what
can an attacker do with this?"; surprising passes get a hand-run repro.

## L-012 Mutants only mean something on green code (2026-10-27)

A new test was failing (a wrong line number) when the mutants ran, so every mutant
"failed a test" and looked caught. The result was worthless and was thrown away.

**Changed:** the mutant run starts with the full suite on the real code; red there
means stop, not continue.

## L-011 `Path.write_text` on Windows writes CRLF (2026-10-27)

A quick fix-up script rewrote three source files with `write_text`; Windows newline
translation turned them into CRLF files. Nothing broke visibly, but a multi-line
mutant pattern stopped matching. Same family as the BOM trap in QuickRPA memory.

**Changed:** scripts that edit repo files use `read_bytes`/`write_bytes` (as
`slices/mutate.py` does), and check line endings before commit.

## L-010 A verifier's "CONFIRMED" without output is an opinion (2026-10-26)

The slice 003 verifier reported CONFIRMED and "production-ready" with no command
output and three requested cases silently skipped. Running those three by hand took
minutes; all passed, but the report itself proved nothing.

**Changed:** a verification report without pasted output for each case is sent back
or re-done; "all handled correctly" is not a result.

## L-009 Check the run happened where you think (2026-10-26)

A command chained `clone && cd && export && run`. The clone failed (Windows path
length), so `cd` and `export` never happened and the run used the previous directory
and no Opengrep. Then the "Opengrep not found" message was wrongly blamed; it was right.

**Changed:** setup and run are separate steps; each run prints where it ran, and setup
is verified (files present, expected commit) before the run.

## L-008 Passing files explicitly can switch off the project's own settings (2026-10-26)

ruff ignores a project's `exclude` settings for files named on the command line unless
`--force-exclude` is given. healthkit passed files explicitly, so it overrode every
project's ruff excludes, and flagged its own rule fixtures.

**Changed:** each adapter states which of the target project's own settings it honours,
and a test covers it.

## L-007 A surviving mutant points at a missing test (2026-10-26)

Breaking the diff parser's deletion-only guard on purpose did not fail any test. The
fixtures had no file changed only by deletion. One line added to the fixture, and the
mutant was caught.

**Changed:** every slice breaks its core logic on purpose at least twice before
calling the tests good.

## L-006 A hand-typed fixture hid a real bug (2026-10-26)

The unit test for the diff parser used a diff typed by hand. Real git ends a path
containing a space with a TAB on the `+++` line; the typed fixture did not, so the
unit test passed while files in "Bot Starter Kit" were silently skipped. Only the
end-to-end test on a real git repo caught it.

**Changed:** fixtures for another tool's output are captured from that tool, never
typed from memory (rule 5 applies to formats, not only to incidents).

## L-005 A prediction is the "failing test" for a tool (2026-10-26)

You cannot write a failing unit test for someone else's tool, but you can write the
expected result down before the run. import-linter matched its prediction exactly;
vulture broke one (`TenantMiddleware`) and that miss explained its whole false-alarm
pattern.

**Changed:** every tool trial writes its prediction into RESULTS.md before the run.

## L-004 "0 findings" can mean "did not run" (2026-10-26)

Skylos reported 0 unused functions on a codebase with known dead code. The reason
was one line in `analysis_errors`: its verification step timed out and it withheld
everything. pyscn's "dead code: 0" meant something narrower than its name suggests
(unreachable lines only).

**Changed:** an adapter must surface a tool's own errors and skipped work next to
its findings; a clean result is only trusted when the run reports it checked.

## L-003 False alarms came from rule choice, not the tool (2026-10-26)

ruff's sample was 47% real, below our 50% bar. Every false alarm traced to which
rules were switched on (lazy imports are deliberate in Django) or where they ran
(tests, tooling scripts), never to ruff misreading code.

**Changed:** a tool's verdict is "keep with this rule set", never just "keep". The
rule set itself is a decision that needs evidence.

## L-002 Claude's knowledge of a tool's defaults was out of date (2026-10-26)

Claude stated ruff's defaults were only `E4/E7/E9/F`. The first run showed 407 rules
enabled with `--isolated`, and the changelog confirmed ruff 0.16 (July 2026) raised
the default set from 59 to 413.

**Changed:** never describe a tool's behaviour from memory in a decision; quote the
version and the output.

## L-001 An agent's "refuted" is not evidence (2026-10-26)

While reviewing Susheel's work, a background verifier agent marked a real bug
(a stale `save()` silently dropping an intended write) as REFUTED by misreading the
code it quoted. It had been asked to run a test and did not. A two-minute script on
a test database proved the bug in one run, and also showed one of our own claims
was too broad.

**Changed:** CLAUDE.md rule 6. Any claim, from any agent, counts only with output
that was actually run.
