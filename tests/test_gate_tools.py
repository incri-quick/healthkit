"""Opengrep and import-linter in `healthkit review`, on real QuickRPA incidents.

Needs the Opengrep binary: on PATH as `opengrep`, or HEALTHKIT_OPENGREP=<path>.
Without it these tests fail (by design, decision 1), they are not skipped.
"""

import subprocess
import sys
from pathlib import Path

import pytest

from healthkit import cli
from healthkit.tools import opengrep

FIXTURES = Path(__file__).parent / "fixtures"
RULES = Path(__file__).parents[1] / "src" / "healthkit" / "rules"

CONTRACT = """\
[importlinter]
root_packages =
    users

[importlinter:contract:api-above-services]
name = Routes may import services; services may not import routes
type = layers
containers =
    users
layers =
    api
    services
"""


def review(base: str) -> int:
    return cli.main(["review", "--base", base])


def users_package(repo, login_body: str) -> None:
    for init in ("users", "users/api", "users/services"):
        repo.write(f"{init}/__init__.py", "")
    repo.write("users/api/users.py", "def _set_auth_cookies(response):\n    return response\n")
    repo.write("users/services/login.py", login_body)
    repo.write(".healthkit/importlinter.ini", CONTRACT)


LOGIN_OK = "def complete_login(response):\n    return response\n"
# QuickRPA users/services/login.py before 4301ca4 (AA-06): reached up into the route file.
LOGIN_REACHES_UP = """\
def complete_login(response):
    from users.api.users import _set_auth_cookies
    return _set_auth_cookies(response)
"""


def test_the_builtin_rules_pass_their_own_tests():
    result = subprocess.run(
        [*opengrep.find_binary(), "test", str(RULES)], capture_output=True, text=True, check=False
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_exception_text_sent_to_the_caller_is_reported(repo, capsys):
    # QuickRPA users/services/password_reset.py:224 at 220f7b3 (AA-15).
    repo.write("users/services/password_reset.py", "def validate(p):\n    return p\n")
    base = repo.commit("base")
    repo.write(
        "users/services/password_reset.py",
        "def validate(p):\n"
        "    try:\n"
        "        checkpassword(p)\n"
        "    except Exception as exc:\n"
        "        raise PasswordResetError(400, str(exc))\n",
    )
    repo.commit()

    assert review(base) == 1
    out = capsys.readouterr().out
    assert "users/services/password_reset.py:5: [opengrep exception-text-in-reply]" in out


def test_every_rule_fixture_has_its_rule():
    # Found in slice 011: `opengrep test` passes a fixture file that has no rule beside it,
    # so a missing or misnamed rule would never fail the test above.
    fixtures = {p.stem for p in RULES.glob("*.py")}
    rules = {p.stem for p in RULES.glob("*.yaml")}
    assert fixtures == rules


def test_a_racy_cache_counter_is_reported(repo, capsys):
    # QuickRPA users/services/password_reset.py:49 at 4cf0801^ (AA-03).
    repo.write("users/services/password_reset.py", "def check(request):\n    return request\n")
    base = repo.commit("base")
    repo.write(
        "users/services/password_reset.py",
        "def check(request, limit=5, window=3600):\n"
        '    cache_key = f"rl:pw_reset:{request}"\n'
        "    count = cache.get(cache_key, 0)\n"
        "    if count >= limit:\n"
        "        raise ValueError(429)\n"
        "    cache.set(cache_key, count + 1, timeout=window)\n",
    )
    repo.commit()

    assert review(base) == 1
    assert "password_reset.py:6: [opengrep cache-read-modify-write]" in capsys.readouterr().out


def test_a_raw_json_body_read_is_reported(repo, capsys):
    # QuickRPA users/api/users.py:230 at 220f7b3 (AA-65).
    repo.write("users/api/users.py", "def obtain_token(request):\n    return request\n")
    base = repo.commit("base")
    repo.write(
        "users/api/users.py",
        "def obtain_token(request):\n"
        "    data = json.loads(request.body) if request.body else {}\n"
        "    return data\n",
    )
    repo.commit()

    assert review(base) == 1
    assert "users/api/users.py:2: [opengrep raw-json-body]" in capsys.readouterr().out


def test_a_service_reaching_up_into_a_route_file_is_reported(repo, capsys):
    users_package(repo, LOGIN_OK)
    base = repo.commit("base")
    users_package(repo, LOGIN_REACHES_UP)
    repo.commit()

    assert review(base) == 1
    out = capsys.readouterr().out
    assert "users/services/login.py:2: [import-linter api-above-services]" in out
    assert "ran: ruff, opengrep, import-linter" in out


def test_a_broken_link_on_an_unchanged_line_is_not_reported(repo, capsys):
    users_package(repo, LOGIN_REACHES_UP)
    base = repo.commit("base already breaks the contract")
    repo.write("users/services/login.py", LOGIN_REACHES_UP + "\n\nVERSION = 2\n")
    repo.commit()

    assert review(base) == 0
    assert "import-linter api-above-services" not in capsys.readouterr().out


def test_a_package_init_that_reaches_up_is_reported_at_its_init(repo, capsys):
    users_package(repo, LOGIN_OK)
    base = repo.commit("base")
    repo.write("users/services/__init__.py", "from users.api.users import _set_auth_cookies\n")
    repo.commit()

    assert review(base) == 1
    out = capsys.readouterr().out
    assert "users/services/__init__.py:1: [import-linter api-above-services]" in out


def test_without_a_contract_import_linter_is_skipped_and_says_so(repo, capsys):
    repo.write("a.py", "x = 1\n")
    base = repo.commit("base")
    repo.write("a.py", "x = 2\n")
    repo.commit()

    assert review(base) == 0
    assert "skipped: import-linter (no .healthkit/importlinter.ini)" in capsys.readouterr().out


def test_an_import_linter_config_error_fails_the_review(repo, capsys):
    users_package(repo, LOGIN_OK)
    repo.write(".healthkit/importlinter.ini", "[importlinter]\nroot_packages =\n    nosuchpkg\n")
    base = repo.commit("base")
    repo.write("users/services/login.py", LOGIN_OK + "\nVERSION = 2\n")
    repo.commit()

    assert review(base) == 2
    assert "import-linter" in capsys.readouterr().err


def _fake_opengrep(script: str) -> list[str]:
    return [sys.executable, "-c", script]


@pytest.mark.parametrize(
    ("fake", "expected"),
    [
        (None, "Opengrep not found"),
        (_fake_opengrep("print('not json')"), "unreadable output"),
        (
            _fake_opengrep(
                f"print(open(r'{FIXTURES / 'opengrep-error.json'}', encoding='utf-8').read())"
            ),
            "Timeout",
        ),
    ],
)
def test_an_opengrep_run_that_did_not_complete_fails_the_review(
    repo, capsys, monkeypatch, fake, expected
):
    if fake is None:
        monkeypatch.setenv("HEALTHKIT_OPENGREP", "")
        monkeypatch.setattr(opengrep.shutil, "which", lambda _name: None)
    else:
        monkeypatch.setattr(opengrep, "find_binary", lambda: fake)
    repo.write("a.py", "x = 1\n")
    base = repo.commit("base")
    repo.write("a.py", "x = 1\nimport os\n")
    repo.commit()

    assert review(base) == 2
    captured = capsys.readouterr()
    assert expected in captured.err
    assert "a.py:2: [ruff F401]" in captured.out  # the tools that did run still report
