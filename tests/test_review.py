"""`healthkit review` end to end, on fixtures from real QuickRPA incidents."""

import pytest

from healthkit import cli
from healthkit.tools import ruff

# QuickRPA users/api/users.py at 220f7b3, line 247; renamed in ca5c64e (RUF052).
LOGIN_BEFORE = """\
def obtain_token(request, data):
    email = require_text(data, "email")
    return authenticate(request, username=email)
"""
LOGIN_AFTER = """\
def obtain_token(request, data):
    email = require_text(data, "email")
    _password = require_text(data, "password", strip=False)
    return authenticate(request, username=email, password=_password)
"""

# QuickRPA users/api/users.py at 220f7b3, line 1459; deleted as dead code in 198494c (F821).
DEAD_LOGIN = """\
def _get_validated_token(raw_token):
    for auth_token in api_settings.AUTH_TOKEN_CLASSES:
        return auth_token(raw_token)
"""


def review(base: str) -> int:
    return cli.main(["review", "--base", base])


def test_a_new_violation_on_a_changed_line_is_reported(repo, capsys):
    repo.write("users/api/users.py", LOGIN_BEFORE)
    base = repo.commit("base")
    repo.write("users/api/users.py", LOGIN_AFTER)
    repo.commit()

    code = review(base)

    out = capsys.readouterr().out
    assert code == 1
    assert "users/api/users.py:3: [ruff RUF052]" in out


def test_an_old_violation_on_an_untouched_line_is_not_reported(repo, capsys):
    repo.write("users/api/users.py", LOGIN_AFTER)
    base = repo.commit("base already has the violation")
    repo.write("users/api/users.py", LOGIN_AFTER + "\n\ndef logout():\n    return None\n")
    repo.commit()

    code = review(base)

    assert code == 0
    assert "RUF052" not in capsys.readouterr().out


def test_an_undefined_name_added_by_the_branch_is_reported(repo, capsys):
    repo.write("users/api/users.py", LOGIN_BEFORE)
    base = repo.commit("base")
    repo.write("users/api/users.py", LOGIN_BEFORE + "\n\n" + DEAD_LOGIN)
    repo.commit()

    code = review(base)

    out = capsys.readouterr().out
    assert code == 1
    assert "[ruff F821]" in out
    assert "api_settings" in out


def test_a_finding_ruff_reports_twice_is_shown_once(repo, capsys):
    # Real case: QuickRPA commons/tests/test_permission_utilisation.py:479 (dev 7fadfe3).
    # ruff 0.17.2 emits PLC2701 once per name in a multi-name private import.
    repo.write("users/migrations/_inert_permissions.py", "A = 1\nB = 2\n")
    repo.write("checks.py", "x = 1\n")
    base = repo.commit("base")
    repo.write(
        "checks.py",
        "x = 1\n"
        "from users.migrations._inert_permissions import (\n    A,\n    B,\n)\n"
        "print(A, B)\n",
    )
    repo.commit()

    review(base)

    out = capsys.readouterr().out
    assert out.count("checks.py:2: [ruff PLC2701]") == 1


def test_a_type_stub_file_is_reviewed_too(repo, capsys):
    # Found by the slice 002 verifier: a changed .pyi was skipped as "no Python files".
    repo.write("types.pyi", "def foo(): ...\n")
    base = repo.commit("base")
    repo.write("types.pyi", "import os\n")
    repo.commit()

    code = review(base)

    assert code == 1
    assert "types.pyi:1: [ruff F401]" in capsys.readouterr().out


def test_outside_a_git_repo_is_an_error(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    assert review("main") == 2
    assert "not a git repository" in capsys.readouterr().err


def test_an_unknown_base_is_an_error(repo, capsys):
    repo.write("a.py", "x = 1\n")
    repo.commit()

    assert review("no-such-branch") == 2
    assert "no-such-branch" in capsys.readouterr().err


def test_no_changed_python_files_is_a_pass(repo, capsys):
    repo.write("a.py", "x = 1\n")
    base = repo.commit()
    repo.write("notes.md", "hello\n")
    repo.commit()

    assert review(base) == 0
    assert "nothing to review" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        (["no-such-tool-healthkit-test"], "could not run ruff"),
        (["python", "-c", "print('not json')"], "unreadable output"),
        (["python", "-c", "import sys; sys.exit(2)"], "ruff failed"),
    ],
)
def test_a_ruff_run_that_did_not_happen_is_never_a_pass(
    repo,
    capsys,
    monkeypatch,
    command,
    expected,
):
    monkeypatch.setattr(ruff, "COMMAND", command)
    repo.write("a.py", "x = 1\n")
    base = repo.commit()
    repo.write("a.py", "x = 1\ny = 2\n")
    repo.commit()

    assert review(base) == 2
    assert expected in capsys.readouterr().err


def test_awkward_files_spaces_crlf_bom_rename_delete_binary(repo, capsys):
    repo.write("Bot Starter Kit/app/bot.py", "x = 1\r\n")
    repo.write("old_name.py", "y = 2\n")
    repo.write("gone.py", "z = 3\n")
    base = repo.commit("base")
    repo.write("Bot Starter Kit/app/bot.py", "x = 1\r\nimport os\r\n")  # F401 on line 2
    repo.git("mv", "old_name.py", "new_name.py")
    repo.write("bom.py", "﻿import sys\n")  # F401 in a file with a byte-order mark
    repo.git("rm", "-q", "gone.py")
    repo.write("logo.png", "\x89PNG\x00\x01binary")
    repo.commit()

    code = review(base)

    out = capsys.readouterr().out
    assert code == 1
    assert "Bot Starter Kit/app/bot.py:2: [ruff F401]" in out
    assert "bom.py:1: [ruff F401]" in out
    assert "new_name.py" not in out  # a pure rename changes no lines
    assert "gone.py" not in out
