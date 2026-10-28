"""Every user tested, and reads only unless asked (slice 019). From another project's run:
with two users only the first was fuzzed (82 admin-only operations never tested), and the
run deactivated a user and reversed a payment without warning."""

import json
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

from healthkit import cli
from healthkit.findings import ToolError
from healthkit.tools import schemathesis

TENANT = Path(__file__).parent / "fixtures" / "tenant_api.py"
pytestmark = pytest.mark.usefixtures("repo")


@pytest.fixture
def logged_api(tmp_path):
    """The two-user test API, writing each request's method to a log."""
    log = tmp_path / "methods.log"
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    process = subprocess.Popen(
        [sys.executable, str(TENANT), str(port), str(log)],
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
    yield url, log
    process.kill()


@pytest.fixture(autouse=True)
def tokens(monkeypatch):
    monkeypatch.setenv("HK_TOKEN_A", "tok-a")
    monkeypatch.setenv("HK_TOKEN_B", "tok-b")
    monkeypatch.setenv("HK_BROKEN", "not-a-token")


def api(url: str, report: Path, *args: str) -> int:
    schema = ["--schema", f"{url}/openapi.json", "--max-examples", "10"]
    return cli.main(["api", *schema, "--report-dir", str(report), *args])


def methods(log: Path) -> set[str]:
    return set(log.read_text(encoding="utf-8").split()) if log.exists() else set()


def test_by_default_only_reads_reach_the_server(logged_api, capsys, tmp_path):
    url, log = logged_api

    api(url, tmp_path / "r", "--token-env", "HK_TOKEN_A")

    assert methods(log) == {"GET"}
    assert "reads only" in capsys.readouterr().out


def test_writes_only_when_asked(logged_api, capsys, tmp_path):
    url, log = logged_api

    api(url, tmp_path / "r", "--token-env", "HK_TOKEN_A", "--allow-writes")

    assert "POST" in methods(log)
    assert "changed data" in capsys.readouterr().out


def test_every_user_is_tested_not_only_the_first(logged_api, capsys, tmp_path):
    # GET /report crashes only for user b, who comes second.
    url, _ = logged_api

    code = api(url, tmp_path / "r", "--token-env", "HK_TOKEN_A", "--token-env", "HK_TOKEN_B")

    out = capsys.readouterr().out
    assert code == 1, out
    report = next(line for line in out.splitlines() if line.startswith("GET /report:"))
    assert "[schemathesis ST101]" in report
    assert "HK_TOKEN_B" in report
    assert "HK_TOKEN_A" not in report
    assert "GET /notes/{note_id}: [schemathesis ST402]" in out  # cross-user still checked


def test_refused_routes_are_counted_per_user(logged_api, capsys, tmp_path):
    url, _ = logged_api

    api(url, tmp_path / "r", "--token-env", "HK_TOKEN_A", "--token-env", "HK_TOKEN_B")

    out = capsys.readouterr().out
    assert "not tested (refused by login) as HK_TOKEN_A: 1 operation(s)" in out
    assert "  GET /report" in out
    assert "login) as HK_TOKEN_B" not in out  # the admin is refused nowhere


def test_a_token_that_works_on_nothing_is_never_a_pass(logged_api, capsys, tmp_path):
    url, _ = logged_api

    code = api(url, tmp_path / "r", "--token-env", "HK_TOKEN_A", "--token-env", "HK_BROKEN")

    assert code == 2
    assert "HK_BROKEN" in capsys.readouterr().err


COMPLETE = {"complete": True, "stop_reason": "completed", "operations": {"tested": 4}}


def test_with_several_users_a_plain_user_refused_almost_everywhere_still_counts():
    refused = ["GET /a", "GET /b", "GET /c"]  # 3 of 4: an admin-heavy API, a plain user

    schemathesis.no_silent_pass(COMPLETE, refused, "HK_TEACHER")  # no error
    with pytest.raises(ToolError, match="authentication failed"):
        schemathesis.no_silent_pass(COMPLETE, refused)  # alone, that token failed


def test_requests_sent_without_login_on_purpose_are_not_refusals(tmp_path):
    def event(label, *answers):
        interactions = {
            str(n): {"request": {"headers": headers}, "response": {"status_code": status}}
            for n, (headers, status) in enumerate(answers)
        }
        recorder = {"label": label, "interactions": interactions}
        return json.dumps({"ScenarioFinished": {"recorder": recorder}})

    login = {"Authorization": ["[Filtered]"]}
    events = tmp_path / "events.ndjson"
    events.write_text(
        "\n".join(
            [
                event("GET /open", ({}, 401), (login, 200)),
                event("GET /admin", ({}, 401), (login, 403)),
                event("GET /probed", ({}, 401)),
            ]
        ),
        encoding="utf-8",
    )

    assert schemathesis.refused_by_login({}, events) == ["GET /admin"]
