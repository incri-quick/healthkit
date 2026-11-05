# Slice 028: the API check states its setup first, and a refusal must be comparable

Status: **approved** (2026-11-05, "proceed to open one"). Phase 2, item 1 (D-027).

## Why (`FEEDBACK.md` 2f and 2c-2)

- A teammate: "`api` didn't tell me the user names its access rules expect until the end
  ('access policy not checked: 10 … not given with --token-env'). I ran a whole pass for
  nothing. It should print the expected names at the start."
- QuickRPA: "It doesn't confirm the role tokens are set up right. If the approver token is
  wrong, its refusals look like passes. Before trusting refusals, it should check that each
  allowed role gets a 2xx on one known route."

## Measured first (healthkit f4c21cd)

- `[[api.deny]]` users that were not given are reported only after the run, under "access
  policy not checked" (`policy.check`): a 20-minute run on the school project with 4 users.
- `policy.check` counts a route "refused as required" whenever the denied user got
  401/403, whatever every other user got. If the route refuses everyone (an allowed
  user's token lacks a permission, or the route is broken), the refusal proves nothing and
  still counts.
- A token that works on nothing is already exit 2 (slice 019). The gap is a working token
  without the permission, on the routes that matter.

## Design

1. **Before the run**, when the project has `[[api.deny]]` rules:
   `access policy expects: HK_MEMBER, HK_OTHER_ORG; not given: HK_OTHER_ORG (add
   --token-env HK_OTHER_ORG, or its rules are not checked)`. Printed first, then the run
   goes on, as before.
2. **A refusal counts only when another user was answered successfully (2xx) on the same
   route.** Otherwise it is "not checked": `GET /x as HK_MEMBER: refused, but no user got
   a successful answer here, so the refusal proves nothing (is an allowed user's token set
   up?)`.
3. **With a single user** there is nothing to compare: refusals count as before, and the
   summary says `refusals not compared with an allowed user (give one more --token-env)`.

## Failure modes, each with a test

- a deny rule for a user not given: named before the run (printed ahead of the results);
- two users, the route refuses both: not checked, with the reason;
- two users, the route answers the other user: refused as required;
- one user: counted as before, with the "not compared" note;
- a deny rule whose user was given: no "not given" text.

## Acceptance

Tests failing first (the unit ones on synthetic statuses: the test API has no route that
answers one user and refuses the other); mutants; full suite; README; line count (budget
asked again); fresh-agent check with its log file read before it is believed.
