"""`healthkit api`: never a 500 (slice 007). Runs real Schemathesis against a tiny local
API (tests/fixtures/crashy_api.py) that reproduces QuickRPA's AA-73 and AA-75 crashes.

Slow (each run generates real requests): about 10 seconds per test.
"""

import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

from healthkit import cli
from healthkit.tools import schemathesis

CRASHY = Path(__file__).parent / "fixtures" / "crashy_api.py"
TOKEN = "s3cr3t-T0KEN-xyz"  # noqa: S105 - a fake token for the test API


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture
def crashy_api():
    started = []

    def start(*extra: str) -> str:
        port = free_port()
        process = subprocess.Popen(
            [sys.executable, str(CRASHY), str(port), *extra],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        started.append(process)
        url = f"http://127.0.0.1:{port}"
        for _ in range(50):
            try:
                urllib.request.urlopen(f"{url}/openapi.json", timeout=1)  # noqa: S310 - local
            except OSError:
                time.sleep(0.1)
            else:
                return url
        pytest.fail("test API did not start")
        return url

    yield start
    for process in started:
        process.kill()


def api(*args: str) -> int:
    return cli.main(["api", *args, "--max-examples", "20"])


def test_routes_that_crash_on_bad_input_are_reported(crashy_api, capsys, tmp_path):
    url = crashy_api()

    code = api("--schema", f"{url}/openapi.json", "--report-dir", str(tmp_path))

    out = capsys.readouterr().out
    assert code == 1
    assert "POST /profile: [schemathesis ST101]" in out  # AA-75
    assert "POST /token: [schemathesis ST101]" in out  # AA-73
    assert "POST /ok" not in out  # validates and answers 422: not a finding
    assert out.count("POST /profile:") == 1  # one finding per route, not one per request


def test_nothing_is_written_into_the_folder_it_runs_from(crashy_api, monkeypatch, tmp_path):
    # Found in slice 007: Schemathesis kept a `.schemathesis/` example database in the
    # current folder, i.e. inside the user's project (CLAUDE.md rule 4).
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    url = crashy_api()

    api("--schema", f"{url}/openapi.json", "--report-dir", str(tmp_path / "reports"))

    assert list(project.iterdir()) == []


def test_a_non_local_host_is_refused_before_any_request(capsys, monkeypatch, tmp_path):
    monkeypatch.setattr(schemathesis, "COMMAND", ["no-such-tool-must-not-run"])

    code = api("--schema", "https://api.example.com/openapi.json", "--report-dir", str(tmp_path))

    assert code == 2
    err = capsys.readouterr().err
    assert "api.example.com" in err
    assert "--allow-remote-host" in err


def test_an_unreachable_schema_is_never_a_pass(tmp_path):
    code = api(
        "--schema", f"http://127.0.0.1:{free_port()}/openapi.json", "--report-dir", str(tmp_path)
    )

    assert code == 2


def test_a_missing_schemathesis_is_never_a_pass(crashy_api, capsys, monkeypatch, tmp_path):
    url = crashy_api()
    monkeypatch.setattr(schemathesis, "COMMAND", ["no-such-tool-healthkit-test"])

    assert api("--schema", f"{url}/openapi.json", "--report-dir", str(tmp_path)) == 2
    assert "could not run schemathesis" in capsys.readouterr().err


def test_every_request_refused_for_auth_is_never_a_pass(crashy_api, capsys, tmp_path):
    # Measured: Schemathesis exits 0 with no failures when every request gets 401.
    url = crashy_api("--require-token", TOKEN)

    code = api("--schema", f"{url}/openapi.json", "--report-dir", str(tmp_path))

    assert code == 2
    assert "authentication" in capsys.readouterr().err


def test_the_token_is_used_and_never_shown(crashy_api, capsys, monkeypatch, tmp_path):
    url = crashy_api("--require-token", TOKEN)
    monkeypatch.setenv("HEALTHKIT_API_TOKEN", TOKEN)

    code = api(
        "--schema",
        f"{url}/openapi.json",
        "--token-env",
        "HEALTHKIT_API_TOKEN",
        "--report-dir",
        str(tmp_path),
    )

    captured = capsys.readouterr()
    assert code == 1  # authenticated, so the crashes are found
    assert TOKEN not in captured.out + captured.err
    for report in tmp_path.rglob("*"):
        if report.is_file():
            assert TOKEN not in report.read_text(encoding="utf-8", errors="replace")


def test_a_few_routes_with_another_login_scheme_do_not_hide_the_rest(
    crashy_api, capsys, monkeypatch, tmp_path
):
    # QuickRPA sweep (slice 007): 18 of 479 operations use other schemes (agent/bot
    # tokens, the login routes themselves); treating that as "nothing tested" hid all
    # 6 real crashes. Only a token that clearly failed (most routes refused) is exit 2.
    url = crashy_api("--require-token", TOKEN)
    monkeypatch.setenv("HEALTHKIT_API_TOKEN", TOKEN)

    code = api(
        "--schema",
        f"{url}/openapi.json",
        "--token-env",
        "HEALTHKIT_API_TOKEN",
        "--report-dir",
        str(tmp_path),
    )

    out = capsys.readouterr().out
    assert code == 1
    assert "POST /profile: [schemathesis ST101]" in out
    assert "not tested (refused by login): 1 operation(s)" in out
    assert "POST /agent-only" in out


def test_a_named_token_variable_that_is_unset_is_an_error(
    crashy_api, capsys, monkeypatch, tmp_path
):
    url = crashy_api()
    monkeypatch.delenv("HEALTHKIT_API_TOKEN", raising=False)

    code = api(
        "--schema",
        f"{url}/openapi.json",
        "--token-env",
        "HEALTHKIT_API_TOKEN",
        "--report-dir",
        str(tmp_path),
    )

    assert code == 2
    assert "HEALTHKIT_API_TOKEN" in capsys.readouterr().err
