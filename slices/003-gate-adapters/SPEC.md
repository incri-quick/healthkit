# Slice 003: the other two gate tools

Status: **approved** (2026-10-26), including decisions 1-3

## Goal

`healthkit review` runs all three pre-push gate tools from D-014, not just ruff:

- **Opengrep** with healthkit's own rules (the two tested in slice 001:
  `exception-text-in-reply` from AA-15, `raw-json-body` from AA-65).
- **import-linter** with the project's layer contract (from AA-06).

Each tool's output, in three different shapes, becomes the same `Finding`, filtered
to changed lines. The last line says which tools ran.

## Out of scope

Project config folder `.healthkit/` beyond the one contract file, default
exclusions (migrations), baseline, report formats, replay harness.

## Design

- **Adapter shape:** every tool module exposes `run(root, files) -> list[Finding]`
  and raises `ToolError` when it could not check. `cli.py` loops over the tools.
- **Opengrep:** JSON output. Rules ship inside the package
  (`src/healthkit/rules/*.yaml`) with their fixtures; `opengrep test` on them is part
  of healthkit's own test suite. Run on changed files only. Opengrep's own
  `errors` list (for example a per-file timeout) is a `ToolError`, never ignored
  (L-004).
- **import-linter:** text output only (slice 001), so the adapter parses lines like
  `users.services.login -> users.api.users (l.169)`. It runs on the whole project
  (under 1 s) and keeps links whose **importing line** was changed by the branch.
  Module names map to `pkg/mod.py` or `pkg/mod/__init__.py`. The contract is read
  from `.healthkit/importlinter.ini` in the target repo.
- Last line, e.g. `healthkit: 3 finding(s) ... | ran: ruff, opengrep, import-linter`.

## Failure modes (each gets a test)

1. Opengrep binary not found → exit 2 with an install hint (see decision 1).
2. Opengrep reports errors in its JSON (timeout, parse error) → exit 2, files named.
3. Opengrep output not JSON → exit 2.
4. No `.healthkit/importlinter.ini` → import-linter **skipped**, said so in the last
   line; not an error (there is nothing to check against).
5. import-linter exits with a config/usage error (not "contract broken") → exit 2.
6. A broken-contract link on an **unchanged** line → not reported.
7. A link whose importing module is a package `__init__.py`.
8. Import inside a function (the AA-06 shape) → reported at that line.
9. One tool fails while others ran → exit 2; findings from the others still printed.

## Tests from real cases

- AA-15: `except Exception as exc: raise PasswordResetError(400, str(exc))` added
  by the branch → `[opengrep exception-text-in-reply]`.
- AA-65: `data = json.loads(request.body) if request.body else {}` added → reported.
- AA-06: `users/services/login.py` adds an in-function
  `from users.api.users import _set_auth_cookies` with an `api` above `services`
  contract → `[import-linter api-above-services]` at that line.
- Fixtures for tool output formats are captured from the real tools (L-006).

## Acceptance

- Tests written first and shown failing; then green. Two mutants per adapter caught.
- Strict ruff clean; healthkit on its own repo clean.
- QuickRPA backend, read-only, base `220f7b3`, with the slice-001 contract copied to
  a throwaway `.healthkit/` (not into the backend repo): output pasted; the
  storage-bucket `str(exc)` findings and the studio_robot private-helper imports are
  reported only where those lines changed in the range.
- Under ~300 lines of source (D-016).

## Needs approval

1. **A missing Opengrep fails the review (exit 2)**, with an install hint. It is not
   silently skipped: a gate that quietly drops a tool would report a pass it did not
   check (L-004). The alternative is "skip with a notice", which D-005 allowed; this
   slice proposes the stricter rule for gate tools.
2. **healthkit does not download Opengrep.** The user installs the signed binary
   (slice 001 recorded how to verify it). healthkit finds it on `PATH` as `opengrep`,
   or at the path in `HEALTHKIT_OPENGREP`. Tests use the same variable.
3. **The two rules ship with healthkit as built-in rules.** `raw-json-body` is
   Django-flavoured; it moves to a Django pack when packs exist (slice 004+).

## Lesson this slice teaches

An adapter's job is to make three different tools look like one, and to make a tool
that did not run impossible to mistake for a tool that found nothing.
