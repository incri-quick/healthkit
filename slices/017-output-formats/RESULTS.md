# Slice 017 results: output for people, AI and pull requests

## What exists

- `--format text|json|markdown|github` on `review` and `scan` (`report.py`). Same exit
  codes in every format; errors stay on stderr.
  - `json`: `exit`, `summary`, `details`, `findings` (each with `kind`: problem, worth a
    look, check; checks carry their output), `approvals`.
  - `markdown`: a pull-request comment: verdict heading, a table of problems, the project's
    failed checks with their output, hints, approvals, the summary, and the line that a clean
    result never means "safe". Posting is the person's action (`gh pr comment -F`).
  - `github`: `::error` / `::warning` / `::notice` workflow commands, escaped per GitHub's
    rules (`%`, CR, LF; also `,` and `:` in properties).
- `review` and `scan` now build one report and print it once (the text is unchanged: every
  existing test still passes on it).
- README: the formats, how to post a comment, and the AI instructions switched to JSON.

## Live run: the planted branch in the QuickRPA clone (slice 008)

`healthkit review --base hk-base --format markdown` gave a ready-to-post comment: the
failed tenancy guard with its output, the soft-delete hint, the summary. It also showed a
real bug: on Windows, output redirected to a file was written in cp1252, so the comment's
separator arrived as `�`, and a character with no cp1252 byte (`→`) crashed the output.
Machine formats now switch stdout to UTF-8; a test reproduces the crash first.

## Not done

GitHub annotations are written but not yet seen in a real Actions run (Actions is stopped);
the format follows GitHub's documented rules and is tested for escaping.

## Verification

- Tests first (5 failing against a stub, the text default already passing), then 7 green
  including the UTF-8 crash test.
- Mutants **11 of 11** caught (against `tests/test_formats.py`).
- Full suite **179 passed**; lint clean. Source: `report.py` 138 lines; `cli.py` shorter (+25 −38).
