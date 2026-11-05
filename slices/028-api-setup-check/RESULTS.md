# Slice 028 results: the API check states its setup first, and a refusal must be comparable

Phase 2, item 1 (D-027).

## What changed

- **The users the access rules expect are named before the run**, on the first line, when
  some are missing:
  `access policy expects: HK_OTHER_ORG, HK_TOKEN_A; not given: HK_OTHER_ORG (add
  --token-env HK_OTHER_ORG, or its rules are not checked)`. Nothing is printed when all
  are given, or when there are no `[[api.deny]]` rules. The run then goes on as before
  (`policy.expected`).
- **A refusal counts only when some user got a successful answer (2xx) on that same
  route.** A route that refuses everyone proves nothing: an allowed user's token may lack
  the permission, or the route may be broken. It is now listed as not checked:
  `GET /approvals as HK_MEMBER: refused, but no user got a successful answer here, so the
  refusal proves nothing (is an allowed user's token set up?)` (`policy._answered_someone`).
- **With one user** there is nothing to compare: refusals count as before, and the summary
  says `refusals not compared with an allowed user (give one more --token-env)`.
- README: give `--token-env` for an allowed user as well as the denied ones.

## Measured first

- Missing users were named only after the run. The teammate's case: a whole pass wasted;
  the school project's 4-user run took about 20 minutes.
- A refusal counted whatever the other users got, so a route refusing everyone counted
  as "refused as required". QuickRPA: "if the approver token is wrong, its refusals look
  like passes".

## Live run: not done

This slice changes the API check, which needs a running app and real user tokens.
healthkit's rules forbid Claude handling them, and no local stack was running. The
behaviour is covered on the test API (the before-the-run line) and on statuses built to
match QuickRPA's case (approver refused on the approvals route, answered elsewhere). The
first real proof is the next teammate's API run.

## Tests

`tests/test_api_setup.py`, 6 tests:
- the expected users on the first line, and the single-user note in the summary, on the
  test API;
- nothing said when every user is given;
- a route refusing everyone proves nothing;
- a success on another route does not count (added from a surviving mutant: QuickRPA's
  exact case);
- a refusal counts when another user was answered;
- one user counts as before.

3 failed before the code; 2 passed already (behaviour that must not change). All 51
existing API tests still pass unchanged.

## Mutants: 7 of 7 killed

Never compared · single user compared too · any answer counts as success · another
route's answer counts (survived first; killed by the added test) · setup never said ·
said even when complete · single-user note missing.

One more mutant was equivalent, and the code was simplified instead of tested: leaving the
denied user out of "did anyone get a 2xx here?" changed nothing, because that user's own
2xx is reported as a leak before this check is reached. The filter was removed.

## Full suite

277 passed (13 min), with `HEALTHKIT_OPENGREP` set.

## Checklist (L-026)

- **Line count:** 2,689 non-blank lines in `src/` (was 2,649; +40). Over the 2,500 budget (D-028); the 3,000 proposal is still unanswered (the owner said "commit" with the count shown),
  so it is asked again.
- **D-/L- entries:** none new.
- **Fresh-agent check:** done, with its log read (304 lines) before it was believed: all
  4 claims confirmed, no defects. The log holds real runs for the edge cases asked:
  - an allowed user answered only 500 (a crash) does not vouch for a refusal;
  - a user given twice still counts as given;
  - a glob matching several routes is judged route by route.

  It left the healthkit repo untouched this time (nothing staged). Its scratch scripts
  in the temp folder and its log were removed afterwards.

## Uncertain

- With several users, if the only users given are all denied on a route and none is
  allowed there, every refusal on it is "not checked". That is the intended honesty, but a
  project must now pass an allowed user to get any "refused as required" at all.
