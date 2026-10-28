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
                f"refusing {host}: the API pack creates, changes and deletes data. "
                f"Run it against a local test stack, or name the host with "
                f"--allow-remote-host {host} (never production)."
            )
            raise ToolError(msg)


def run(  # noqa: PLR0913 - each argument is one setting of the run
    schema: str,
    base_url: str | None,
    tokens: list[str],
    max_examples: int,
    report_dir: Path,
    *,
    parameters: tuple[tuple[str, object], ...] = (),
) -> ApiRun:
    report_dir = report_dir.resolve()
    report_dir.mkdir(parents=True, exist_ok=True)
    report = report_dir / "schemathesis-run.json"
    if "://" not in schema:  # a file: absolute, because the run starts in report_dir
        schema = str(Path(schema).resolve())
    args = [
        *COMMAND,
        "run",
        schema,
        "--checks",
        _prepare(report_dir, tokens, parameters),
        "--max-examples",
        str(max_examples),
        "--generation-deterministic",
        "--report",
        "json",
        "--report-json-path",
        str(report),
    ]
    args += ["--url", base_url] if base_url else []
    args += ["-H", f"Authorization: Bearer {tokens[0]}"] if len(tokens) == 1 else []
    env = {**os.environ, "PYTHONUTF8": "1"}  # measured: cp1252 console crash otherwise
    # Measured: it writes `.schemathesis/` and `.hypothesis/` into the folder it runs from
    # even in deterministic mode, so it runs from report_dir, never the user's project.
    try:
        result = subprocess.run(  # noqa: S603 - argument list, no shell
            args, capture_output=True, env=env, cwd=report_dir, check=False
        )
    except OSError as exc:
        msg = f"could not run schemathesis: {exc}"
        raise ToolError(msg) from exc
    finally:
        (report_dir / AUTH_FILE).unlink(missing_ok=True)  # never leave a token behind
    (report_dir / "schemathesis-console.txt").write_bytes(result.stdout + result.stderr)
    if result.returncode not in (0, 1) and not report.is_file():
        msg = f"could not run schemathesis (exit {result.returncode})"
        raise ToolError(msg)
    try:
        data = json.loads(report.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        msg = f"schemathesis gave no readable report (exit {result.returncode})"
        raise ToolError(msg) from exc
    _no_silent_pass(data)
    findings = [
        Finding(tool=NAME, rule=failure["code"], path=operation, line=0, message=failure["title"])
        for failure in data.get("failures", [])
        for operation in failure.get("operations", [])
    ]
    warnings = data.get("warnings", {})
    return ApiRun(
        findings=findings,
        tested=data.get("operations", {}).get("tested", 0),
        refused=list(warnings.get("missing_auth", [])),
        shallow=len(warnings.get("missing_test_data", [])),
    )


def _prepare(report_dir: Path, tokens: list[str], parameters: tuple) -> str:
    """Write the run's own `schemathesis.toml` (it reads it from the folder it runs in);
    return the checks. Measured (slice 016): `[parameters]` takes real values, `${VAR}`
    included; two or more users need a Web Fuzzing Commons auth file AND `peers`, or the
    cross-user read check does not run."""
    lines = ["[parameters]", *(f"{json.dumps(k)} = {json.dumps(v)}" for k, v in parameters)]
    checks = "not_a_server_error"
    if len(tokens) > 1:
        users = [f"user{n}" for n in range(1, len(tokens) + 1)]
        auth = [
            {"name": user, "fixedHeaders": [{"name": "Authorization", "value": f"Bearer {t}"}]}
            for user, t in zip(users, tokens, strict=True)
        ]
        auth_json = json.dumps({"schemaVersion": "1.0", "auth": auth})
        (report_dir / AUTH_FILE).write_bytes(auth_json.encode("utf-8"))
        lines += [
            "",
            "[auth.wfc]",
            f"path = {json.dumps(AUTH_FILE)}",
            f"peers = {json.dumps(users)}",
        ]
        checks += ",object_level_authorization"
    text = "".join(f"{line}\n" for line in lines)
    (report_dir / "schemathesis.toml").write_bytes(text.encode("utf-8"))
    return checks


@dataclass(frozen=True)
class ApiRun:
    findings: list[Finding]
    tested: int
    refused: list[str]  # answered only 401/403: not tested behind their login
    shallow: int  # no valid sample data (e.g. real IDs): tested only on the surface


def _no_silent_pass(data: dict) -> None:
    """A run that could not check must never read as "no 500s" (L-004)."""
    if not data.get("complete") or data.get("stop_reason") != "completed":
        titles = [e.get("title", "error") for e in data.get("errors", [])] or ["incomplete run"]
        msg = f"schemathesis could not check the API: {', '.join(titles)}"
        raise ToolError(msg)
    refused = data.get("warnings", {}).get("missing_auth", [])
    tested = data.get("operations", {}).get("tested", 0)
    # Most operations refused = the token did not work: nothing behind the login was
    # tested. A few refused = routes with their own login scheme (QuickRPA: 18 of 479);
    # those are reported as not tested, and the rest still count (slice 007).
    if refused and len(refused) * 2 > tested:
        msg = (
            f"authentication failed for {len(refused)} of {tested} operation(s) "
            f"(e.g. {refused[0]}): nothing behind the login was tested. "
            f"Pass a token with --token-env."
        )
        raise ToolError(msg)
    if errored := data.get("operations", {}).get("errored"):
        msg = f"schemathesis could not test {errored} operation(s)"
        raise ToolError(msg)
