# Slice 014: spelling

Status: **approved** (2026-10-28)

## Measured first

codespell 2.4.1 with its clear-cut dictionary (`--builtin clear`), words of 4+ letters:

| Project | Real typos | Not typos |
|---|---|---|
| QuickRPA app code | 11 (`succesfully`, `locahost` x2, `Dowloading`, `avialable`, `tempory`, `deleteion`, `defaul`, `secons`, `arrise`) | 6 (`re-used`, `re-uses`, `pre-empts`, `unparseable` x2, `Ines`) |
| mulearnbackend | 8 | 2 |
| Susheel #44 (`ca5c64e^`) | `liscense` x2: caught | |

Without the clear-cut dictionary and the length filter, short variable names (`nd`, `ot`,
`ser`) and rare words (`loner`) add noise. Some typos cannot be fixed: QuickRPA's database
field is named `liscense_key`.

## Design

1. A spelling check (codespell, pinned) in `review` and `scan`: clear-cut typos only,
   words of 4+ letters, hyphenated words ignored, `unparseable` accepted.
2. **Advisory** ("worth a look"): typos are minor, and some cannot be changed.
3. The project lists words to accept: `[spelling] ignore = ["liscense"]`.

## Tests

- A typo in a message is worth a look and never fails the run (Susheel #44's line).
- Short words, hyphenated words and `unparseable` are not reported.
- A word the project accepts is not reported; a malformed list is a config error.
- codespell missing is "could not check" (exit 2).
- Mutants.
