# Slice 004: project settings in `.healthkit/`

Status: **approved** (2026-10-26), including decisions 1-6

## Goal

A project tells healthkit three things, in one file it owns, `.healthkit/config.toml`:

1. **What not to check** (exclusions), on top of built-in defaults.
2. **Known exceptions** (allow entries), each with a written reason.
3. **Its own rules**: Opengrep rules in `.healthkit/rules/`, run next to the built-in
   ones. This is how project-specific rules live in the project, not in healthkit
   (D-002).

Nothing is hidden: the last line counts what was excluded and what was allowed.

## Out of scope

Baseline/ratchet, stale-allow detection (needs whole-file scans), report formats,
replay harness, packs (Django/Python split).

## Design

```toml
# .healthkit/config.toml
exclude = ["src/healthkit/rules/*.py"]   # added to the defaults

[[allow]]
rule = "raw-json-body"
path = "commons/payload.py"
reason = "This is the one shared JSON body reader the rule points everyone to."
```

- **Defaults, always on:** `**/migrations/**` (generated code; slice 002 showed Django's
  capitalised model variables there as false alarms) and `.healthkit/**` (rule fixtures).
- **Exclusions** remove files before any tool runs; import-linter findings in excluded
  files are dropped too.
- **Allow entries** match on rule and path (glob), not line numbers: lines move. An
  allowed finding is not printed but is counted.
- **Globs:** `*` stays inside one folder, `**` crosses folders. Matched against
  repo-relative paths with forward slashes.
- **Project rules:** if `.healthkit/rules/` has `.yaml` files, Opengrep gets it as a
  second `--config`.
- Last line, e.g. `... | ran: ruff, opengrep, import-linter | excluded: 4 file(s) | allowed: 1`.
- **Changes to `.healthkit/` are flagged for a human (D-018).** Any added, modified,
  renamed or **deleted** file under `.healthkit/` in the branch is listed as
  `needs human approval: .healthkit/...`. If that is the only thing found, the exit code
  is **3** ("clean, but a person must approve the referee change"); findings still win
  (exit 1), and "could not check" still wins over both (exit 2).
- **Wording (D-017):** a clean run says `no known problems on changed lines`, never
  that the code is safe.

## Failure modes (each gets a test)

1. No config file → defaults only; works as today.
2. Invalid TOML → exit 2, naming the file and the parser's message.
3. An allow entry without a `reason` (or an empty one) → exit 2, naming the entry.
4. An unknown key (a typo such as `exlude`) → exit 2. A typo must not silently do nothing.
5. A broken project rule file → exit 2 (Opengrep's own error, surfaced).
6. Config paths written with backslashes → normalised to forward slashes.
7. A pattern that excludes every changed file → still visible: "excluded: N file(s)",
   "nothing to review".
8. `commons/migrations_helper.py` must **not** match `**/migrations/**`.
9. A branch that **deletes** a project rule or an allow entry's file → flagged
   (deletions are invisible to the changed-lines diff, so this needs its own check).
10. A branch that only adds an allow entry (an agent "fixing" a finding by allowing
    it) → exit 3, the entry listed.

## Tests from real cases

- QuickRPA `users/migrations/0037_permission_override_nulls_not_distinct.py:30`,
  `Override = apps.get_model(...)` (N806, slice 002) → excluded by default.
- QuickRPA `commons/payload.py:54` (`raw-json-body` on the shared reader, slice 003)
  → allowed with a reason; counted, not printed.
- **A QuickRPA project rule from a real incident:** `_get_workspace_or_404` is defined
  in 9 route files in 3 drifted versions (slice 001, D-015). A project rule in
  `.healthkit/rules/` flags a new local definition of it; a branch adding one is reported.
- healthkit itself, with its own `.healthkit/config.toml` excluding its rule fixtures
  → **clean** (closes the slice 003 gap).

## Acceptance

- Tests first, shown failing; green; at least two mutants on the glob and two on the
  allow logic, all caught.
- healthkit on its own repo: 0 findings.
- QuickRPA throwaway clone with a `.healthkit/config.toml` (contract, allow entry,
  project rule): output pasted; the payload.py finding shown as allowed; migrations
  excluded.
- Under ~300 lines of source (D-016).

## Needs approval

1. **Python 3.11 or newer** (was 3.10). TOML reading is in the standard library from
   3.11 (`tomllib`); 3.10 reaches end of life this month (October 2026). The
   alternative keeps 3.10 and adds the `tomli` package as a dependency.
2. **TOML** for the config, in `.healthkit/config.toml`.
3. **Default exclusions:** `**/migrations/**` and `.healthkit/**`. Tests are *not*
   excluded: test code is code.
4. **Strict config:** unknown keys and missing reasons are errors (exit 2), never ignored.
5. **Allow entries match rule + path, not line numbers.** Detecting entries that no
   longer match anything needs whole-file scans; it is deferred.
6. **Exit code 3 = "needs human approval"** for a branch whose only issue is a change
   to `.healthkit/` (D-018). A pre-push hook can let it through; a PR check can require
   a person. Existing codes keep their meaning: 0 clean, 1 findings, 2 could not check.

## Lesson this slice teaches

Exceptions are part of the rules. An exception without a written reason, or a typo
that silently disables a setting, is how a gate quietly stops checking.
