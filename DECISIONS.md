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
   *(Priority superseded by D-021: meaning moves to the advisory AI layer.)*
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

**Answered by slice 011 (2026-10-28):** measured four matchers on the real cases; only the
same-name search finds drifted copies, so it ships (`copy-same-name`, advisory). Shape
similarity (outside tools and healthkit's own) sees exact copies only and was dropped.

## D-016 Slice budget counts source, not tests — decided (2026-10-26)

A slice stays under about 300 lines of **source**. Tests do not count against it:
more tests are wanted, and the formatter spreads test fixtures over many lines.
Slice 002 (208 source, 269 tests) is accepted under this rule.

## D-017 What healthkit can and cannot catch — decided (2026-10-26)

A rule is a past mistake written down so a machine can spot it again. It catches
known kinds of mistakes, never new ones. Four kinds of problem:

| Kind | Example | healthkit? | Cost of a rule |
|---|---|---|---|
| 1. Pattern (shape in one place) | `str(exc)` in a reply; raw `json.loads(request.body)` | yes (Opengrep) | about an hour with tests |
| 2. Structure (who may import whom) | a service importing a route file | yes (import-linter) | minutes |
| 3. Knowledge (needs the project's model) | soft-delete reads; `assert_perm` scope; protected-field `save()` | partly (Python guards) | a day or two each |
| 4. Behaviour (does it do the right thing) | a reset link working as a login; a race; a misleading message | **no** | tests, QA, people |

healthkit owns kinds 1-2, part of 3, never 4. Bugs nobody wrote a rule for are the job
of other layers: tests, behaviour testing ("never a 500" catches unknown bugs without a
rule per bug), advisory AI review, human review, production signals. Every escaped bug
gets the question "could a rule or test have caught it?".

healthkit never says "safe". It says what it checked and that it found no known problem.

Consequence: the behaviour pack (Schemathesis "never a 500") moves up, right after
slice 004.

## D-018 Operating model: agents run it, humans approve what "correct" means — decided (2026-10-26)

- **Run loop:** mostly AI coding agents run `healthkit review` before handing over and
  fix their own findings. healthkit needs a machine-readable output for them (later
  slice) alongside the human one.
- **Learn loop:** when something escapes, an AI drafts a rule and fixtures from the real
  case; the rule must fire on the incident and stay quiet on real code; **a human
  approves it.**
- **Separation of duties:** the agent that writes code must not be able to quietly
  change the referee (allow entries, exclusions, rules, contracts): the "genie" /
  reward-hacking risk. **Any change to `.healthkit/` is flagged for a human**, even when
  everything else is clean.

## D-019 Default exclusion: Django-named migrations only — decided (2026-10-27), supersedes slice 004 decision 3

The default was everything under `migrations/`. An agent could put real code there and
the gate would never see it (found by hand in slice 005); QuickRPA already has one such
file, `users/migrations/_inert_permissions.py` (99 lines, real code). The default is now
`**/migrations/[0-9][0-9][0-9][0-9]_*.py`: all 205 of QuickRPA's generated migrations
match; helper modules and `__init__.py` are reviewed. Other frameworks' migration
folders (e.g. Alembic `migrations/versions/`) need one line in `.healthkit/config.toml`
(D-004: Django first). Globs gained `[0-9]` / `[!0-9]` character classes.

## D-020 First measured value — recorded (2026-10-27), answers D-008

Replay on Susheel's users/auth review (slice 006): **9 of 45 findings caught (20%)** by
rules not written from those incidents; 11/45 with them. Pattern findings 8 of 12; knowledge
0 of 13; behaviour 1 of 15. Not fully out-of-sample (gate rules were chosen partly from the
same fixes), so the next module Susheel reviews is the clean measurement. Next slices are
ordered by this backlog: the f-string gap in `exception-text-in-reply` (small), then the
API pack (catches AA-40, AA-73, AA-75 without a rule per bug).

## D-021 The plan, revised by evidence — decided (2026-10-27), supersedes D-001's priority

The replay (D-020) showed where the value is. Of Susheel's 45 findings: 13 knowledge
(copies of shared code, token types, unused routes), 15 behaviour (3 of them 500s), 12
pattern, 4 judgement/naming. Rules caught 8 of 12 pattern and 0 of 4 naming. D-001 named
"names that lie" the first target; nobody chose to drop it, the work simply went
elsewhere. This records the change instead of letting it happen silently.

New order:

1. **API pack** ("never a 500"): catches bad-input crashes without a rule per bug.
   The f-string gap in `exception-text-in-reply` rides along.
2. ~~**QuickRPA knowledge pack**: soft-delete reads, `assert_perm` scope, protected-field
   `save()`, token reads outside their door: where QuickRPA's real bugs have been.~~
   Renamed by D-022: **project checks + Django pack** (slice 008).
3. **Live run on Susheel's next module**: the clean, out-of-sample measurement.
4. Near-copy detection (D-015) and an unused-route check.
5. **"Names that lie" moves from the gate to the advisory AI layer**: a rule cannot judge
   meaning reliably (0 of 4 in the replay).
6. Still pending, unchanged: baseline file, reviewer-style + machine-readable output,
   module scorecard.

Gains from rules written using the replay's misses are measured on new code only;
scoring them on the 45 they came from would be circular.

## D-022 healthkit never contains one project's knowledge — decided (2026-10-27)

D-021 step 2 was named after a customer ("QuickRPA knowledge pack"), and the first slice
008 draft followed it with a hard-coded list of QuickRPA's models. The owner stopped it:
healthkit is a separate project, built for every project.

- **healthkit ships** mechanisms (gate, project rules, project checks) and generic packs
  (Python, Django, API). A pack rule works on a project it has never seen, with no names
  from any one project in it.
- **A project's own knowledge** (its model lists, allow entries, commands, extra rules)
  lives in that project's `.healthkit/` folder, written by that team. This is what D-005
  calls the project pack: it is never shipped in this repo.
- **QuickRPA is the test bed**: where rules are measured and bugs are found, never what a
  rule is built for. Its config is written in the test-bed clone, as a customer would.
- A rule found in one project is measured on at least one other before it is called
  generic; when no second project is available, it ships marked "measured on one project".
- Slices are named after what they build, never after a customer.

## D-023 Advisory findings: shown, never blocking — decided (2026-10-27)

`soft-delete-read` found real bugs (one confirmed by running it on QuickRPA's local stack)
but measured about half precision on code it was never tuned on (QuickRPA held-out 41%,
mulearnbackend 55%), under the 70% slice 008 set for a rule that fails the gate.

- A rule below that bar ships **advisory**: printed as `worth a look: ...` and counted in
  the summary, never changing the exit code.
- A rule moves from advisory to blocking only when it reaches the bar on unseen code from
  at least two projects.
- Advisory findings follow the same changed-lines, exclusion and allow rules as the rest.

---

## Open

- **O-1 (rest) Final name; open source later or not.**
- **O-4 Where it runs while GitHub Actions is blocked.** Suggested: git pre-push hook
  plus a manual command.
- **O-5 Windows support of Opengrep.** Answered by slice 001 (the tool trial).

## Build plan (original estimates, one person; status as of 2026-10-27)

| Step | What | Time | Status |
|---|---|---|---|
| M0 | Design doc + repo skeleton; settle O-1..O-5 | 1 day | done |
| M1 | Tool trial on QuickRPA backend: keep or drop each candidate | 1 day | done (slice 001) |
| M2 | Core: diff filter, finding format, baseline, gate, report, replay harness | 3–4 days | mostly (slices 002-006); baseline file and reviewer-style report not built |
| M3 | Python pack: ruff + Opengrep adapters, names-that-lie and error-handling rules | 3–4 days | partly: adapters + 2 rules; names-that-lie moved to the AI layer (D-021) |
| M4 | Django pack + project packs (each project's own `.healthkit/`, D-022) | 3 days | partly: `.healthkit/` (slice 004); project checks + `soft-delete-read` (advisory) done (slice 008) |
| M5 | First replay score; first live run on Susheel's next module | 1 day | score done (slice 006); live run done (slice 009): 0 findings, recall needs a human review |
| M6 | API pack: Schemathesis "never a 500" sweep | 2 days | done (slice 007): 6 real crashes in QuickRPA; database reset per run not built |
| M7 | Module scorecard (pyscn + coverage per app) | 2 days | not started |
| — | Anti-silencing (exit 3, `--isolated`, suppressions, `.gitattributes`) | not planned | done (slices 004-005) |
| — | Routes nobody calls (D-021 step 4, part 1) | not planned | done (slice 010): 5/5 incident routes, 80-90% precision on QuickRPA |
| — | Copies (D-021 step 4, part 2; D-015) | not planned | done (slice 011): same-name helper (advisory) + racy cache counter rule; similarity engine measured and dropped |

Revised order: D-021.
