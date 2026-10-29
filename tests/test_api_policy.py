"""The access policy: "this user must be refused on these routes" (slice 021). From
another project's run: a teacher read all 400 students and a parent-only page, and the
cross-user check (ST402) could not see it, because no object was another user's."""

import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

from healthkit import cli, config

TENANT = Path(__file__).parent / "fixtures" / "tenant_api.py"


@pytest.fixture
def tenant_api(monkeypatch):
    monkeypatch.setenv("HK_TOKEN_A", "tok-a")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    process = subprocess.Popen(
        [sys.executable, str(TENANT), str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            urllib.request.urlopen(f"{url}/openapi.json", timeout=1)  # noqa: S310 - local
            break
        except OSError:
            time.sleep(0.1)
    yield url
    process.kill()


def deny(repo, user: str, *routes: str) -> None:
    listed = ", ".join(f'"{route}"' for route in routes)
    repo.write(
        ".healthkit/config.toml",
        f'[[api.deny]]\nuser = "{user}"\nroutes = [{listed}]\nreason = "admins only"\n',
    )


def api(url: str, report: Path) -> int:
    schema = ["--schema", f"{url}/openapi.json", "--max-examples", "10"]
    return cli.main(["api", *schema, "--token-env", "HK_TOKEN_A", "--report-dir", str(report)])


def test_a_route_that_refuses_the_user_passes(repo, tenant_api, capsys, tmp_path):
    deny(repo, "HK_TOKEN_A", "GET /report")  # user a gets 403

    code = api(tenant_api, tmp_path / "r")

    out = capsys.readouterr().out
    assert code == 0, out
    assert "must-refuse" not in out
    assert "access policy: 1 route(s) refused as required" in out


def test_a_route_that_answers_the_user_is_a_finding(repo, tenant_api, capsys, tmp_path):
    deny(repo, "HK_TOKEN_A", "GET /notes/{note_id}")  # user a reads any note: 200

    code = api(tenant_api, tmp_path / "r")

    out = capsys.readouterr().out
    assert code == 1, out
    finding = "GET /notes/{note_id}: [policy must-refuse] HK_TOKEN_A got 200"
    assert finding in out
    assert "admins only" in out  # the rule's reason


def test_a_wildcard_covers_every_matching_route(repo, tenant_api, capsys, tmp_path):
    deny(repo, "HK_TOKEN_A", "GET /notes/*")

    api(tenant_api, tmp_path / "r")

    out = capsys.readouterr().out
    assert "GET /notes/{note_id}: [policy must-refuse]" in out
    assert "GET /notes: [policy" not in out  # `*` needs a segment after /notes/


def test_a_pattern_matching_no_route_is_never_a_pass(repo, tenant_api, capsys, tmp_path):
    deny(repo, "HK_TOKEN_A", "GET /reprot")  # a typo

    assert api(tenant_api, tmp_path / "r") == 2
    assert "GET /reprot" in capsys.readouterr().err


def test_what_could_not_be_checked_is_listed(repo, tenant_api, capsys, tmp_path):
    repo.write(
        ".healthkit/config.toml",
        '[[api.deny]]\nuser = "HK_TOKEN_A"\nroutes = ["POST /notes", "GET /items/{item_id}"]\n'
        'reason = "admins only"\n'
        '[[api.deny]]\nuser = "HK_TEACHER"\nroutes = ["GET /report"]\nreason = "admins only"\n',
    )

    code = api(tenant_api, tmp_path / "r")

    out = capsys.readouterr().out
    assert code == 0, out
    assert "access policy not checked: 3" in out
    assert "  POST /notes as HK_TOKEN_A: reads only (add --allow-writes)" in out
    assert "  GET /items/{item_id} as HK_TOKEN_A: answered only 404" in out  # guessed ids
    assert "  GET /report as HK_TEACHER: not given with --token-env" in out


@pytest.mark.parametrize(
    "rule",
    [
        'user = "A"\nroutes = ["GET /x"]\n',  # no reason
        'user = "A"\nroutes = []\nreason = "r"\n',  # no routes
        'user = "A"\nroutes = ["/x"]\nreason = "r"\n',  # no method
        'user = "A"\nroutes = ["GET x"]\nreason = "r"\n',  # not a path
        'user = "A"\nroutes = ["GET /x"]\nreason = "r"\nrole = "t"\n',  # unknown key
        'routes = ["GET /x"]\nreason = "r"\n',  # no user
    ],
)
def test_a_malformed_rule_is_a_config_error(rule):
    with pytest.raises(config.ConfigError, match=r"api\.deny"):
        config.parse(f"[[api.deny]]\n{rule}")
