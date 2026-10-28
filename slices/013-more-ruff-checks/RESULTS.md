# Slice 013 results: more ruff checks, chosen per project

## What exists

- `[ruff] extra = [...]` in `.healthkit/config.toml`: ruff rule codes or prefixes a team
  wants (`D1`, `ANN`, `PLR2004`, ...). Used by `review` and `scan`, failing the run like
  the built-in checks. Must be a list of codes (`PLR2004; rm` and typos like `extras` are
  config errors, exit 2).
- Complexity (`C901`, more than 10 branches) for every project, as "worth a look". The
  finding covers the whole function: an edit anywhere inside it shows it.
- README: the new setting and the complexity hint.

## Live run: QuickRPA `users/` (clone, baseline from slice 012 in place)

```
worth a look: users/management/commands/audit_role_tenancy.py:38: [ruff C901] `handle` is too complex (19 > 10)
worth a look: users/services/user_management.py:234: [ruff C901] `update_org_user` is too complex (13 > 10)
worth a look: users/tasks.py:138: [ruff C901] `clean_media_temp` is too complex (12 > 10)
healthkit scan: no known problems in 102 file(s) | ... | worth a look: 3 | ...
```

Exit 0: the hints show, never fail, and the 94 baselined findings stay hidden.

## Covers

Susheel's #41 (docstrings and type hints) and #42 (bare numbers), for any team that adds
them to `extra`.

## Verification

- Tests first: 4 failing before code, 5 green (the fifth asserts nothing changes without
  the project's choice).
- Mutants **6 of 6** caught (against `tests/test_ruff_extra.py`).
- Full suite **152 passed**; lint clean. Source: about 45 lines (`config.py`, `tools/ruff.py`).
