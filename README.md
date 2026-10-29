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
| `healthkit api --schema <url> --token-env TOKEN_A` | Sends good and bad input to every API route; any server error (500) is a finding. Reads only (GET) unless you add `--allow-writes`. Give `--token-env` once per user: each user is tested, and with two or more it also checks that one user cannot read another's objects. Local servers only. |
| `healthkit routes --schema <url> --callers <folder>` | Lists API routes that no client code calls. |
| `healthkit scorecard [folders]` | One row of facts per module, the ones needing attention first: files, lines, too-complex functions, the most complex one, problems and hints. |

### Output formats

`review` and `scan` take `--format`:

- `text` (default): for a person at a terminal.
- `json`: for an AI assistant or a script. One object: `exit`, `summary`, `details`,
  `findings` (each with `kind`: `problem`, `worth a look` or `check`), `approvals`.
- `markdown`: a pull-request comment. healthkit never posts anything; you do:
  `healthkit review --base main --format markdown > review.md` then
  `gh pr comment <number> -F review.md`.
- `github`: annotations that GitHub Actions shows inline on the pull request.

Exit codes are the same in every format. Machine formats are always UTF-8.

### What the results mean

- `path:line: [tool rule] message`: a problem. Fix it, or explain it (see "Exceptions").
- `worth a look: ...`: a hint, about half of these are real. It never fails the run.
- `needs human approval: ...`: someone changed healthkit's settings or switched a check off
  in the code (`# noqa`, `# nosemgrep`). A person must agree.
- `baselined: N`: N old problems were hidden because they are in the baseline.

Exit codes: **0** nothing found, **1** problems found, **2** could not check (never treat
this as a pass), **3** only a settings change that needs a person's approval.

### The API check

- **Reads only by default.** Only GET requests are sent, so no data changes. Add
  `--allow-writes` to also send POST, PUT, PATCH and DELETE: that run **creates, changes
  and deletes data** (it can deactivate users or reverse payments), so use spare test
  data and reset it afterwards.
- **Every user is tested.** Give one `--token-env` per role, for example an admin, a
  plain user and a user in another organisation. Findings name the user that hit them:
  `GET /report: [schemathesis ST101] Server error (as ADMIN_TOKEN)`.
- **Refused routes are listed per user.** A route that answered a user only with 401 or
  403 was not tested as that user; it is listed under `not tested (refused by login)`.
  With one user, most routes refused means the token did not work: exit 2. With several,
  only a token that works on nothing is exit 2, because a plain user is refused on every
  admin route by design.
- **The access policy** checks who must be refused where. healthkit cannot know your
  roles, so you write the rules in `.healthkit/config.toml`, one entry per user:

  ```toml
  [[api.deny]]
  user = "HK_TEACHER"   # the --token-env name
  routes = ["GET /people/students", "GET /finances/**"]   # * = one path part, ** = any
  reason = "a teacher sees only her own class"
  ```

  Any 2xx answer to that user on a matching route is a finding: `[policy must-refuse]`.
  A 401 or 403 is "refused as required". Anything else (only 404, only 422) is listed
  under `access policy not checked`, because a 404 can mean a guessed id as easily as a
  refusal. A route pattern that matches nothing tested is exit 2, so a typo never passes.
  It catches a route open to the wrong role, not a route that returns too many rows to
  the right role.
- **Shallow routes are listed per user**: routes with an id in the path that only got
  "not found", because no real id was known. Give real ids in `[api.parameters]`.
- Tokens are read from environment variables, never typed on the command line, and never
  written to the reports.
- The report folder (`--report-dir`, default a temp folder) ignores itself in git, so it
  is never committed by accident. It holds every request sent: delete it when done.

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

  - `[api.parameters]`: real values for the API check, such as ids that exist in your test
    data (`workflow_id = 12`, or `workflow_id = "${HK_WORKFLOW_ID}"` to read one from the
    environment). Without them most routes only answer "not found" to guessed ids.
  - `[[api.deny]]` with `user`, `routes` and `reason`: the access policy (see "The API
    check").
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

1. Run `healthkit scan <folder> --format json`. Read every finding and the summary.
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
- run `healthkit api` against anything but a local test server;
- add `--allow-writes` unless the person said the data may be changed.

## For people working on healthkit itself

Read `CLAUDE.md` (how we build), `DECISIONS.md` (what we decided), `LEARNINGS.md` (what
went wrong and what changed), and `slices/` (each piece of work: spec, results).
