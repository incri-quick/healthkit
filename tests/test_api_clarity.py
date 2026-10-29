"""The API report says how big a leak was, leaves no personal data behind, and counts
each kind (slice 022). From another project's run: every "must refuse" finding had to
be probed by hand to tell 469 parents' details from an empty list, the report folder
held those details after the run, and "40 routes failed" mixed three kinds."""

import base64
import json
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import pytest

from healthkit import cli, config, policy
from healthkit.tools import schemathesis

TENANT = Path(__file__).parent / "fixtures" / "tenant_api.py"
pytestmark = pytest.mark.usefixtures("repo")


@pytest.mark.parametrize(
    ("body", "records"),
    [
        ([{"id": 1}, {"id": 2}], 2),
        ([], 0),
        ({"total": 3, "items": [1, 2, 3]}, 3),
        ({"id": 1, "name": "x"}, 1),
        ({}, 0),
    ],
)
def test_records_are_counted_by_the_shape_of_the_answer(body, records):
    assert schemathesis.records(json.dumps(body).encode()) == records


def test_an_answer_that_is_not_json_has_no_count():
    assert schemathesis.records(b"<html>hello</html>") is None


@pytest.fixture
def tenant_api(monkeypatch):
    monkeypatch.setenv("HK_TOKEN_A", "tok-a")
    monkeypatch.setenv("HK_TOKEN_B", "tok-b")
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


def api(url: str, *args: str) -> int:
    schema = ["--schema", f"{url}/openapi.json", "--max-examples", "10"]
    return cli.main(["api", *schema, *args])


def test_a_leak_says_how_big_the_answer_was(repo, tenant_api, capsys, tmp_path):
    repo.write(
        ".healthkit/config.toml",
        '[[api.deny]]\nuser = "HK_TOKEN_A"\nroutes = ["GET /notes"]\nreason = "admins only"\n',
    )

    api(tenant_api, "--token-env", "HK_TOKEN_A", "--report-dir", str(tmp_path / "r"))

    out = capsys.readouterr().out
    assert "GET /notes: [policy must-refuse] HK_TOKEN_A got 200 (1 record)" in out
    assert "reports: deleted" not in out  # --report-dir: kept, as asked


@pytest.fixture
def temp_dir(tmp_path, monkeypatch):
    folder = tmp_path / "temp"
    folder.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(folder))
    return folder


def test_without_report_dir_no_report_is_left_behind(tenant_api, capsys, temp_dir):
    api(tenant_api, "--token-env", "HK_TOKEN_A")

    assert list(temp_dir.iterdir()) == []
    assert "reports: deleted" in capsys.readouterr().out


def test_a_failed_run_leaves_no_report_either(monkeypatch, temp_dir):
    monkeypatch.setattr(schemathesis, "COMMAND", ["no-such-schemathesis-healthkit-test"])
    monkeypatch.setenv("HK_TOKEN_A", "tok-a")

    assert api("http://127.0.0.1:9", "--token-env", "HK_TOKEN_A") == 2
    assert list(temp_dir.iterdir()) == []


def test_the_summary_counts_each_kind(repo, tenant_api, capsys, tmp_path):
    # User b crashes GET /report; any user reads any note (ST402); policy denies a note.
    repo.write(
        ".healthkit/config.toml",
        '[[api.deny]]\nuser = "HK_TOKEN_A"\nroutes = ["GET /notes"]\nreason = "admins only"\n',
    )

    api(
        tenant_api,
        "--token-env",
        "HK_TOKEN_A",
        "--token-env",
        "HK_TOKEN_B",
        "--report-dir",
        str(tmp_path / "r"),
    )

    summary = capsys.readouterr().out.splitlines()[-1]
    assert "server errors: 1" in summary
    assert "access leaks: 1" in summary
    assert "cross-user reads: 1" in summary
    assert "other" not in summary


def test_the_largest_2xx_answer_is_kept(tmp_path):
    def answer(status, body):
        content = {"$base64": base64.b64encode(json.dumps(body).encode()).decode()}
        request = {"headers": {"Authorization": ["[Filtered]"]}}
        return {"request": request, "response": {"status_code": status, "content": content}}

    answers = [answer(200, [1, 2]), answer(200, [1] * 5), answer(200, [1]), answer(404, [1] * 9)]
    recorder = {"label": "GET /people", "interactions": dict(enumerate(answers))}
    events = tmp_path / "events.ndjson"
    events.write_text(json.dumps({"ScenarioFinished": {"recorder": recorder}}), encoding="utf-8")

    assert schemathesis.read_events(events).sizes == {"GET /people": 5}


@pytest.mark.parametrize(("size", "said"), [(0, "(empty)"), (469, "(469 records)")])
def test_the_size_is_said_plainly(size, said):
    rule = config.Deny("HK_TEACHER", ("GET /people",), "own class only")

    run = policy.check(
        (rule,),
        {"HK_TEACHER": {"GET /people": {200}}},
        writes=False,
        sizes={"HK_TEACHER": {"GET /people": size}},
    )

    assert run.findings[0].message.startswith(f"HK_TEACHER got 200 {said}, ")
