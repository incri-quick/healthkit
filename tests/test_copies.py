"""`copy-same-name` (slice 011): a private helper a branch adds or changes that is also
defined in other modules. The only check that found D-015's drifted copies. Fixtures are
real QuickRPA copies of `_get_workspace_or_404` (dev 7fadfe3)."""

import pytest

from healthkit import cli
from healthkit.findings import ToolError
from healthkit.tools import copies

# organization/api/audit.py:122 (6 files hold this exact copy)
COMMON = '''\
def _get_workspace_or_404(workspace_id: int, user):
    """Get workspace if user has access to it."""
    permitted_workspaces = [ws.id for ws in user.get_permitted_workspaces()]
    workspace = get_object_or_404(WorkSpace, id=workspace_id, id__in=permitted_workspaces)
    return workspace
'''
# studio_agent/api/agent.py:598 (trimmed): arguments swapped, a different access check
DRIFTED = '''\
def _get_workspace_or_404(user, workspace_id: int):
    """Validate workspace exists and user has access."""
    from organization.models import WorkSpace

    try:
        workspace = WorkSpace.objects.get(id=workspace_id)
    except WorkSpace.DoesNotExist:
        raise HttpError(404, "Workspace not found")
    return workspace
'''


def findings(repo, files: dict[str, str], changed: list[str]) -> list[str]:
    for path, text in files.items():
        repo.write(path, text)
    return [f"{f.path}:{f.line}-{f.end_line} {f.message}" for f in copies.run(repo.root, changed)]


def test_a_helper_defined_in_other_modules_is_named_with_its_versions(repo):
    files = {
        "reports/api.py": COMMON,
        "agent/api/agent.py": COMMON,
        "studio_agent/api/agent.py": DRIFTED,
        "logs/api.py": "x = 1\n\n\n" + COMMON,
    }

    assert findings(repo, files, ["logs/api.py"]) == [
        (
            "logs/api.py:4-8 _get_workspace_or_404 is also defined in 3 other file(s), "
            "2 different version(s): agent/api/agent.py, reports/api.py, studio_agent/api/agent.py"
        )
    ]


def test_only_private_module_level_functions_are_checked(repo):
    shared = "def get_items(x):\n    return x\n\n\ndef __getattr__(name):\n    return name\n"
    method = "class A:\n    def _helper(self):\n        return 1\n"
    files = {
        "a.py": shared + method,
        "b.py": shared + method + "\n\ndef _helper():\n    return 2\n",  # module level here
        "c.py": "def _alone():\n    return 1\n",
    }

    assert findings(repo, files, ["a.py", "c.py"]) == []


def test_copies_in_tests_and_excluded_paths_do_not_count(repo):
    repo.write(".healthkit/config.toml", 'exclude = ["vendor/**"]\n')
    files = {
        "app/api.py": COMMON,
        "app/tests/test_api.py": COMMON,
        "app/tests.py": COMMON,
        "vendor/lib.py": COMMON,
    }

    assert findings(repo, files, ["app/api.py"]) == []


def test_two_changed_copies_name_each_other(repo):
    files = {"a.py": COMMON, "b.py": COMMON}

    out = findings(repo, files, ["a.py", "b.py"])

    same = "_get_workspace_or_404 is also defined in 1 other file(s), 1 different version(s)"
    assert out == [f"a.py:1-5 {same}: b.py", f"b.py:1-5 {same}: a.py"]


def test_copies_that_differ_only_in_their_docstring_are_one_version(repo):
    # agent/api/agent.py and analytics/api.py hold the same body under other docstrings.
    other = COMMON.replace("Get workspace if user has access to it.", "Workspace, or 404.")
    files = {"a.py": COMMON, "b.py": other}

    assert findings(repo, files, ["a.py"])[0].endswith("1 different version(s): b.py")


def test_a_changed_file_that_does_not_parse_is_never_a_pass(repo):
    repo.write("a.py", "def _helper(:\n")

    with pytest.raises(ToolError, match=r"a\.py"):
        copies.run(repo.root, ["a.py"])


def test_an_edit_inside_the_body_is_enough_and_it_never_blocks(repo, capsys):
    # Copies drift through body edits, not by renaming: the finding covers the function.
    repo.write("reports/api.py", COMMON)
    repo.write("audit/api.py", COMMON)
    base = repo.commit("base")
    repo.write("audit/api.py", COMMON.replace("return workspace", "return workspace  # changed"))
    repo.commit()

    code = cli.main(["review", "--base", base])

    out = capsys.readouterr().out
    assert code == 0, out
    assert "worth a look: audit/api.py:1: [copies copy-same-name] _get_workspace_or_404" in out
