# healthkit feedback

Everything we learn from real use, in one place. **Nothing here is planned work.** Since
2026-10-29 healthkit is in a feature freeze: the team uses it, feedback is collected
here, and only then do we decide what (if anything) to build next.

## How to add feedback

One row per point, newest at the bottom of its table. Keep it short and concrete: what
happened, on which project, and what you expected.

- **Kind:** `bug` (healthkit is wrong), `noise` (a finding that was not a real problem),
  `missed` (a real problem healthkit did not report), `confusing` (output or docs unclear),
  `slow`, `idea`.
- Misses found while fixing bugs also go in that project's own `.healthkit/misses.md`;
  copy the ones worth discussing here.

## 1. Team feedback (to be filled in)

| Date | Who | Project | Kind | What happened | Expected |
|---|---|---|---|---|---|
| 2026-11-03 | Baibhav (with Claude) | QuickRPA backend | bug | `option-never-passed` said 5 options of `execute_node()` are "always None/False". The only *direct* call it saw was a new test; production calls it as `asyncio.to_thread(execute_node, …, execution_id=…, meta_out=…)` and passes every option. | Count a function passed as a callable (`asyncio.to_thread`, `sync_to_async`, `functools.partial`, `executor.submit`) as a call, or stay silent when such references exist. |
| 2026-11-03 | Baibhav (with Claude) | QuickRPA backend | missed | `C901` (too complex) is anchored on the `def` line. Filtering findings to changed lines — the only way to check uncommitted work, since `review` sees commits only — missed it twice when an edit inside a function pushed it over the limit (11 > 10, then 18). Caught only by listing every finding in the touched files. | A function-level finding belongs to the function's whole line span, so a changed line anywhere inside it brings the finding along. |
| 2026-11-03 | Baibhav (with Claude) | QuickRPA backend | confusing | Adding one more `except Exception as exc:` to a file whose existing ones are baselined reported the *last* identical line (`cache_guard.py:176`, untouched) as new, not the line actually added. | Point at the added line, or say "one more occurrence of an accepted finding in this file". |
| 2026-11-03 | Baibhav (with Claude) | QuickRPA backend | idea | What actually worked as a pre-commit check was "every finding in the files I touched" — it caught all three of the above. | A built-in `scan --changed-files` (working tree vs base) mode. |

Note on the C901 row (checked 2026-11-03): `review` already gives a "too complex" finding
the function's whole line span (`Finding.end_line`, slice 013), so an edit anywhere inside
it brings the finding along. The miss came from the hand-made changed-line filter used
because `review` cannot see uncommitted work. So it is one more case of signal 1 in 2d,
not a separate bug. The other three rows are new.

## 2. Outside test: the school project (FastAPI)

Five rounds, 2026-10-28 to 2026-10-30. Score: **55 → 62 → 68 → 76 → 72** out of 100.
Rounds 1-4 were API test runs; round 5 (section 2b) is daily use on every bug fix.

