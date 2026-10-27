# Slice 004 results

## What exists

A project tells healthkit, in `.healthkit/config.toml`, what not to check
(exclusions), which known exceptions to accept (allow entries, each with a written
reason), and adds its own Opengrep rules in `.healthkit/rules/`. Any change under
`.healthkit/` (including deletions) is flagged "needs human approval" with exit 3
(D-018). A clean run says "no known problems on changed lines" (D-017).

Source: 562 lines total, ~157 added (D-016). Python 3.11+ (`tomllib`).

## Evidence

- Tests written first, shown failing (no `config` module); 56/56 green (~75 s).
- **7 mutants, all caught on green code** (`mutants.py`, shared harness
  `slices/mutate.py`). The first round had **4 survivors**, each a real test gap:
  `**/` with zero folders (top-level `migrations/`), allow ignoring the rule, allow
  ignoring the path, exclusions not applied to whole-project tool findings. Each got a
  test; the last one needed a second changed file so the tools actually run.
- Strict ruff and formatter: clean.
- **healthkit on itself:** `no known problems on changed lines in 8 file(s)`, exit 3
  because this slice adds `.healthkit/config.toml`. The slice-003 gap (its own rule
  fixtures flagged) is closed.
- **QuickRPA throwaway clone** (dev `7fadfe3`; contract, allow entry and project rule
  in its untracked `.healthkit/`; the backend repo untouched), base `220f7b3`:
  `71 finding(s) on changed lines in 207 file(s) | ran: ruff, opengrep, import-linter
  | excluded: 8 file(s) | allowed: 1`, exit 1, ~8 s.
  - 8 migration files excluded; 2 of the 3 earlier `N806` false alarms gone (the
    third is a script under `docs/`).
  - `commons/payload.py` allowed with its reason, counted, not printed.
  - Project rule `no-local-workspace-lookup`: 0 hits, **checked**: all 9 copies of
    `_get_workspace_or_404` are on lines unchanged in the range; scanned directly, the
    rule matches existing copies, including the drifted one with swapped arguments.

## Independent verification

The fresh agent reported "25 of 25 passed, no vulnerabilities" with **no pasted output**
for any case (L-010 again). Two of its "passes" were warnings, re-run by hand:

- **`.Healthkit/` bypass (real bug, fixed).** On Windows, `.Healthkit/config.toml` was
  loaded as the config (case-insensitive filesystem) but the approval check asked git
  for `.healthkit` exactly. A commit adding an allow-everything entry there plus a raw
  JSON read gave **exit 0, "no known problems"**, and no approval flag. Now matched
  ignoring case; test added (platform-independent: the flag must appear, exit ≠ 0);
  mutant added.
- **A config saved with a byte-order mark failed the whole review** (exit 2). Safe but
  needlessly blocking on Windows. Now read as `utf-8-sig`; test added.

## My mistakes in this slice

1. A Python fix-up script used `Path.write_text`, which on Windows writes CRLF; three
   source files silently changed line endings and a multi-line mutant stopped matching.
   The shared harness refused to run it rather than passing it.
2. I wrote a new test with the wrong line number (9 instead of 7), then ran the
   mutants while that test was failing, so every mutant looked "caught". Results
   discarded; real code made green first, mutants re-run.
3. The first version of the exclusion test excluded the only changed file, so no tool
   ran and the code under test was never reached.

## Known gaps

- **The gate can still be silenced without touching `.healthkit/` (found 2026-10-27,
  before commit).** In a throwaway repo, one commit hid three real findings with no
  "needs human approval": `extend-exclude = ["a.py"]` in `pyproject.toml` (hid an
  F401; healthkit honours project ruff excludes since slice 003's `--force-exclude`),
  `# noqa: F401` on the line, and `# nosemgrep` on a raw-json-body line. Only an
  unrelated I001 was reported (exit 1). Proposed fix for the next slice: ruff with
  `--isolated` (exclusions only from `.healthkit/`), and new suppression comments on
  changed lines flagged for a human.
- Stale allow entries (no longer matching anything) are not detected: needs whole-file
  scans.
- `.healthkit/` changes are seen only when committed (the gate reviews commits).
- Project rules have no `healthkit` command to test them; `opengrep test .healthkit/rules`
  works by hand.

## Lesson

Exceptions are part of the rules. Every exception path (exclude, allow, project rule,
referee change) got a test that tries to abuse it, and four of those tests only exist
because a mutant survived.
