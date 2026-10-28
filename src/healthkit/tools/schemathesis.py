"""Schemathesis adapter: the API pack, "never a 500" (slice 007, D-017/D-021).

Measured before coding (slice 007 SPEC):
- On Windows its console output crashes with a cp1252 error unless PYTHONUTF8=1.
- Its JSON run report lists failures by type with the operations ("POST /profile").
- When every request is refused for auth it exits 0 with no failures; the only signal
  is `warnings.missing_auth`. That is a run that checked nothing, never a pass (L-004).
- A token passed as a header is recorded as "[Filtered]" in the report.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from healthkit.findings import Finding, ToolError

NAME = "schemathesis"
COMMAND = ["uvx", "schemathesis@4.32.5"]
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
AUTH_FILE = "users.wfc.json"  # holds the tokens: removed after every run (slice 016)


def check_hosts_are_local(urls: list[str], allowed: list[str]) -> None:
    """Refuse, before any request, a target that is not this machine (slice 007 safety)."""
    for url in urls:
        host = urlparse(url).hostname
        if host and host not in LOCAL_HOSTS and host not in allowed:
            msg = (
                f"refusing {host}: the API pack sends bad input, and changes data with "
                f"--allow-writes. Run it against a local test stack, or name the host with "
                f"--allow-remote-host {host} (never production)."
            )
            raise ToolError(msg)


def run(  # noqa: PLR0913 - each argument is one setting of the run
    schema: str,
    base_url: str | None,
    users: dict[str, str],
    max_examples: int,
    report_dir: Path,
    *,
    parameters: tuple[tuple[str, object], ...] = (),
    writes: bool = False,
) -> ApiRun:
    """One run per user, each named by its token's variable (slice 019): fuzzing only the
    first user left every route only the second may use untested. `users` maps that name
    to the token. Reads only (GET) unless `writes`: a run that writes changes data
    (another project's run deactivated a user and reversed a payment)."""
    report_dir = report_dir.resolve()
    if "://" not in schema:  # a file: absolute, because the run starts in report_dir
        schema = str(Path(schema).resolve())
    several = len(users) > 1
    runs = {
        name: _run_as(
            schema,
            base_url,
            users,
            name,
            report_dir / name if several else report_dir,
            max_examples=max_examples,
            parameters=parameters,
            writes=writes,
        )
        for name in users or {"": ""}
    }
    found_by: dict[tuple[str, str, str], list[str]] = {}
    for name, (findings, _, _) in runs.items():
        for finding in findings:
            found_by.setdefault((finding.rule, finding.path, finding.message), []).append(name)
    reports = [data for _, data, _ in runs.values()]
    return ApiRun(
        findings=[
            Finding(
                tool=NAME,
                rule=rule,
                path=operation,
                line=0,
                message=f"{message} (as {', '.join(names)})" if several else message,
            )
            for (rule, operation, message), names in found_by.items()
        ],
        tested=max(data.get("operations", {}).get("tested", 0) for data in reports),
        refused={name: refused for name, (_, _, refused) in runs.items() if refused},
        shallow=max(len(data.get("warnings", {}).get("missing_test_data", [])) for data in reports),
    )


def _run_as(  # noqa: PLR0913 - each argument is one setting of the run
    schema: str,
    base_url: str | None,
    users: dict[str, str],
    name: str,
    folder: Path,
    *,
    max_examples: int,
    parameters: tuple,
    writes: bool,
) -> tuple[list[Finding], dict, list[str]]:
    """One Schemathesis run as the user `name`: its findings, its JSON report, and the
    operations the login refused."""
    folder.mkdir(parents=True, exist_ok=True)
    report = folder / "schemathesis-run.json"
    events = folder / "schemathesis-events.ndjson"
    args = [
        *COMMAND,
        "run",
        schema,
        "--checks",
        _prepare(folder, users, parameters, writes=writes),
        "--max-examples",
        str(max_examples),
        "--generation-deterministic",
        "--report",
        "json,ndjson",
        "--report-json-path",
        str(report),
        "--report-ndjson-path",
        str(events),
    ]
    args += ["--url", base_url] if base_url else []
    args += [] if writes else ["--include-method", "GET"]
    if len(users) == 1:
        args += ["-H", f"Authorization: Bearer {users[name]}"]
    elif users:
        args += ["--auth-wfc-user", name]
    env = {**os.environ, "PYTHONUTF8": "1"}  # measured: cp1252 console crash otherwise
    # Measured: it writes `.schemathesis/` and `.hypothesis/` into the folder it runs from
    # even in deterministic mode, so it runs from report_dir, never the user's project.
    try:
        result = subprocess.run(  # noqa: S603 - argument list, no shell
            args, capture_output=True, env=env, cwd=folder, check=False
        )
    except OSError as exc:
        msg = f"could not run schemathesis: {exc}"
        raise ToolError(msg) from exc
    finally:
        (folder / AUTH_FILE).unlink(missing_ok=True)  # never leave a token behind
    (folder / "schemathesis-console.txt").write_bytes(result.stdout + result.stderr)
    if result.returncode not in (0, 1) and not report.is_file():
        msg = f"could not run schemathesis (exit {result.returncode})"
        raise ToolError(msg)
    try:
        data = json.loads(report.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        msg = f"schemathesis gave no readable report (exit {result.returncode})"
        raise ToolError(msg) from exc
    refused = refused_by_login(data, events)
    no_silent_pass(data, refused, name if len(users) > 1 else None)
    findings = [
        Finding(tool=NAME, rule=failure["code"], path=operation, line=0, message=failure["title"])
        for failure in data.get("failures", [])
        for operation in failure.get("operations", [])
    ]
    return findings, data, refused


def refused_by_login(data: dict, events: Path) -> list[str]:
    """Operations that answered this user's requests only with 401 or 403. Measured (slice
    019): Schemathesis's own `missing_auth` counts 401 only, so a plain user's 403 on every
    admin route read as tested. Its event log records each response's status, the token as
    "[Filtered]"; requests it sent with no login on purpose carry no Authorization header."""
    statuses: dict[str, set[int]] = {}
    try:
        lines = events.read_text(encoding="utf-8").splitlines()
    except OSError:
        lines = []
    for line in lines:
        scenario = json.loads(line).get("ScenarioFinished") if line.strip() else None
        recorder = (scenario or {}).get("recorder", {})
        for interaction in (recorder.get("interactions") or {}).values():
            headers = {h.lower() for h in interaction.get("request", {}).get("headers", {})}
            response = interaction.get("response")
            if "authorization" in headers and response:
                statuses.setdefault(recorder["label"], set()).add(response["status_code"])
    denied = {label for label, codes in statuses.items() if codes <= {401, 403}}
    return sorted(denied | set(data.get("warnings", {}).get("missing_auth", [])))


def _prepare(folder: Path, users: dict[str, str], parameters: tuple, *, writes: bool) -> str:
    """Write the run's own `schemathesis.toml` (it reads it from the folder it runs in);
    return the checks. Measured (slice 016): `[parameters]` takes real values, `${VAR}`
    included; two or more users need a Web Fuzzing Commons auth file AND `peers`, or the
    cross-user read check does not run. Measured (slice 019): `--include-method GET` alone
    still sends DELETE, POST and others as "unexpected method" probes; with those switched
    off only GETs reach the server, and the bad-input tests still run."""
    lines = ["[parameters]", *(f"{json.dumps(k)} = {json.dumps(v)}" for k, v in parameters)]
    lines += [] if writes else ["", "[phases.coverage]", "unexpected-methods = []"]
    checks = "not_a_server_error"
    if len(users) > 1:
        auth = [
            {"name": name, "fixedHeaders": [{"name": "Authorization", "value": f"Bearer {t}"}]}
            for name, t in users.items()
        ]
        auth_json = json.dumps({"schemaVersion": "1.0", "auth": auth})
        (folder / AUTH_FILE).write_bytes(auth_json.encode("utf-8"))
        lines += [
            "",
            "[auth.wfc]",
            f"path = {json.dumps(AUTH_FILE)}",
            f"peers = {json.dumps(list(users))}",
        ]
        checks += ",object_level_authorization"
    text = "".join(f"{line}\n" for line in lines)
    (folder / "schemathesis.toml").write_bytes(text.encode("utf-8"))
    return checks


@dataclass(frozen=True)
class ApiRun:
    findings: list[Finding]
    tested: int
    refused: dict[str, list[str]]  # per user: answered only 401/403, not tested behind it
    shallow: int  # no valid sample data (e.g. real IDs): tested only on the surface


def no_silent_pass(data: dict, refused: list[str], user: str | None = None) -> None:
    """A run that could not check must never read as "no 500s" (L-004)."""
    if not data.get("complete") or data.get("stop_reason") != "completed":
        titles = [e.get("title", "error") for e in data.get("errors", [])] or ["incomplete run"]
        msg = f"schemathesis could not check the API: {', '.join(titles)}"
        raise ToolError(msg)
    tested = data.get("operations", {}).get("tested", 0)
    # One user: most operations refused = the token did not work. A few refused = routes
    # with their own login scheme (QuickRPA: 18 of 479); those are reported as not tested,
    # and the rest still count (slice 007). Several users: one may be a plain user refused
    # on every admin route, so only a token that works on NOTHING fails the run (slice 019).
    failed = len(refused) >= tested if user else len(refused) * 2 > tested
    if refused and failed:
        who = f" as {user}" if user else ""
        msg = (
            f"authentication failed{who} for {len(refused)} of {tested} operation(s) "
            f"(e.g. {refused[0]}): nothing behind the login was tested. "
            f"Pass a token with --token-env."
        )
        raise ToolError(msg)
    if errored := data.get("operations", {}).get("errored"):
        msg = f"schemathesis could not test {errored} operation(s)"
        raise ToolError(msg)
