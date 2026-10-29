# Slice 013: more ruff checks, chosen per project

Status: **approved** (2026-10-28)

## Measured first

Candidate ruff checks, run on QuickRPA `users/` (app code) and mulearnbackend:

| Check | QuickRPA `users/` | mulearnbackend |
|---|---|---|
| Missing docstrings (D100-D103) | 1,053 | 3,782 |
| Missing type hints (ANN001, ANN201) | 1,762 | 5,781 |
| Bare numbers (PLR2004) | 37 | 528 |
| Too complex (C901) | 3 | 412 |

Docstrings, type hints and bare numbers are a team's style choice: thousands per project.
Complexity is a quality signal for any project, but the threshold is a judgement.

## Design

1. **A project chooses extra ruff checks** in `.healthkit/config.toml`:
   `[ruff] extra = ["D1", "ANN", "PLR2004"]` (ruff rule codes or prefixes). They apply in
   `review` and `scan` and fail the run like the built-in ones; `baseline` hides the old
   ones. Changing the list is a `.healthkit/` change, so it needs a person (D-018).
2. **Complexity (C901) is on for every project, advisory** ("worth a look", D-023). The
   finding covers the whole function, so an edit anywhere inside a too-complex function
   shows it, not only an edit to its `def` line.

Covers Susheel's #41 (docstrings and type hints) and #42 (bare numbers) for teams that
want them. Under ~60 lines of source.

## Tests

- An extra rule from the project's config is reported; without the config it is not.
- A malformed `extra` (not a list of rule codes) is a config error (exit 2).
- A too-complex function is "worth a look" and never fails the run; an edit deep inside
  it is enough to show it.
- Mutants.
