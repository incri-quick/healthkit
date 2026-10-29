"""API pack with real ids and more than one user (slice 016). Real Schemathesis against
tests/fixtures/tenant_api.py: a route reachable only with a real id, and a cross-user read."""

import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

from healthkit import cli
from healthkit.tools import schemathesis

TENANT = Path(__file__).parent / "fixtures" / "tenant_api.py"
# Every test runs in a throwaway repo (config is read from it) with both users' tokens set.
pytestmark = pytest.mark.usefixtures("repo", "users")


@pytest.fixture
def tenant_api():
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


@pytest.fixture
def users(monkeypatch):
    monkeypatch.setenv("HK_TOKEN_A", "tok-a")
    monkeypatch.setenv("HK_TOKEN_B", "tok-b")


def api(url: str, report: Path, *tokens: str) -> int:
    token_args = [arg for name in tokens for arg in ("--token-env", name)]
    schema = ["--schema", f"{url}/openapi.json"]
    return cli.main(
        ["api", *schema, *token_args, "--max-examples", "20", "--report-dir", str(report)]
    )


def test_a_real_id_from_the_project_reaches_the_route(repo, tenant_api, capsys, tmp_path):
    api(tenant_api, tmp_path / "without", "HK_TOKEN_A")
    assert "/items/{item_id}: [" not in capsys.readouterr().out  # guessed ids: all 404

    repo.write(".healthkit/config.toml", "[api.parameters]\nitem_id = 7\n")
    code = api(tenant_api, tmp_path / "with", "HK_TOKEN_A")

    assert code == 1
    assert "/items/{item_id}: [schemathesis ST101]" in capsys.readouterr().out


def test_a_value_can_come_from_the_environment(repo, tenant_api, capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("HK_ITEM", "7")
    repo.write(".healthkit/config.toml", '[api.parameters]\nitem_id = "${HK_ITEM}"\n')

    api(tenant_api, tmp_path, "HK_TOKEN_A")

    assert "/items/{item_id}: [schemathesis ST101]" in capsys.readouterr().out


def test_two_users_find_a_cross_user_read(tenant_api, capsys, tmp_path):
    code = api(tenant_api, tmp_path, "HK_TOKEN_A", "HK_TOKEN_B")

    out, err = capsys.readouterr()
    assert code == 1, out + err
    assert "GET /notes/{note_id}: [schemathesis ST402]" in out
    assert "users: 2" in out
    files = [p for p in tmp_path.rglob("*") if p.is_file()]
    assert not [p for p in files if p.name == schemathesis.AUTH_FILE]  # the token file is gone
    for report in files:
        text = report.read_text(encoding="utf-8", errors="replace")
        assert "tok-a" not in text
        assert "tok-b" not in text
    assert "tok-a" not in out + err


def test_a_route_the_project_accepts_is_not_reported(repo, tenant_api, capsys, tmp_path):
    # QuickRPA's GET /api/v1/agents/agent/{token}/status (slice 016 live run): the token in
    # the path IS the credential, so any holder may read it. A capability URL, by design.
    repo.write(
        ".healthkit/config.toml",
        '[[allow]]\nrule = "ST402"\npath = "GET /notes/{note_id}"\n'
        'reason = "capability URL: the id in the path is the credential"\n'
        '[[allow]]\nrule = "ST101"\npath = "GET /report"\n'
        'reason = "the second user crashes it (slice 019), not this test\'s subject"\n',
    )

    code = api(tenant_api, tmp_path, "HK_TOKEN_A", "HK_TOKEN_B")

    out = capsys.readouterr().out
    assert code == 0, out
    assert "ST402" not in out
    assert "allowed: 2" in out


def test_one_user_cannot_check_cross_user_reads(tenant_api, capsys, tmp_path):
    api(tenant_api, tmp_path, "HK_TOKEN_A")

    assert "ST402" not in capsys.readouterr().out


def test_an_unset_second_token_is_an_error(tenant_api, capsys, monkeypatch, tmp_path):
    monkeypatch.delenv("HK_TOKEN_B")

    assert api(tenant_api, tmp_path, "HK_TOKEN_A", "HK_TOKEN_B") == 2
    assert "HK_TOKEN_B" in capsys.readouterr().err


def test_malformed_parameters_are_a_config_error(repo, tenant_api, capsys, tmp_path):
    for bad in (
        "[api]\nparameters = [7]\n",
        "[api.parameters]\nitem_id = [7]\n",
        "[api]\nx = {}\n",
    ):
        repo.write(".healthkit/config.toml", bad)

        assert api(tenant_api, tmp_path, "HK_TOKEN_A") == 2, bad
        assert "api" in capsys.readouterr().err


def test_the_token_file_is_removed_when_the_run_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(schemathesis, "COMMAND", ["no-such-schemathesis-healthkit-test"])

    assert api("http://127.0.0.1:9", tmp_path, "HK_TOKEN_A", "HK_TOKEN_B") == 2
    assert not [p for p in tmp_path.rglob("*") if p.name == schemathesis.AUTH_FILE]
