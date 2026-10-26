# Learnings

What went wrong, or what surprised us, and what changed because of it.
Newest first.

---

## L-001 An agent's "refuted" is not evidence (2026-10-26)

While reviewing Susheel's work, a background verifier agent marked a real bug
(a stale `save()` silently dropping an intended write) as REFUTED by misreading the
code it quoted. It had been asked to run a test and did not. A two-minute script on
a test database proved the bug in one run, and also showed one of our own claims
was too broad.

**Changed:** CLAUDE.md rule 6. Any claim, from any agent, counts only with output
that was actually run.
