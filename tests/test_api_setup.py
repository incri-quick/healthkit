"""The API check states its setup first, and a refusal must be comparable (slice 028).
A teammate ran a whole pass before learning which users the access rules expected;
QuickRPA warned that with a misconfigured allowed user, refusals look like passes."""

import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

from healthkit import cli, config, policy

TENANT = Path(__file__).parent / "fixtures" / "tenant_api.py"
MEMBER = config.Deny("HK_MEMBER", ("GET /approvals",), "needs approve permission")


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


def test_the_expected_users_are_named_before_the_run(repo, tenant_api, capsys, tmp_path):
    repo.write(
        ".healthkit/config.toml",
        '[[api.deny]]\nuser = "HK_TOKEN_A"\nroutes = ["GET /report"]\nreason = "admins only"\n'
        '[[api.deny]]\nuser = "HK_OTHER_ORG"\nroutes = ["GET /notes"]\nreason = "tenancy"\n',
    )
    schema = ["--schema", f"{tenant_api}/openapi.json", "--max-examples", "5"]

    cli.main(["api", *schema, "--token-env", "HK_TOKEN_A", "--report-dir", str(tmp_path / "r")])

    lines = capsys.readouterr().out.splitlines()
    expects = (
        "access policy expects: HK_OTHER_ORG, HK_TOKEN_A; not given: HK_OTHER_ORG "
        "(add --token-env HK_OTHER_ORG, or its rules are not checked)"
    )
    assert lines[0] == expects  # first: before a long run, not after it
    assert "refusals not compared with an allowed user" in lines[-1]  # one user only


def test_nothing_is_said_when_every_expected_user_is_given():
    assert policy.expected((MEMBER,), ["HK_APPROVER", "HK_MEMBER"]) is None


def test_a_route_that_refuses_everyone_proves_nothing():
    statuses = {"HK_APPROVER": {"GET /approvals": {403}}, "HK_MEMBER": {"GET /approvals": {403}}}

    run = policy.check((MEMBER,), statuses, writes=False)

    assert run.refused == 0
    assert run.unchecked == [
        (
            "GET /approvals as HK_MEMBER: refused, but no user got a successful answer here, "
            "so the refusal proves nothing (is an allowed user's token set up?)"
        )
    ]


def test_success_on_another_route_does_not_count():
    # QuickRPA's case: the approver's token works (its profile answers) but lacks the
    # permission on the approvals route. Only that route's answers can vouch for it.
    statuses = {
        "HK_APPROVER": {"GET /profile": {200}, "GET /approvals": {403}},
        "HK_MEMBER": {"GET /profile": {200}, "GET /approvals": {403}},
    }

    run = policy.check((MEMBER,), statuses, writes=False)

    assert run.refused == 0
    assert len(run.unchecked) == 1


def test_a_refusal_counts_when_another_user_was_answered():
    statuses = {"HK_APPROVER": {"GET /approvals": {200}}, "HK_MEMBER": {"GET /approvals": {403}}}

    run = policy.check((MEMBER,), statuses, writes=False)

    assert run.refused == 1
    assert run.unchecked == []


def test_with_one_user_a_refusal_counts_as_before():
    run = policy.check((MEMBER,), {"HK_MEMBER": {"GET /approvals": {403}}}, writes=False)

    assert run.refused == 1
