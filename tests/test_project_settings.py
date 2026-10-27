"""Project settings end to end: exclusions, allow entries, project rules, and the
human-approval flag on `.healthkit/` changes (slice 004, D-018)."""

from healthkit import cli

# QuickRPA users/migrations/0037_permission_override_nulls_not_distinct.py:30 (dev 7fadfe3).
MIGRATION = """\
def forwards(apps, schema_editor):
    Override = apps.get_model("users", "UserPermissionOverride")
    return Override
"""
# QuickRPA commons/payload.py:54: the one shared reader the raw-json-body rule points to.
SHARED_READER = """\
import json


def read_json_object(request):
    data = json.loads(request.body) if request.body else {}
    return data
"""
ALLOW_READER = """\
[[allow]]
rule = "raw-json-body"
path = "commons/payload.py"
reason = "This is the one shared JSON body reader the rule points everyone to."
"""
# QuickRPA: _get_workspace_or_404 exists in 9 route files in 3 drifted versions (D-015).
WORKSPACE_RULE = """\
rules:
  - id: no-local-workspace-lookup
    languages: [python]
    severity: WARNING
    message: A local copy of the workspace access check. Use the shared one.
    pattern: |
      def _get_workspace_or_404(...):
          ...
"""
LOCAL_COPY = """\
def _get_workspace_or_404(workspace_id: int, user):
    permitted = [ws.id for ws in user.get_permitted_workspaces()]
    return get_object_or_404(WorkSpace, id=workspace_id, id__in=permitted)
"""


def review(base):
    return cli.main(["review", "--base", base])


def test_migrations_are_excluded_by_default(repo, capsys):
    repo.write("users/migrations/0037_nulls.py", "x = 1\n")
    base = repo.commit("base")
    repo.write("users/migrations/0037_nulls.py", MIGRATION)
    repo.commit()

    assert review(base) == 0
    out = capsys.readouterr().out
    assert "N806" not in out
    assert "excluded: 1 file(s)" in out


def test_real_code_in_a_migrations_folder_is_still_reviewed(repo, capsys):
    # QuickRPA users/migrations/_inert_permissions.py: 99 lines of real code, imported by
    # tests, hidden by the old "everything under migrations/" default (slice 005).
    repo.write("users/migrations/_inert_permissions.py", "x = 1\n")
    base = repo.commit("base")
    repo.write("users/migrations/_inert_permissions.py", "x = 1\nimport os\n")
    repo.commit()

    assert review(base) == 1
    assert "users/migrations/_inert_permissions.py:2: [ruff F401]" in capsys.readouterr().out


def test_an_allowed_finding_is_counted_not_printed(repo, capsys):
    repo.write(".healthkit/config.toml", ALLOW_READER)
    repo.write("commons/payload.py", "x = 1\n")
    base = repo.commit("base")
    repo.write("commons/payload.py", SHARED_READER)
    repo.commit()

    assert review(base) == 0
    out = capsys.readouterr().out
    assert "raw-json-body" not in out.splitlines()[0]
    assert "allowed: 1" in out
    assert "no known problems on changed lines" in out


def test_an_allow_entry_does_not_hide_another_rule_in_the_same_file(repo, capsys):
    repo.write(".healthkit/config.toml", ALLOW_READER)
    repo.write("commons/payload.py", "x = 1\n")
    base = repo.commit("base")
    repo.write("commons/payload.py", SHARED_READER + "import os\n")
    repo.commit()

    assert review(base) == 1
    out = capsys.readouterr().out
    assert "commons/payload.py:7: [ruff F401]" in out
    assert "allowed: 1" in out  # the raw-json-body on line 5 is still allowed


def test_an_allow_entry_does_not_hide_the_same_rule_in_another_file(repo, capsys):
    # Real case: QuickRPA studio_agent/api/agent_api.py:435 still parses the body itself.
    repo.write(".healthkit/config.toml", ALLOW_READER)
    repo.write("studio_agent/api/agent_api.py", "x = 1\n")
    base = repo.commit("base")
    repo.write(
        "studio_agent/api/agent_api.py",
        "import json\n\n\ndef runs(request):\n"
        "    body = json.loads(request.body) if request.body else {}\n"
        "    return body\n",
    )
    repo.commit()

    assert review(base) == 1
    assert "studio_agent/api/agent_api.py:5: [opengrep raw-json-body]" in capsys.readouterr().out


def test_a_project_rule_catches_a_new_local_copy(repo, capsys):
    repo.write(".healthkit/rules/no-local-workspace-lookup.yaml", WORKSPACE_RULE)
    repo.write("reports/api.py", "x = 1\n")
    base = repo.commit("base")
    repo.write("reports/api.py", LOCAL_COPY)
    repo.commit()

    assert review(base) == 1
    assert "reports/api.py:1: [opengrep no-local-workspace-lookup]" in capsys.readouterr().out


