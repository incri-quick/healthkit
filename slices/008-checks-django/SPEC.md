# Slice 008: project checks + the Django pack's first rule

Status: **approved** (2026-10-27), including decisions 1-4. Rewritten 2026-10-27 under D-022: the first draft
("QuickRPA knowledge pack", with a hard-coded list of QuickRPA's models) built for one
customer.

## What the search found first (CLAUDE.md rule 1)

D-021 step 2 listed four rules taken from QuickRPA's bugs. QuickRPA already enforces three
of them with its own build guards in `commons/tests/` (`test_tenancy_guard.py`,
`test_auth_source_guard.py`: unscoped permission checks, token reads outside their door,
password writes that skip the stamp). Mature projects often have checks like these. What
they lack is a guarantee that they run: QuickRPA's run only inside the test suite, which
nobody starts automatically while GitHub Actions is stopped.

The fourth, **reading soft-deleted rows as if they were live**, is guarded nowhere, and it
is not a QuickRPA idea: any Django project that marks rows deleted with a flag instead of
deleting them can make this mistake.

## Goal (both parts work on any project; nothing QuickRPA-specific ships)

1. **Project checks (core):** a project lists its own guard commands in
   `.healthkit/config.toml`; `healthkit review` runs them before push when the branch
   touches matching files. Any language, any command.
2. **Django pack, first rule `soft-delete-read`:** healthkit finds, by itself, every model
   that has a deletion flag, then flags a read of that model that does not filter on it.
   No model list is written by hand.

## Out of scope

Near-copy detection and unused routes (D-021 step 4). Other Django rules. Rewriting any
project's existing guards. QuickRPA's own config: it is written in the test-bed clone as a
customer would, never in this repo.

## Design

### A. Project checks (core, any project)

```toml
[[check]]
name = "build guards"
command = ["python", "manage.py", "test", "myapp.tests.test_guards"]
paths = ["**/*.py"]      # run only when the branch changes a matching file
reason = "our own guards; CI does not run them"
timeout = 300            # seconds, optional
```

- Exit 0 is a pass. Any other exit is **one finding** naming the check; its full output is
  saved to a report file and only the last lines are printed.
- The command cannot start, or exceeds its timeout → exit 2, never a pass.
- An argument list only, never a shell string.
- **Commands are read from the base branch's config** (`git show <base>:.healthkit/config.toml`),
  never from the branch under review. Otherwise a branch could add a command that runs on
  the reviewer's machine before anyone approves it: D-018 approves a change, it cannot undo
  a run. A branch that adds or edits a check gets "needs human approval" (exit 3) as today;
  the new check runs once merged.

### B. Django pack: `soft-delete-read`

**Switches on by detection** (D-005): the repo has Django model classes.

**Which models (found, not listed):** healthkit reads the repo's model classes (Python AST,
no Django import, no project code run) and keeps those that declare a deletion-flag field,
directly or through a base class defined in the repo. The field names default to
`is_deleted`; a project can change them:

```toml
[django]
soft_delete_fields = ["is_deleted"]
```

**Skipped models:** a model whose default manager already hides deleted rows. healthkit
reads the manager's `get_queryset`: if it filters on the flag, reads are safe and the model
is skipped. A manager from an outside package that healthkit cannot read (e.g.
`django-safedelete`) is also skipped, and the summary says which models were not checked,
never silently.

**Flagged:** on changed lines, `Model.objects.get(...)`, `Model.objects.filter(...)`,
`get_object_or_404(Model, ...)` for a kept model, when the flag appears nowhere in the
query chain.

**Not flagged:** the flag anywhere in the chain (`.filter(...).filter(is_deleted=False)`,
`Q(is_deleted=False)`, `is_deleted__in=...`); `**kwargs` passed in (unknowable);
writes (`.update(...)`, `.delete()`). Deliberate reads of deleted rows (a purge or a
restore) are allow entries with a written reason in the project's own config.

## Failure modes (each gets a test)

1. A check that fails → one finding, exit 1; output saved, not flooded to the screen.
2. A check that cannot start, or times out → exit 2.
3. A branch that adds a `[[check]]` → that command is **not** run; review needs approval (exit 3).
4. No changed file matches `paths` → check skipped; the summary says so.
5. A `[[check]]` without `reason`, or with a string command → config error (exit 2).
6. A model file that does not parse → exit 2, not "no soft-delete models".
7. Flag inherited from a repo base class → model kept; a manager that filters → model skipped.
8. Each "not flagged" shape stays quiet; a chain that never names the flag is flagged.

## Tests

- **Main fixture: a small made-up Django project** (models, an abstract base with the flag,
  one manager that filters, one that does not; no Django install needed, since healthkit
  only reads the code).
- **Evidence from real history** (QuickRPA, the test bed): four fixes that added a missing
  filter, each line checked at the fix's parent: `e938910` "Hide archived robots from
  workspace listings", `f0a3b4e`, `ac8a630`, `2993b3b`. Each parent line must be flagged,
  each fixed line not.
- Checks: a fixture command that exits 0, 1, never starts, and sleeps past its timeout.

## Acceptance

- Tests first, shown failing; green; mutants on green code (base-branch read, timeout,
  skip-when-untouched, inherited flag, manager that filters, chain exception).
- **Precision measured on two projects, not one (L-016):** QuickRPA (rough count today:
  74 unfiltered reads of 7 soft-delete models in 29 files; 20 read by hand) and one
  open-source Django project that uses a deletion flag, found during the build. If none
  is found within an hour, that is reported and the rule ships marked "measured on one
  project". Below 70% precision the rule is narrowed before it ships.
- A live review in the QuickRPA clone with its guards configured as a `[[check]]`: output
  pasted.
- Under ~300 lines of source (D-016).

## Honest expectation

The replay's knowledge score (0/13) does not move: QuickRPA's guards were written from
those incidents (counting them would be circular), and the other 8 need step 4. This slice
gives every project two things: its own checks run before every push, and one Django mistake
caught with no setup.

## Needs approval

1. **Run a project's own checks through `[[check]]`**; never copy them into healthkit.
2. **Checks are read from the base branch only.**
3. **`soft-delete-read` finds the models itself** (flag field, inheritance, manager), with
   `is_deleted` as the default field name; outside-package managers are skipped and named.
4. **Precision on two projects**, shipping at 70% or more.

## Lesson this slice teaches

Search before writing: the best rule may already exist in the project, and the missing
piece is making it run. And a rule found in one project ships only once it works without
that project's names in it.
