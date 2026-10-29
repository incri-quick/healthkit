"""Options nobody sets (slice 015): a parameter with a default no call ever passes."""

import pytest

from healthkit import cli
from healthkit.findings import ToolError
from healthkit.tools import options

# QuickRPA users/services/login.py:138 at beb9780^ (Susheel #23, AA-09), trimmed.
LOGIN = """\
def complete_login(request, response, user, *, mint, build_body, enforce_mfa=True):
    if enforce_mfa:
        return "challenge"
    return "session"
"""
CALLERS = """\
from login import complete_login


def obtain_token(request, response, user):
    return complete_login(request, response, user, mint=1, build_body=2)


def oidc(request, response, user):
    return complete_login(request, response, user, mint=3, build_body=4)
"""


def findings(repo, files: dict[str, str], changed: list[str]) -> list[str]:
    for path, text in files.items():
        repo.write(path, text)
    return [f"{f.path}:{f.line} {f.message}" for f in options.run(repo.root, changed)]


def test_a_switch_no_caller_passes_is_named(repo):
    out = findings(repo, {"login.py": LOGIN, "views.py": CALLERS}, ["login.py"])

    never = "option `enforce_mfa` of complete_login() is never passed by any of its 2 call(s)"
    assert out == [f"login.py:1 {never}; it is always True"]


def test_passing_it_by_keyword_or_by_position_counts(repo):
    call = "complete_login(r, s, u, mint=1, build_body=2, enforce_mfa=False)"
    by_keyword = CALLERS + f"\n\ndef admin(r, s, u):\n    {call}\n"
    positional = "def f(a, b=1):\n    return a + b\n\n\nx = f(1, 2)\n"

    assert findings(repo, {"login.py": LOGIN, "views.py": by_keyword}, ["login.py"]) == []
    assert findings(repo, {"pos.py": positional}, ["pos.py"]) == []
    short = "def g(a, b=1):\n    return a + b\n\n\ny = g(1)\n"  # b's position is never reached
    assert [f.split(" option")[0] for f in findings(repo, {"g.py": short}, ["g.py"])] == ["g.py:1"]


def test_star_callers_and_never_called_functions_are_skipped(repo):
    star = CALLERS + "\n\ndef admin(r, s, u, **extra):\n    complete_login(r, s, u, **extra)\n"
    route = "def list_items(request, page=1):\n    return page\n"

    assert findings(repo, {"login.py": LOGIN, "views.py": star}, ["login.py"]) == []
    assert findings(repo, {"routes.py": route}, ["routes.py"]) == []


def test_tests_are_callers_and_are_not_checked(repo):
    in_test = (
        "def test_no_mfa():\n    complete_login(1, 2, 3, mint=1, build_body=2, enforce_mfa=False)\n"
    )
    files = {"login.py": LOGIN, "views.py": CALLERS, "tests/test_login.py": in_test}

    assert findings(repo, files, ["login.py"]) == []
    test_helper = "def helper(x, verbose=False):\n    return x\n\n\ny = helper(1)\n"
    assert findings(repo, {"tests/test_h.py": test_helper}, ["tests/test_h.py"]) == []


def test_a_signature_edit_shows_it_and_a_body_edit_does_not(repo, capsys):
    repo.write("views.py", CALLERS)
    repo.write("login.py", LOGIN.replace(", enforce_mfa=True", ""))
    base = repo.commit("base")
    repo.write("login.py", LOGIN)  # the switch is added: the signature changed
    repo.commit()

    assert cli.main(["review", "--base", base]) == 0
    assert "worth a look: login.py:1: [options option-never-passed]" in capsys.readouterr().out

    base = repo.git("rev-parse", "HEAD")
    repo.write("login.py", LOGIN.replace('return "session"', 'return "session!"'))
    repo.commit()

    cli.main(["review", "--base", base])
    assert "option-never-passed" not in capsys.readouterr().out


def test_an_unparsable_file_is_never_a_pass(repo):
    repo.write("broken.py", "def f(x=1:\n")

    with pytest.raises(ToolError, match=r"broken\.py"):
        options.run(repo.root, ["broken.py"])
