# Slice 011: near-copies of code that already exists (D-021 step 4, part 2; D-015)

Status: **approved** (2026-10-27, decisions 1-2); design reduced and approved 2026-10-28 after measurement

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

---

## Measured (2026-10-28), before any matcher was written

Each case at its fix's parent; application code only (`packages/`, the bot starter kit,
tests and migrations removed): about 420 files, 120,000 lines.

| Case | pylint `duplicate-code` | jscpd | same name across modules | own: similar functions (normalised tokens) | own: repeated statement |
|---|---|---|---|---|---|
| AA-03 rate limit copy | missed | missed | missed | missed | missed |
| AA-64 cookie rule ×3 | missed | missed | missed | missed | **found** (`samesite = getattr(settings, "AUTH_COOKIE_SAMESITE", "Lax")`) |
| AA-62 three sign-ins | missed | missed | missed | **the two token routes: 0.58**; Studio `login`: 0.23-0.27 | missed |
| `_get_workspace_or_404` ×9 | missed | exact copies only | **all 9, drifted ones too** | exact copies 1.00; the drifted copy **0.02** | missed |
| Reported per tree (noise) | ~15 blocks | ~340 pairs | 24 private names | ~20 pairs at 0.6 | ~179 statements |

What the numbers say:

- **The outside tools see only exact copies** (as pyscn did in slice 001). Neither is
  worth wrapping for this job.
- **AA-03 is not a near-copy at its parent.** The shared `check_rate_limit` had already
  been rewritten to an atomic increment; the copy kept the old racy shape (`cache.get` →
  compare → `cache.set(count + 1)`), which the helper's own docstring calls defect 1. No
  similarity measure can link code that no longer looks alike. It is a **pattern**: a
  non-atomic read-modify-write on a cache, a known race any Django project can write.
- **A drifted copy is found by its name, not its shape** (0.02 similarity, same name).
- **Two of the three sign-ins are near-copies** (0.58); the third repeats the same steps
  in different code: behaviour, not shape (D-017).
- **The repeated-statement view finds AA-64** but reports ~179 statements per tree:
  precision unknown, and the riskiest of the three for noise.

## Design (approved 2026-10-28, reduced after the measurement)

The owner asked whether it was worth it. Verdict: the similarity engine is not (one hit in
four, its noise unknown, exact copies already in pyscn's scorecard). Two cheap checks are:

1. **Same-name helper** (`copy-same-name`, in `review`, advisory per D-023): a branch adds
   or changes a private module function (`_name`, not `__dunder__`) that is also defined at
   module level in another file → one finding on its `def` line: "`_get_workspace_or_404`
   is also defined in 8 other file(s), 3 different version(s): ...". Versions are told
   apart by the function body's syntax tree (docstring dropped). Test files and excluded
   paths never count as the other copies. The only check that found D-015's drifted copies.
2. **Racy cache counter** (`cache-read-modify-write`, a built-in Opengrep rule): a value
   read with `$C.get($K, ...)` and written back with `$C.set($K, <value> + ..., ...)` →
   "not atomic: simultaneous requests read the same count; use the cache's increment".
   Catches AA-03 by its pattern, in any Python project.

**Dropped:** the near-copy similarity engine and the repeated-statement view (AA-64);
either returns only with a real case that needs it. Out of reach: AA-62's third sign-in
(same steps, different code).

## Acceptance (replaces the one above)

- AA-03's copy at `4cf0801^` flagged by the rule, the fixed shared helper not.
- A branch touching one `_get_workspace_or_404` at `7fadfe3`: the finding names the other
  8 files and 3 versions.
- Precision: every same-name group in QuickRPA and mulearnbackend read by hand (real copy
  or coincidence); every rule hit in both read by hand.
- Tests first, mutants; well under ~300 lines of source.
