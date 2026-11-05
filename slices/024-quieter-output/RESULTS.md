# Slice 024 results: quieter output, style folded, quoted type names as hints

## What changed

- **`scan` folds import order (ruff I001) and unused imports (F401) into one line** in
  `text` and `markdown`, with the command that fixes them:
  `style: 243 finding(s), import order (I001) 130, unused imports (F401) 113, in 83
  file(s). Fix: uvx ruff@0.17.2 check --isolated --fix --select I001,F401 app`.
  The targets are the folders scanned. Exit code and summary count are unchanged; `json`
  and `github` still list every finding.
- **`review` lists them in full** (your own lines keep their line numbers) **plus the same
  fix line**, naming the files (10 at most, then "and N more").
- **ruff F821 on a name inside a string literal becomes "worth a look"**, with
  `(inside a quoted type: often a forward reference resolved at runtime)`. Unquoted names
  and names in f-string `{...}` expressions stay problems. Decided with Python's parser:
  ruff's position must fall inside a `str` constant.
- `report.py`: `STYLE`, `_fold()`, `Report.fix_targets`; the fix command is built from the
  ruff adapter's own `COMMAND`, not a copy of its version. `ruff.py`: `in_quotes()`; the
  whole-function span is now tied to C901 itself.
- README: both.

## Changed while building

The spec folded style in `review` too. That broke 25 older tests, and they showed why it
was wrong: in `review` the style findings are on your own few changed lines, where the
line number is the point. The volume the feedback measured was in `scan` (both numbers
were whole-module scans). So only `scan` folds. 3 older scan tests now read the JSON
output for the same facts (file, line, rule); one of them first became stricter than
before and was brought back to its original strength.

## Measured first

| Rule | QuickRPA baseline (2,748) | School baseline (370) |
|---|---|---|
| I001 import order | 978 (36%) | 135 (36%) |
| F401 unused import | 347 (13%) | 114 (31%) |
| BLE001 / RUF052 (not folded: policy, and a real bug class) | 429 / 242 | 55 / 0 |
| F821 | 1 | 17, all inside quoted types |

## Live runs (throwaway clones, baselines removed so the full volume shows)

- **School project, `scan app`:** 243 style findings became one line; the output went from
  about 365 lines to 123. All 17 F821 are now hints (17 hints, 0 left as problems).
- **QuickRPA, `scan studio_robot`:** 183 style findings became one line; the 133 findings
  that need a person stay in full (BLE001 64, RUF052 48, PLC2701 12, N806 5, 3 project
  rules, F811 1); 168 lines instead of about 350.
- Both originals untouched (git status unchanged, baselines intact). The clones
  `C:\tmp\hk24-school` and `C:\tmp\hk24-qrpa` could not be deleted by Claude (a safety
  check: one had become the session's working folder); left for the owner.

## Tests

`tests/test_quieter_output.py`, 11 tests. 6 failed before the code (the JSON test passed:
JSON must not change). Added during the slice:
- the parser edge cases: an unparsable file keeps its finding; f-string code vs quoted
  text;
- a boundary test from a surviving mutant (`x = [Y,"s"]`: the name right before a string
  is not inside it);
- the non-ASCII test from the bug below, shown failing before the fix.

## Mutants: 12 of 12 killed

Review folds too · scan does not fold · no cap on named files · scan fixes files instead of
its folders · folders ignored · quoted F821 still a problem · every F821 a hint · hint not
explained · column off by one (survived first; killed by the boundary test) · bytes not
counted (added with the fix) · any expression counts as a string · an unparsable file
turns a hint.

## A bug found after the fresh-agent check

The fresh agent reported the non-ASCII case "works correctly" with no run pasted (L-001:
that counts for nothing), so it was run by hand:

- `naïve: "Café"` and the unquoted `naïve2 = [Y,"s"]`, `λ = Zed` were right;
- **`ééé: "Gone" = 1` was wrong**: a quoted name, still reported as a problem. ruff counts
  characters (column 7), Python's parser counts bytes, and 3 two-byte letters put the
  position before the string's start.

The error was in the safe direction (a hint stayed a problem), but wrong. Fixed by
turning ruff's character column into a byte offset from the line's own text. Test first,
then the fix.

## Full suite

249 passed (12 min), with `HEALTHKIT_OPENGREP` set, after the non-ASCII fix.

## Checklist (L-026)

- **Line count:** 2,556 non-blank lines in `src/` (was 2,505; +51). **Over the 2,500
  budget again (D-028): put to the owner,** who said "commit" with the count in front of them (2026-11-05). The proposal to raise the budget to 3,000 for the restart phase was not answered: D-028 stays at 2,500 and the next slice asks again.
- **D-/L- entries:** L-027 (below) proposed; no new decision.
- **Fresh-agent check:** done. The verifier pasted real runs for the fold (scan text, the
  fix command fixing 3 of 3) and reported all 4 claims confirmed, no defects. Its
  non-ASCII verdict came without a run; checked by hand, it was wrong (above).

## Uncertain

- F401 is folded as style, but an unused import is occasionally a real mistake (a
  feature never wired up). It still counts as a problem and is listed by `review`.

## Lesson (L-027)

The 25 broken tests were the design review. When a change breaks many old tests, read
what they protect before rewriting them: here they protected `review`'s line numbers, and
the design was narrowed instead of the tests.

And L-001 held again: the one verdict the fresh agent gave without a pasted run was the
one that was wrong.
