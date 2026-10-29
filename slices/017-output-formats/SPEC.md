# Slice 017: output for people, AI and pull requests

Status: **approved** (2026-10-28: "proceed to the best way"; the owner reviews the diff)

## Why

Results print as text for a person at a terminal. An AI assistant or a script needs them
structured; a pull request needs them as a comment; GitHub Actions (when it is back) shows
inline annotations. Item #9 of the plan.

## Design

`healthkit review` and `healthkit scan` take `--format`:

| Format | For | Shape |
|---|---|---|
| `text` (default) | a person | exactly today's output |
| `json` | AI assistants, scripts | one JSON object on stdout: exit code, summary, every finding with its kind (`problem`, `worth a look`, `check`), approvals |
| `markdown` | a pull-request comment | a verdict line, a table of problems, a "worth a look" section, approvals, the summary; post it with `gh pr comment <n> -F <file>` |
| `github` | GitHub Actions | `::error` per problem, `::warning` per hint, `::notice` per approval (inline on the PR) |

- Exit codes are the same in every format. Errors stay on stderr.
- GitHub's workflow-command text rules: `%`, CR and LF are escaped in messages, and `,`
  and `:` too in properties (file, title).
- healthkit never posts anything itself: posting a comment is the person's action.

## Tests

Each format on a real review (a branch with a problem, a hint and a settings change) and on
`scan`; JSON parses and matches the exit code; the text default is unchanged (the existing
tests); GitHub escaping on a message with `%` and a newline. Mutants.
