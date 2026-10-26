# Decisions

Append-only. To change a decision, add a new entry that supersedes it.
Status: **decided**, **open**, or **superseded by D-xxx**.

---

## D-001 The problem — decided (2026-10-26)

Code drifts away from the agreed standard, and nothing checks the parts of the
standard that need understanding. Three levels:

1. **Form** (case, layout, imports): already solved by ruff. Adopt, do not build.
2. **Meaning** (names that tell the truth, `get_` has no side effects, booleans
   read as questions, no flag arguments): unsolved. healthkit's first target.
3. **Team conventions** (use the shared function, follow the house pattern, no
   copies of a rule): unsolved and project-specific. Where the costly bugs were.

Evidence: QuickRPA backend, 2026-10. 260 of 533 commits since Aug 1 were fixes;
the same rule lived in several copies (3 sign-ins, 4 sign-outs, 2 change-password
routes, 7+ JSON readers); a cross-tenant leak recurred within a week.
Research: 77% of review findings are evolvability issues (Mäntylä & Lassenius 2009).

## D-002 Separate project — decided (2026-10-26)

Own repo, own versions, installed as a tool. QuickRPA is the first user, not its
home: a project keeps its own rules in a `.healthkit/` folder.

## D-003 AI is not in the gate — decided (2026-10-26)

The pass/fail gate is deterministic (rules and tools only). AI review is advisory
and never blocks. Later loop: AI finds a recurring problem → it is written as a
rule → the rule enforces it.

## D-004 Boundary — decided (2026-10-26)

Python + git + web backends, Django first. The core knows no language. An API pack
(OpenAPI-based) works for any backend language. TypeScript pack later.

## D-005 Architecture — decided (2026-10-26)

Core + packs: language / framework / project / API. Tools are called through small
adapters with pinned versions, never forked or vendored. Every tool's output is
converted to one finding format. One tool per job. Missing tools are skipped with a
notice. Packs switch on automatically by detection.

Core responsibilities: diff filter, finding format, baseline/ratchet, gate,
report (Conventional Comments with incident IDs), module scorecard, replay test.

## D-006 Tool inclusion rule — decided (2026-10-26)

A tool joins only if it: has machine-readable output, runs as one command with no
server, does not overlap a tool already included, and catches real findings in the
replay test.

Shortlist, pending the M1 trial: ruff, Opengrep, import-linter, pyscn,
Skylos or vulture, diff-cover, Schemathesis, gitleaks, pip-audit, deptry,
django-zeal, django-migration-linter.

Dropped: reviewdog, diff-quality, Semgrep baseline (the core does the diff
filter); wily (the scorecard keeps history); SonarQube, qlty, PR-Agent (servers or
overlap with the core).

## D-007 Gate behaviour — decided (2026-10-26)

Only lines the branch changed are judged. A baseline records existing problems so
only new ones fail. Existing problems are paid down module by module (ratchet).

## D-008 Success measure — decided (2026-10-26)

Replay test: run healthkit on QuickRPA backend at `49d5dc8^` (the code before
Susheel's users/auth review) and count how many of his AA findings it reproduces.
Every new rule should raise that count. Estimate before measuring: ~27% of his
findings detected, ~4% auto-fixed.

## D-009 Why the working agreement exists — decided (2026-10-26)

Research on AI-written code names eight misses: unwritten rules, reuse,
unhappy paths, safe defaults, honest tests, self-assessment, comprehension,
destructive actions (GitClear 2026, CodeRabbit 2025, Veracode 2025, Sonar 2025,
METR 2025, Anthropic 2026, DORA 2025, Beck, Osmani, Willison, Torvalds).
CLAUDE.md maps one rule to each.

## D-010 First rule families — decided (2026-10-26)

1. Names that lie
2. Error-handling conventions (catalogue errors, no HTTP errors in services,
   bare `except` needs a reason, no `str(exc)` in responses)
3. Copies of shared logic
4. Project rules for QuickRPA (protected-field `save()`, raw `json.loads(request.body)`,
   `assert_perm` scope, soft-delete reads)
5. Changes that delete or skip tests

---

## D-011 Home and visibility — decided (2026-10-26), resolves O-1 in part

Repo: `github.com/incri-quick/healthkit`, **private** for now. It may go public once
it is generic and holds no client details. The name "healthkit" stays a working name.

## D-012 Co-owner and replay data — decided (2026-10-26), resolves O-2 and O-3

Susheel co-owns the toolkit and agreed (verbally) that his users/auth review notes
may be used as replay-test data.

## D-013 Tool set after the trial — decided (2026-10-26), supersedes the shortlist in D-006

Measured on QuickRPA backend (slice 001, `slices/001-tool-trial/RESULTS.md`).

- **Keep:** ruff 0.17.2 (curated rule set), Opengrep 1.32.0 (engine for our own rules
  only), import-linter 2.15, pyscn 1.33.0 (scorecard), Skylos 5.1.0 (`--no-grep-verify`).
- **Drop:** vulture (15% real), Opengrep community rules (25% real, Commons Clause
  licence, timeouts on the largest files).
- **Not yet trialled:** diff-cover, Schemathesis, gitleaks, pip-audit, deptry,
  django-zeal, django-migration-linter. Trial each when its milestone arrives.
- O-5 resolved: Opengrep has a native, signed Windows build.

## D-014 Two speeds: gate vs whole-repo — decided (2026-10-26)

- **Pre-push gate, every push, changed files only, seconds:** ruff, Opengrep (own
  rules), import-linter.
- **Whole-repo, nightly or on demand, minutes:** Skylos (dead code needs the whole
  repo to know nothing calls a symbol), pyscn (scorecard).

Why: dead-code analysis cannot be scoped to one module (anything called only from
other modules would look dead), and Skylos takes ~3 minutes on 134k lines.

## D-015 Near-copy detection is still unsolved — open (2026-10-26)

pyscn found only exact copies. The tenancy helper `_get_workspace_or_404` exists in
9 files in 3 versions; the 3 drifted ones were found by a same-name search across
modules, not by any trialled tool. Candidates: same-name functions across modules,
and project rules that require the shared function.

---

## Open

- **O-1 (rest) Final name; open source later or not.**
- **O-4 Where it runs while GitHub Actions is blocked.** Suggested: git pre-push hook
  plus a manual command.
- **O-5 Windows support of Opengrep.** Answered by slice 001 (the tool trial).

## Build plan (estimates, one person)

| Step | What | Time |
|---|---|---|
| M0 | Design doc + repo skeleton; settle O-1..O-5 | 1 day |
| M1 | Tool trial on QuickRPA backend: keep or drop each candidate | 1 day |
| M2 | Core: diff filter, finding format, baseline, gate, report, replay harness | 3–4 days |
| M3 | Python pack: ruff + Opengrep adapters, names-that-lie and error-handling rules | 3–4 days |
| M4 | Django pack + QuickRPA project pack | 3 days |
| M5 | First replay score; first live run on Susheel's next module | 1 day |
| M6 | API pack: Schemathesis "never a 500" sweep | 2 days |
| M7 | Module scorecard (pyscn + coverage per app) | 2 days |
