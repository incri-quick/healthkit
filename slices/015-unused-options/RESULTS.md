# Slice 015 results: options nobody sets

## What exists

`option-never-passed` (`tools/options.py`) in `review` and `scan`, advisory: a function
option (a parameter with a default) that no call in the project passes, by keyword or by
position. Calls are found by name across the project, tests included; a function never
called by name, or called anywhere with `*args`/`**kwargs`, is skipped. The finding covers
the signature only. README updated, including the `[[allow]]` advice for SDK code.

## The real case: Susheel's #23 (AA-09), at `beb9780^`

```
worth a look: users/services/login.py:138: [options option-never-passed] option `enforce_mfa` of complete_login() is never passed by any of its 3 call(s); it is always True
worth a look: users/services/passwords.py:22: [options option-never-passed] option `blacklist_refresh` of apply_password_set() is never passed by any of its 6 call(s); it is always True
```

Both switches found.

## Precision (measured with the prototype before building; same rules)

Today's QuickRPA app code, every 4th of 89, read by hand: **14 of 20 real**; 4 not (2 in
`qrlib`, the bot SDK, called from outside the repo; 2 signatures a framework dictates:
Django's `has_perm(perm, obj=None)`, a Celery hook); 2 debatable. 70% (80% at most).
Through healthkit on the clone: 99 hints in app code, 220 with `packages/` (builtin nodes a
framework calls: a project-level exclude).

## Verification

- Tests first: 3 failing against a stub, then green; one test added for an option after a
  positional argument (the case that proves positions are counted right).
- Mutants **11 of 11** caught (against `tests/test_options.py`).
- Full suite **164 passed**; lint clean. Source: about 110 lines (`tools/options.py`, `cli.py`).
