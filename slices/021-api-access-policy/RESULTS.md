# Slice 021 results: the access policy

## What changed

- **Config:** `[[api.deny]]` takes `user` (a `--token-env` name), `routes` (`METHOD /path`
  patterns, `*` one segment, `**` any) and `reason`. It is strict, like the rest of the
  config: missing keys, unknown keys, an empty list or a route without a method or a path
  are all config errors.
- **New module:** `src/healthkit/policy.py`. For each rule and each tested operation it
  matches:
  - any 2xx answer to that user is a finding, `[policy must-refuse]`, naming the user,
    the status and the rule's reason;
  - else any 401 or 403 is refused as required (counted in the summary);
  - else it is listed under `access policy not checked`, with the statuses seen.
- **Never silent:**
  - a pattern that matches no tested operation is exit 2;
  - a write route in a reads-only run is listed as not checked;
  - a rule for a user not given with `--token-env` is listed as not checked.
- **Adapter:** `ApiRun.statuses` gives, per user and per operation, the statuses answered
  to that user's login. These come from the event log (slice 019). Each user's run is now
  a small record (`_UserRun`) instead of a growing tuple.
- `[[allow]]` with rule `must-refuse` applies, as for every finding.

## Live check (the school project's teacher run, its own report folder, read only)

The rules were mine, written to match what that project's AI called leaks:

- teacher denied the `/people/*` lists;
- teacher denied `GET /parent/**` and `GET /finances/**`.

Result:

- **8 leaks (2xx to the teacher):**
  - `/people/students`, `/people/parents`, `/people/staff`, `/people/teachers`;
  - `/parent/child/{student_id}/attendance`, `/parent/child/{student_id}/fees`,
    `/parent/child/{student_id}/marks`, `/parent/my-children`.

  The last three were **not** in that AI's hand-made list: it had tested one parent page.
- **17 refused as required:** finances, `/people/users`.
- **1 not checked:** the payment receipt answered only 404 (no real ids).

Limit, stated in the README: a deny rule catches a route open to the **wrong role**. It
cannot catch a route open to the right role that returns too many rows, such as a
teacher who may list students but gets all 400 instead of her class's 36. Whether the
teacher should see `/people/students` at all is that project's call, not healthkit's.

## Tests

`tests/test_api_policy.py`, 11 tests, all failing before the code:

- refused route passes;
- 200 is a finding naming user, status and reason;
- `*` wildcard;
- typo is exit 2;
- write route in a reads-only run, a route answering only 404, and a missing user are
  each listed as not checked;
- 6 malformed rules are config errors.

## Mutants: 9 of 9 killed

2xx not a leak · any answer counts as refused · 403 not a refusal · typo only listed ·
write route in reads-only an error · exact match only · policy errors not exit 2 · any
route text accepted · policy findings dropped.

## Full suite

207 passed (9 min), with `HEALTHKIT_OPENGREP` set.
