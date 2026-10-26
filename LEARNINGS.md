# Learnings

What went wrong, or what surprised us, and what changed because of it.
Newest first.

---

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