What it found in that project (so healthkit's value is visible):
- 26+ crashing routes (missing bounds on limit/skip, unchecked filter values, zero bytes
  in search text, out-of-range years);
- serious access leaks: any teacher could read all 469 parents' contact and citizenship
  details, every staff member's salary, and parent-only pages for any child.

Fixed in slices 019-022, from this feedback:

| Feedback | Fixed in |
|---|---|
| Only the first user was tested | 019 |
| The run changed data with no warning | 019 (reads only by default) |
| 403 routes counted as tested | 019 |
| "Stateful tests" hid a crashing route | 020 |
| Shallow routes counted but not named | 020 |
| Report folder could be committed by accident | 020 |
| Access leaks invisible (role-based) | 021 (`[[api.deny]]`) |
| Empty answer looked like a real leak | 022 (answer size) |
| Report folder kept personal data | 022 (temp folder deleted) |
| One "40 routes failed" count for everything | 022 (counts per kind) |

Still open (raised, not built):

| Kind | Feedback |
|---|---|
| idea | Per-user ids: one set of ids for all users, so "a parent opens her own child's page" is never tested. |
| confusing | Cross-user (ST402) lines say "as HK_ADMIN, HK_TEACHER" without saying who read whose data, and flag the admin, who may read everything. |
| slow | 21 minutes for four users (users run one after another). |
| idea | Group crashes by cause: 17 crashing routes were really 5 bugs. |
| missed | Create and update bugs are invisible in reads-only mode; needs a safe way to test writes against a throwaway database. |
| missed | Row-level leaks (the right role sees too many rows, e.g. all classes instead of her own) cannot be expressed as a deny rule. |
| confusing | A route that answers "bad input" (400/422) before checking who is asking can never be proven refused. |

## 2b. School project, round 5: daily use on every fix (2026-10-30), 72/100

Based on 50 lines in its `.healthkit/misses.md` plus every scan, review and API run.
Score went **down** from 76: the 76 was one API run; used day to day, `review` said
"no known problems" on branches that had real bugs.

**What it caught that mattered**

| Where | Catch |
|---|---|
| API check | Year-end promotion always crashing; nobody else had found it |
| API check | About 30 routes crashing on bad input (5 causes) |
| API check + access rules | A teacher reading 469 parents' citizenship numbers and every colleague's salary |
| API check | The profile `user_id` re-link: showed up as a crash, led to the bug |
| `review` during fixes | Import order on new lines (6 times); one function grown too complex |
| Full scan | Unused imports that `review` missed |

**The 50 misses by kind:** 21 behaviour, 11 knowledge, 2 judgement (mostly need a
person); 16 pattern or structure (13 + 3), which a generic tool could catch.

The 16, grouped as rules that would work on any Python web project:

| Possible rule | Misses |
|---|---|
| Uniqueness check that is case-sensitive (exact compare, or unique without `lower()`) | 5 |
| Check-then-insert with no conflict handling | 3 |
| "Active rows only" lookup guarding a rule that covers all rows, or used in edit/delete | 4 |
| The odd route out: most `/students/{id}/…` routes check ownership, one does not | 3 |
| Identity taken from the request: `user_id` in a body never compared with the caller, or `user_id`/role in an update form | 3 |
| Picker queries that forget "is active" | 2 |
| Unbounded limit/skip/page, free text compared with a fixed-choice column (findable without a server) | ~10 routes |
| One security check, several sign-in paths (check in one auth function, not its siblings) | 2 |
| Hand-written SQL naming a column the models do not have | 1 |
| An edit that breaks untouched lines (imports left unused just above an edit) | 1 |
| The same logic copied under different names (copy check matches names, not shape) | 1 |

**Noise and confusing output**

| Kind | What |
|---|---|
| noise | Cosmetic findings drowned the rest: 249 of the first 370 were import order and unused imports |
| noise | 17 false alarms on SQLAlchemy's string type names, reported as "undefined name" (F821) |
| confusing | `review` before a commit says "nothing to review", exit 0: looks like a pass (it does not see uncommitted work) |
| confusing | A baseline taken after a change silently hides that branch's own findings |
| missed | Access rules cannot see row-level leaks (a teacher seeing every class) |
| confusing | Cross-user wording: "as HK_ADMIN, HK_TEACHER" does not say who read whose data |
| slow | About 20 minutes for an API run with 4 users |

**Their requested features, in their priority order**

1. Compare roles in the API check: if a plain user's list is as big as the admin's, flag
   it. Would have found BUG-01, BUG-12 and NEW-01 with no rules written.
2. A built-in SQLAlchemy/FastAPI rule pack with the rules above (most of the 16).
3. `review` re-checks whole changed files for problems an edit caused (unused imports,
   undefined names), and has a mode for uncommitted work.
4. Ids per user in the API check ("a parent opens her own child").
5. Write runs on a throwaway copy of the database (create/update crashes like promotion).
6. Read the server's error log, when given access, to group crashes by cause.
7. Less noise: fold cosmetic findings into one line; understand SQLAlchemy string type names.

"To pass 85: the first three features." What it is good at: keeping changes tidy, and
the API check, "the most valuable part".

## 2c. QuickRPA, HITL module, daily use (2026-10-30), 65/100

**Caught that mattered**
- The engine crash (missing logger): an existing ruff check, reported as a real problem.
- A resume running a deleted robot version: a "worth a look" hint pointing at the exact
  line; reading the code confirmed it.
- The robot decide 409 leak: the API check showed the 409 but filed it under "not
  checked" instead of flagging it. Half a catch.
- Useful as a guard: 7 project rules now protect the HITL core laws on every change;
  `routes` confirmed every HITL screen route has a caller; `scorecard` showed where the
  complex code is; the baseline means only new problems show.

**Missed** (from its `misses.md`): mostly project knowledge a generic tool cannot have.

| Bug | Kind |
|---|---|
| Ending a workflow left its paused robot's approval pending (rule written afterwards) | knowledge |
| Robot approval page reads the live workflow (R-11) | knowledge |
| Robot approval rows never deleted (R-16) | knowledge |
| Decide 409 leak, shown but not flagged | behaviour |
| Studio approvals notify nobody (since ruled not needed) | behaviour |

**Noise and confusing output**

| Kind | What |
|---|---|
| confusing | **`review` says "nothing to review" when changes are not committed: looks like a pass while nothing was checked. "The most dangerous one."** |
| noise | Full scan: 2,207 problems, about 1,900 pure style (import order, `_name` variables, naming) or deliberate `except Exception` |
| bug | Project rules ignore their own severity: every rule is a full problem, no hint-level rule possible |
| noise | Project rules run on test files while built-in checks skip them: 23 false hits until tests were excluded |
| missed | A 409 to a must-refuse user counts as "not checked"; it leaks state and should be flagged |
| missed | One value per parameter name: `approval_request_id` means different things on Studio and robot routes, so one side always gets a guessed id |
| idea | `api` cannot be limited to some routes; a trimmed API description had to be made by hand |
| missed | The API check cannot create test data: with nothing pending, only refusals were tested, never a real approve |
| bug | A healthkit test run left a `.schemathesis/` cache inside the QuickRPA repo, not git-ignored |

**Their proposals** (all generic; they would do 1, 2, 5 first)

| # | Upgrade | Fixes |
|---|---|---|
| 1 | `review` checks uncommitted changes too, or warns and exits 2 instead of "nothing to review" | the silent false pass |
| 2 | Access policy flags 409 (and other state-revealing answers) to a must-refuse user | the decide-leak miss |
| 3 | Parameters per route, e.g. `[api.parameters."/robots/*/approvals/*"]` | colliding ids, shallow routes |
| 4 | `healthkit api --routes "<glob>"` | hand-made trimmed API descriptions |
| 5 | A setup command before the API check, e.g. `--setup "manage.py seed_x"` | real approve paths tested, not only refusals |
| 6 | Project rules honour severity: WARNING becomes "worth a look" | hint-level rules |
| 7 | Project rules skip test files by default, like the built-ins | false hits on fixtures |
| 8 | `healthkit rules test`: each rule runs against good and bad example files (Opengrep's rule tests) | proving a rule works |
| 9 | A "focused" default output: one count line for style, real findings in full | the noise |
| 10 | Multi-step API tests: follow linked routes (create, approve, read) | flow bugs a single call cannot show |
| 11 | Schemathesis's cache goes to a temp folder, never the scanned repo | the leftover folder |

Strong: safety (local only, tokens never written, reports deleted, writes only on
request), the access-policy idea, project rules, baseline and the `misses.md` loop.
Weak: few bugs found by itself in this module, noisy full scan, `review` silently skips
uncommitted work.

## 2c-2. QuickRPA, HITL module, after fixing the bugs (2026-11-02)

Verdict in one line: **"good at keeping fixed bugs fixed, weak at finding bugs in the
first place. In this pass, end-to-end scenarios found more than the scanner did."**

- Caught: the undefined logger in the workflow engine (scan), plus smaller issues.
- Missed, 9 real bugs:
  - 4 **knowledge** (product intent): approval page reading the live workflow instead of
    the version the robot ran (R-11); approval records blocking deletes (R-16); a
    cancelled run leaving its approval pending; the audit-log edit.
  - 5 **behaviour**, found only by running real scenarios: a healthy run force-failed;
    an approval during a busy robot creating no resume; the modern dispatch path never
    recording `robot_version_id`; the permission check running after the 409; Studio
    approvals notifying no one.
- Paid off: the project rules (`rules/hitl.yaml` 7 rules, `rules/audit.yaml`) now stop
  these bugs coming back. The "no noqa" rule worked: adding one forced a real fix or an
  `[[allow]]` with a written reason.

**Cheap problems hit**

| Kind | What |
|---|---|
| bug | Project rules scan test files: the config's `exclude` does not apply to them (at least on Windows), so `paths: exclude` was repeated in all 8 rules. Rules should inherit `exclude`, tests excluded by default |
| bug | `severity` in a rule file is silently ignored: honour it or reject it with a warning |
| confusing | `review` only sees committed changes; a script was written to check uncommitted work. Wants `--working-tree` / `--staged` |
| bug | A BOM in a rule file breaks parsing; PowerShell adds one by default. Strip it on load. **Not reproduced (2026-11-05, slice 027):** a rule file with a BOM, and with a BOM plus a comment first line and CRLF, both work in Opengrep 1.32.0 and `healthkit scan`. Needs the failing file before any fix. |
| confusing | The baseline is 2,748 entries, too big to read or trust; wants a per-path view (e.g. `scorecard --path studio_robot`) |

**API check problems**

| Kind | What |
|---|---|
| missed | A 409 to a must-refuse user was "not checked". For a must-refuse user, anything other than 401/403/404 is a leak, not only 2xx (how "409 before the permission check" slipped through). Note: they count 404 as a refusal; healthkit currently treats only-404 as "not checked" |
| missed | Role tokens are not confirmed to work: a wrong approver token makes its refusals look like passes. Before trusting refusals, check each allowed role gets a 2xx on one known route |
| idea | Test-data ids (`workflow_id = 80260`) sit in the committed `config.toml`; they belong in a git-ignored local override next to the token variables |

**Bigger upgrades proposed**

1. **Scenario runner** (they rank it the one that changes what healthkit can find): a
   file in `.healthkit/scenarios/`, a list of steps (start → pause → decide → resume),
   each with its expected status, run against the local stack with the role tokens.
   Every behaviour miss was found by such a script, not the scanner.
2. **Miss → rule draft**: a command that turns a `misses.md` entry into a draft rule, and
   the scorecard counting misses by kind over time, to show whether the tool improves.
   "`misses.md` was the most useful discipline in the whole process."
3. **Sibling code paths**: show "this function has two dispatch branches and the tests
   take only one" (the modern-dispatch miss: tests used only the legacy branch).

## 2f. QuickRPA, a teammate's answers to the 5 questions (2026-11-04)

From Sushil's session on an approvals feature (backend), answered question by question.

**1. Found what I would not have found myself**
- `api`: two real server crashes in `/audit/logs` and `/audit/statistics` from bad
  filter input ("null" dates, huge numbers). No test or review caught them; "this was
  healthkit's best catch".
- `review`: a function pushed over the complexity limit (the agent pause endpoint).
- The private-import and underscore-variable rules caught two careless changes from a
  bulk test edit.

**2. Noise**
- `scan` kept reporting the same 5 findings from someone else's merged work (the audit
  files), filtered out by eye on every run. `review --base` does not have this problem,
  so advertise `review` as the default and `scan` for full sweeps.

**3. Checked by hand, healthkit could have said it** (their three most useful)

| Kind | What |
|---|---|
| confusing | `review` reported "23 files, no problems" while two changed files sat uncommitted; after committing it found the complexity problem. Wants "N uncommitted files not reviewed", or a flag to include them |
| confusing | `api` only said at the END which user names the access rules expect ("access policy not checked: 10 … not given with --token-env"): a whole pass for nothing. Print the expected names at the start, or stop early when they are missing |
| idea | Tests that run only on PostgreSQL were silently skipped in local SQLite runs, and a real failure hid there. A note like "these tests cover your changed files but are skipped on this database" |

**4. Confusing output**

| Kind | What |
|---|---|
| confusing | "project checks are not run by scan" does not say which checks, or how to run them |
| confusing | "allowed: 1" and "baselined: 1" in `review` do not name the finding, so you cannot tell whether it is yours |
| confusing | About 155 routes "shallow (no valid sample data)": a large blind spot seen only as a number. (Checked: since slice 020 the routes ARE listed by name, but 155 lines get lost in the output, and nothing says how to give them sample data, i.e. `[api.parameters]`) |
| confusing | The import-order finding has no fix command, and ruff is not on PATH, so healthkit's own copy had to be dug out. A `healthkit fix`, or print the command |

**5. Would you run `review` before every push?** Yes: fast, shows only your lines. With
the uncommitted-changes fix it is the right pre-push check. Gap: the frontend repo has
no healthkit setup, so the React side of the feature got no checks (healthkit is
Python only).

**Can't be expected to catch:** the database review and the security review found the
deeper bugs (approvers moved instead of copied, a bot pausing under the wrong step, a
stale step cache). Design and logic, not linting. "healthkit plus a security/logic
review together is the real gate."

## 2e. Outside readers: the post about healthkit (2026-11-03)

Reach: Medium no response; dev.to 2 commenters (one an author of a similar tool, an AI
PR reviewer called RoastMyPR); LinkedIn only colleagues, not counted as outside.

| Kind | What they said |
|---|---|
| praise | The strict count (29 of 45 → 9 of 45 once a hit only counts when the rule points at the actual problem) is "the most honest number" in such a post. The PR-reviewer author hit the same trap: the hit rate looked great until checked against the real problem. "Distrust the metric that looks good." |
| praise | The pattern / knowledge / behaviour split: rules own shapes, never behaviour; a green check that pretends otherwise is false safety |
| praise | "The agent can't quietly change the referee" is the rule they would adopt first |
| question | Has the `.healthkit/` approval caught a real self-exemption? Our answer: mostly insurance. No deliberate attempt yet; the gate fired on 3 developer `# noqa` with reasons and on 1 agent-added `# noqa` (QuickRPA, resolved by a fix or a written `[[allow]]`). Three bypasses found while building (pyproject exclude, `# noqa`, `# nosemgrep`) were closed in slice 005. Their view: closing quiet routes is the gate's real job, more telling than a caught attempt |
| agreed design | The uncommitted-work gap is two problems. **Enforcement stays committed-only** (anything local can be switched off: hooks, `--no-verify`), and it judges by the base branch's rules. **The feedback loop** needs a `--working-tree` mode (diff against HEAD, staged and unstaged, same machinery) and never "nothing to review" with exit 0 while there are uncommitted changes. Same as team signal 1 below |

Lessons to keep: judge every new rule by the strict count before it ships; say
"insurance" when that is the truth.

## 2d. Asked by more than one project (the strongest signals)

| Ask | School project | QuickRPA | Teammate (Sushil) |
|---|---|---|---|
| `review` must not pass silently on uncommitted work | yes ("looks like a pass") | yes, twice ("the most dangerous one"; wrote a script around it) | yes ("23 files, no problems" with 2 uncommitted) |
| Fold style findings, show real ones in full | yes (249 of 370 cosmetic) | yes (~1,900 of 2,207 style; baseline 2,748 too big) | yes (others' findings in `scan`; unnamed "allowed/baselined") |
| Ids/parameters per user or per route, so the API check gets past "not found" | yes (per user) | yes (per route; and keep them out of the committed config) | yes (~155 shallow routes, no hint how to fix) |
| Create test data so write and flow paths are tested | yes (throwaway database) | yes (setup command, multi-step, scenario runner) | |
| The API check should flag more than 2xx as a leak or misuse | yes (row-level, via role comparison) | yes, twice (409 to a must-refuse user) | |
| Behaviour bugs are found by running scenarios, not by scanning | yes (21 of 50 misses were behaviour) | yes (5 of 9 misses; "scenarios found more than the scanner") | yes (deeper bugs found by database and security reviews) |
| The API check should check its own setup first (expected user names, working tokens) | | yes (role tokens not confirmed to work) | yes (expected names only shown at the end) |

## 3. Our own findings

### How healthkit was built (checked against its own `CLAUDE.md`, 2026-10-30)

Kept in slices 019-022: spec first, tests shown failing first, real data, pasted output,
mutant tests, the owner reading every diff, feature branches.

Drifted:

| Rule | What happened |
|---|---|
| 1. Decisions written down | Reads-only by default and the access policy are not in `DECISIONS.md` (it stops at D-023). |
| 2. Size budget about 1,500 lines, reported each slice | Source is now 2,456 lines; never reported, never asked. |
| 6. A fresh agent tries to refute each slice | Not done since slice 009 (mutant tests used instead). |
| 7. One lesson per slice in `LEARNINGS.md` | None written for 019-022 (stops at L-022). |
| 8. Claude never pushes or merges | Pushed and merged on the owner's explicit word; the rule text is out of date. |

### Sharing

- The GitHub repo is **private**: teammates need to be added as collaborators to install it.
- `slices/` notes contain internal QuickRPA findings (security weaknesses, review work).
  Clean them out before the repo is ever made public.
- The 8 anti-vibe-coding rules only govern building healthkit itself. The starter
  prompt for other projects carries only the healthkit-usage guards, not those rules.

### Not yet proven in real use

- `review` (the gate on changed lines) has now been used day to day once (school
  project, round 5) and was the weakest part: it said "no known problems" on branches
  with real bugs, did not see uncommitted work, and missed problems an edit caused just
  outside the edited lines. The API check is proven; the original core needs the most work.
- The Susheel replay (about 19 of 49 caught confidently) has not been measured again.

## 4. Questions for the team

1. Did healthkit find anything you would not have found yourself?
2. Which findings were noise?
3. What did you have to check by hand that healthkit could have told you?
4. Was any output confusing?
5. Would you run `healthkit review` before every push? If not, why not?