def test_a_broken_project_rule_fails_the_review(repo, capsys):
    repo.write(".healthkit/rules/broken.yaml", "rules:\n  - id: broken\n    pattern: [\n")
    repo.write("a.py", "x = 1\n")
    base = repo.commit("base")
    repo.write("a.py", "x = 2\n")
    repo.commit()

    assert review(base) == 2
    assert "opengrep" in capsys.readouterr().err


def test_changing_the_referee_needs_a_human(repo, capsys):
    # An agent "fixing" a finding by allowing it (D-018).
    repo.write("commons/payload.py", SHARED_READER)
    base = repo.commit("base")
    repo.write(".healthkit/config.toml", ALLOW_READER)
    repo.commit()

    assert review(base) == 3
    assert "needs human approval: .healthkit/config.toml" in capsys.readouterr().out


def test_deleting_a_project_rule_needs_a_human(repo, capsys):
    repo.write(".healthkit/rules/no-local-workspace-lookup.yaml", WORKSPACE_RULE)
    repo.write("a.py", "x = 1\n")
    base = repo.commit("base")
    repo.git("rm", "-q", ".healthkit/rules/no-local-workspace-lookup.yaml")
    repo.commit()

    assert review(base) == 3
    out = capsys.readouterr().out
    assert "needs human approval: .healthkit/rules/no-local-workspace-lookup.yaml" in out


def test_a_differently_cased_healthkit_folder_still_needs_a_human(repo, capsys):
    # Found by the slice 004 verifier, confirmed by hand: on Windows `.Healthkit/` is
    # loaded as the config folder, but the approval check asked git for `.healthkit`.
    repo.write("c.py", "import json\n\n\ndef f(request):\n    return request\n")
    base = repo.commit("base")
    repo.write(
        ".Healthkit/config.toml",
        '[[allow]]\nrule = "raw-json-body"\npath = "**"\nreason = "agent"\n',
    )
    repo.write("c.py", "import json\n\n\ndef f(request):\n    return json.loads(request.body)\n")
    repo.commit()

    code = review(base)

    assert "needs human approval: .Healthkit/config.toml" in capsys.readouterr().out
    assert code != 0


def test_findings_outrank_the_approval_flag(repo, capsys):
    repo.write("a.py", "x = 1\n")
    base = repo.commit("base")
    repo.write(".healthkit/config.toml", 'exclude = ["build/**"]\n')
    repo.write("a.py", "x = 1\nimport os\n")
    repo.commit()

    assert review(base) == 1
    assert "needs human approval: .healthkit/config.toml" in capsys.readouterr().out


def test_a_bad_config_fails_the_review(repo, capsys):
    repo.write(".healthkit/config.toml", 'exlude = ["build/**"]\n')
    repo.write("a.py", "x = 1\n")
    base = repo.commit("base")
    repo.write("a.py", "x = 2\n")
    repo.commit()

    assert review(base) == 2
    assert "exlude" in capsys.readouterr().err


def test_a_whole_project_tool_finding_in_an_excluded_file_is_dropped(repo, capsys):
    # import-linter scans the whole project, not just the files healthkit passes it.
    contract = (
        "[importlinter]\nroot_packages =\n    users\n\n"
        "[importlinter:contract:api-above-services]\nname = api above services\n"
        "type = layers\ncontainers =\n    users\nlayers =\n    api\n    services\n"
    )
    for init in ("users", "users/api", "users/services"):
        repo.write(f"{init}/__init__.py", "")
    repo.write("users/api/users.py", "def helper():\n    return 1\n")
    repo.write("users/services/legacy.py", "def old():\n    return 1\n")
    repo.write(".healthkit/importlinter.ini", contract)
    repo.write(".healthkit/config.toml", 'exclude = ["users/services/legacy.py"]\n')
    base = repo.commit("base")
    repo.write(
        "users/services/legacy.py",
        "def old():\n    from users.api.users import helper\n    return helper()\n",
    )
    repo.write("users/api/users.py", "def helper():\n    return 2\n")  # so the tools do run
    repo.commit()

    assert review(base) == 0
    out = capsys.readouterr().out
    assert "legacy.py" not in out
    assert "excluded: 1 file(s)" in out
    assert "ran: ruff, opengrep, import-linter" in out


def test_excluding_every_changed_file_is_still_visible(repo, capsys):
    repo.write(".healthkit/config.toml", 'exclude = ["**"]\n')
    repo.write("a.py", "x = 1\n")
    base = repo.commit("base")
    repo.write("a.py", "x = 1\nimport os\n")
    repo.commit()

    assert review(base) == 0
    out = capsys.readouterr().out
    assert "nothing to review" in out
    assert "excluded: 1 file(s)" in out
