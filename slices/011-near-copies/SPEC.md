# Slice 011: near-copies of code that already exists (D-021 step 4, part 2; D-015)

Status: **approved** (2026-10-27), including decisions 1-2. Starts after slice 010 ships.

## Goal

On a branch's changed lines: "this looks like `X` in `Y`; use it, or share one copy". In
the replay, 3 of the 13 knowledge misses were copies that had drifted:

- **AA-03:** the password-reset limit re-implemented the shared `check_rate_limit`
  (read, compare, write; not atomic: 10-20 requests got through instead of 5).
- **AA-64:** the cookie SameSite/Secure rule written out three times.
- **AA-62:** three sign-ins repeating the same steps.

Plus `_get_workspace_or_404`: 9 route files, 3 drifted versions (D-015).

## Why the existing tools missed them (slice 001)

pyscn found only exact copies, and these are not exact: names differ, a step is added or
dropped, a constant changes. That drift is the danger: a copy that differs is a bug in one
of the two.

## Measure first (L-006), then decide

Run on the four cases above, at each fix's parent, before writing any matcher:

| Candidate | What it compares |
|---|---|
| pylint `duplicate-code` | lines, after dropping comments, docstrings, imports |
| jscpd | token windows, names optionally ignored |
| same-name functions across modules | names only (found `_get_workspace_or_404`) |
| healthkit's own: normalised syntax-tree fragments | statements with names and constants replaced, compared by similarity |

The spec's design is then fixed by what finds the four cases with the least noise. If an
outside tool does, healthkit wraps it (D-005); it builds its own only if none does.

## Design shape (whatever the matcher)

- In `review`, changed lines only: a changed function or block that is a near-copy of code
  elsewhere in the repo is one finding naming the other place.
- Advisory (D-023) until it reaches 70% precision on unseen code from two projects.
- Tests, migrations and `packages/`-style by-design copies are configured as exclusions
  in the project, not hard-coded.

## Acceptance

- The four cases found at their parents (each found / missed, stated).
- Precision on today's QuickRPA and on mulearnbackend, 20 hand-read each.
- Under ~300 lines of source.

## Needs approval

1. **Measure the four candidates first**; the matcher is chosen by the result.
2. **Advisory** until measured otherwise.
