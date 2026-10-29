# Slice 008 results: project checks + the Django pack's first rule

## What exists

- **Project checks (core):** `[[check]]` in `.healthkit/config.toml` (name, argument-list
  command, paths, reason, optional timeout). `healthkit review` runs each check when the
  branch changed a matching file. A failure is one finding with the last 5 lines printed
  and the full output in a report file; a check that cannot start or times out is exit 2.
  **Commands are read from the base branch** (`git show <base>:.healthkit/config.toml`):
  a branch that adds or edits a check gets "needs human approval" and its command does not
  run.
- **Django pack, `soft-delete-read` (advisory):** finds every model with a deletion flag
  by reading the project's code (no model list, nothing imported or run), and shows reads
  of those models that never name the flag. Shown as "worth a look", **never fails the
  gate** (D-023). `[django] soft_delete_fields` changes the flag name.

## The search that changed the plan (CLAUDE.md rule 1)

QuickRPA already guards three of the four rules D-021 planned (unscoped permission checks,
token reads outside their door, password writes that skip the stamp) with its own build
guards, which only run when someone runs the test suite. So the slice runs a project's own
guards instead of copying them, and writes only the unguarded rule, generically (D-022).

## `soft-delete-read`: how the number moved, and why it ships advisory

| Step | Data | Findings | Precision (hand-read) |
|---|---|---|---|
| First version | QuickRPA, every 5th of 99 | 99 | **25%** (5 real / 20) |
| Generic fixes from that read: skip test files; a field the delete method sets False counts as the flag (`RobotVersion.soft_delete()` clears `is_active`); skip `values`/`values_list` projections; skip `management/commands/` | | 31 | |
| **Held-out**: every QuickRPA finding not read before | QuickRPA | 22 | **41%** (9 real, 9 fine, 4 debatable; 59% if debatable count) |
| Second project, fresh | gtech-mulearn/mulearnbackend | 47 | **55%** (11 / 20; 60%) |
| Third project, fresh | mitodl/micromasters | 1 | 0 / 1 |

About half of what it shows on code it was never tuned on is a real bug: under the 70% a
blocking rule needs (spec acceptance). So it is shown, not enforced.

**The second project found a gap the first never could:** mulearnbackend keeps its models
in `db/*.py`, and the rule (looking only in `models.py`) found none of them. Discovery now
reads any file with a class based on a model, manager or queryset; 3 s on QuickRPA.
mulearnbackend's own code documents this exact bug class
(`api/dashboard/task/dash_task_view.py`: "filtering on active alone lets a deleted task
keep appearing here").

### Real bugs it found in QuickRPA today (dev 7fadfe3)

Run on the local stack (throwaway rows, removed after):

| Read | Result |
|---|---|
| `studio_robot/api/robots.py:123` `list_robots` | **Confirmed by running:** an archived robot is returned by `GET /api/v1/robots/` (same class as incident `e938910`, another route) |
| `studio_media/api/media.py:519` `download_file` (and `:529` preview) | **Lookup confirmed:** a deleted media row passed the lookup and reached the storage step; the file itself was not served only because local storage holds no media files |

Judged by reading only (opinions until run, L-010): agent can create a run for, or download
the file of, an archived robot (`agent/api/agent.py:389, 475, 494`,
`studio_agent/api/agent_api.py:384`); archived robot detail and re-archive
(`organization/api/organization.py:3091, 3210`); a bot can patch a deleted bucket file
(`storage_buckets/api/storage_buckets.py:454`); a workflow can start a run of an archived
robot (`studio_workflow/execution/robot_call.py:129`); a run pinned to a deleted version
still runs it (`studio_robot/tasks.py:377`); the robot-target picker offers archived robots
(`studio_workflow/api/workflow.py:2507`); media of a deleted version is served
(`studio_robot/api/robots.py:6978`).

### Known gaps (not fixed in this slice)

- **Reads through a relation**: `Vault.objects.get(robot__work_space=ws)` where the parent
  `Robot` is soft-deleted (`f0a3b4e`, `ac8a630` fixed these with `robot__is_deleted=False`).
  A different, harder shape.
- A query built over several statements (`qs = ...; qs = qs.filter(...)`) is read per
  statement.
- Two classes with the same name in different apps: the first one found is used.
- A model whose bases have no "Model" in their name, in a file with no other model class,
  is not found.

## Live run (QuickRPA throwaway clone, configured as a customer would)

Base branch `hk-base`: the team's `.healthkit/` with one `[[check]]` running the tenancy
and auth-source guards in a fresh container on the branch's code (`docker run --rm
--entrypoint python -v <clone>:/code ...`; 62 guard tests, about 26 s). Test branch
`hk-test`: `retrieve_robot`'s `assert_perm(..., workspace=robot.work_space)` loses its
scope, and one new `Robot.objects.get(id=robot_id)` is added.

```
worth a look: studio_robot/api/robots.py:7358: [django soft-delete-read] Robot rows can be soft-deleted (is_deleted); this read does not filter them out
.healthkit/config.toml:0: [check tenancy and auth guards] failed (exit 1); full output: C:\Users\legio\AppData\Local\Temp\healthkit-checks-s6mzdwm9\1.txt

    ----------------------------------------------------------------------
    Ran 62 tests in 20.778s

    FAILED (failures=1)
healthkit: 1 finding(s) in 1 changed file(s) and checks | ran: ruff, opengrep, import-linter, django, check tenancy and auth guards | worth a look: 1
exit=1
```

The report file names exactly the planted line, with QuickRPA's own fix instruction:
`studio_robot.api.robots.retrieve_robot (studio_robot/api/robots.py:157, assert_perm)`.

**Open:** the printed last 5 lines are unittest's summary, not the reason; the reason is in
the report. Printing the lines that name the failure (per tool) is a later improvement.

Tests: 109 pass. Mutants: **16 of 16 caught** (base-branch read, skip-when-untouched,
failing check, start error, timeout, inherited flag, filtering manager, writes and
projections, flag in the query, cleared field, test files, discovery outside `models.py`,
unreadable managers named, unparsable model file, advisory never blocking ×2).

## Deviations from the spec

1. `2993b3b` is not an incident (`FileArtifact` got its flag in that same commit); the
   three real incidents are `e938910`, `f0a3b4e`, `ac8a630`.
2. The spec said tests were "already excluded"; healthkit excludes only migrations. The
   rule now skips test files itself.
3. Models are found in any file, not by file name (second-project finding).
4. Below the 70% bar after narrowing on unseen data: shipped advisory instead of blocking
   (D-023).
5. **Over budget:** about 444 lines of source (122 changed in core files, `checks.py` 78,
   `tools/django.py` 244) against ~300 (D-016). The growth came from what measurement
   forced in mid-slice (discovery in any file, cleared fields, projections, advisory
   output); a split into two slices would have been the disciplined call.

## Process notes

- The first two runtime probes "refuted" real bugs: the sweep user could not see the
  workspace the probe robot was in, and the media owner had no Studio access. Both were
  bad setups, not results (L-019).
- Probe rows on the local stack were created, used and hard-deleted (a soft-delete would
  have let a retention sweep purge a file the probe shared with a live row).
