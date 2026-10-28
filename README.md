# healthkit

healthkit checks Python code for problems that tools can find reliably, so people (and AI
reviewers) can spend their time on the problems tools cannot. It works on any Python
project; Django and web APIs get extra checks.

**What it can never judge:** whether the logic is right, whether it is secure, whether the
design is right, whether a name means the right thing. A clean healthkit run means "nothing
it knows about", never "safe". Those questions still need a person.

## Install

You need [uv](https://docs.astral.sh/uv/) and Python 3.11 or newer.

```
uv tool install <path-or-git-url-of-this-repo>
```

One checker, Opengrep, is a separate download: take the signed binary for your system from
https://github.com/opengrep/opengrep/releases, and either put it on your PATH as
`opengrep`, or set `HEALTHKIT_OPENGREP` to its full path. The other tools (ruff,
import-linter, Schemathesis) are fetched automatically, at fixed versions.

## Commands

Run them from inside the project's git repository.

| Command | What it does |
|---|---|
| `healthkit review --base main` | Checks only the lines your branch changed since `main`. Use before you push. |
| `healthkit scan users/` | Checks **every** line of the Python files in a folder. Use to check one module. |
| `healthkit baseline users/` | Remembers today's findings in a folder, so later runs show only **new** ones. |
| `healthkit api --schema <url>` | Sends good and bad input to every API route; any server error (500) is a finding. Local servers only. |
| `healthkit routes --schema <url> --callers <folder>` | Lists API routes that no client code calls. |

### What the results mean

- `path:line: [tool rule] message`: a problem. Fix it, or explain it (see "Exceptions").
- `worth a look: ...`: a hint, about half of these are real. It never fails the run.
- `needs human approval: ...`: someone changed healthkit's settings or switched a check off
  in the code (`# noqa`, `# nosemgrep`). A person must agree.
- `baselined: N`: N old problems were hidden because they are in the baseline.

Exit codes: **0** nothing found, **1** problems found, **2** could not check (never treat
this as a pass), **3** only a settings change that needs a person's approval.

## The project's `.healthkit/` folder

Everything specific to one project lives in its own `.healthkit/` folder, never in healthkit:

- `config.toml`:
  - `exclude = ["generated/**"]`: paths never checked.
  - `[[allow]]` with `rule`, `path` and a written `reason`: an accepted exception.
  - `[[check]]` with `name`, `command` (a list), `paths`, `reason`: the project's own
    guard commands, run by `review` before push. They are taken from the base branch, so a
    branch cannot add a command that runs on your machine.
  - `[django] soft_delete_fields = ["is_deleted"]`: the field that marks deleted rows.
  - `[ruff] extra = ["D1", "ANN", "PLR2004"]`: more ruff checks your team wants, such as
    docstrings (`D1`), type hints (`ANN`) or bare numbers (`PLR2004`). Off unless you add
    them: on most projects they fire thousands of times, so add a baseline when you do.

  - `[spelling] ignore = ["liscense"]`: words to accept, such as a misspelt name you cannot
    change (a database field).

Every project also gets two kinds of "worth a look" hints:
- functions that are too complex (ruff `C901`, more than 10 branches); an edit anywhere
  inside such a function shows it;
- spelling: clear-cut typos in messages, comments and names (codespell);
- options nobody sets: a function option with a default that no call in the project ever
  passes, so its other value is dead code. If your project has code called from outside
  the repo (an SDK, a plugin API), add `[[allow]]` with rule `option-never-passed` for it.
- `rules/*.yaml`: the project's own Opengrep rules.
- `importlinter.ini`: which layers may import which.
- `baseline.json`: written by `healthkit baseline`.
- `misses.md`: the miss log (below).

Any change in this folder shows as "needs human approval" in `review`.

## The miss log

When a person or an AI review finds a problem healthkit did not report, add one line to
`.healthkit/misses.md`:

```
| 2026-10-28 | users/api/users.py:410 | old refresh token still works after password change | behaviour |
```

Kinds: `pattern` (visible in the shape of the code), `structure` (who imports whom),
`knowledge` (needs to know the project), `behaviour` (does it do the right thing),
`judgement` (naming, placement, wording). The misses decide what healthkit learns next.

## Instructions for an AI assistant

When asked to check a module with healthkit:

1. Run `healthkit scan <folder>`. Read the whole output, including the summary line.
2. If the exit code is **2**, stop and report what could not run. Never report a pass.
3. Group the findings by rule; say how many of each, then list the ones that matter most.
   `worth a look` findings are hints: read the code before calling one real.
4. Then review the module yourself for what healthkit cannot judge: logic, security,
   design, naming, missing tests. That is where your review adds value.
5. For every problem you find that healthkit did not, propose one line for
   `.healthkit/misses.md`.

Never:
- edit anything in `.healthkit/` to make a finding go away;
- add `# noqa` or `# nosemgrep` to silence a finding;
- write or refresh a baseline unless the person asks for it;
- run `healthkit api` against anything but a local test server.

## For people working on healthkit itself

Read `CLAUDE.md` (how we build), `DECISIONS.md` (what we decided), `LEARNINGS.md` (what
went wrong and what changed), and `slices/` (each piece of work: spec, results).
