"""The API report names every route (slice 020). From another project's run: a
`Stateful tests: Server error` line hid `GET /assignments/`, `shallow: 8` named no route,
and a 38 MB report folder sat in the repo, not ignored by git."""

import json
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
SERVER_ERROR = {"code": "ST101", "title": "Server error"}


def stateful_failure(operation: str) -> str:
    """One stateful-phase event, in the format measured on a real run (slice 020)."""
    failure = {"type": "ServerError", **SERVER_ERROR, "operation": operation}
    check = {
        "name": "not_a_server_error",
        "status": "failure",
        "failure_info": {"failure": failure},
    }
    scenario = {
        "phase": "stateful",
        "status": "failure",
        "recorder": {"label": "Stateful tests", "cases": {}, "checks": {"c1": [check]}},
    }
    return json.dumps({"ScenarioFinished": scenario})


def report(*operations: str) -> dict:
    return {"failures": [{**SERVER_ERROR, "operations": list(operations)}]}


def routes(findings) -> list[str]:
    return sorted(f.path for f in findings)


def test_a_stateful_failure_is_named_by_its_route(tmp_path):
    events = tmp_path / "events.ndjson"
    events.write_text(
        "\n".join([stateful_failure("GET /assignments/"), stateful_failure("GET /notices/")]),
        encoding="utf-8",
    )

    found = schemathesis.failures(
        report("GET /notices/", "Stateful tests"), schemathesis.read_events(events)
    )

    assert routes(found) == ["GET /assignments/", "GET /notices/"]  # /notices/ not doubled
    assert {(f.rule, f.message) for f in found} == {("ST101", "Server error")}


def test_with_no_route_named_the_stateful_line_stays(tmp_path):
    found = schemathesis.failures(
        report("Stateful tests"), schemathesis.read_events(tmp_path / "missing.ndjson")
    )

    assert routes(found) == ["Stateful tests"]  # a failure is never dropped


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


def test_shallow_routes_are_listed_and_reports_stay_out_of_git(
    repo, tenant_api, capsys, monkeypatch
):
    monkeypatch.setenv("HK_TOKEN_A", "tok-a")
    repo.write("app.py", "x = 1\n")
    repo.commit()

    cli.main(
        [
            "api",
            "--schema",
            f"{tenant_api}/openapi.json",
            "--token-env",
            "HK_TOKEN_A",
            "--max-examples",
            "10",
            "--report-dir",
            "healthkit-api-report",
        ]
    )

    out = capsys.readouterr().out
    assert "shallow (no valid sample data): 1 operation(s)\n  GET /items/{item_id}" in out
    assert (repo.root / "healthkit-api-report" / "schemathesis-run.json").is_file()
    assert repo.git("status", "--porcelain") == ""  # one `git add .` cannot commit it
