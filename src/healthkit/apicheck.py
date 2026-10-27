"""`healthkit api`: send every route good and bad input; any 500 is a finding (slice 007).

Whole-API and slow (D-014), so not part of `review`. Exit codes as `review`: 0 no
server errors found, 1 findings, 2 could not check (never reported as a pass).
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from healthkit.findings import ToolError
from healthkit.tools import schemathesis


def add_parser(commands) -> None:  # noqa: ANN001 - argparse's private subparsers type
    api = commands.add_parser("api", help="send bad input to every route; a 500 is a finding")
    api.add_argument("--schema", required=True, help="OpenAPI URL or file")
    api.add_argument("--base-url", help="API base URL (needed when --schema is a file)")
    api.add_argument("--token-env", help="NAME of the environment variable holding a bearer token")
    api.add_argument("--max-examples", type=int, default=50, help="generated inputs per route")
    api.add_argument("--report-dir", type=Path, help="where to keep the reports (default: temp)")
    api.add_argument(
        "--allow-remote-host",
        action="append",
        default=[],
        metavar="HOST",
        help="allow a non-local host (never production)",
    )


def run(args) -> int:  # noqa: ANN001 - argparse.Namespace
    report_dir = args.report_dir or Path(tempfile.mkdtemp(prefix="healthkit-api-"))
    try:
        urls = [u for u in (args.schema, args.base_url) if u and "://" in u]
        schemathesis.check_hosts_are_local(urls, args.allow_remote_host)
        token = _token(args.token_env)
        result = schemathesis.run(args.schema, args.base_url, token, args.max_examples, report_dir)
    except ToolError as exc:
        print(f"healthkit api: {exc}", file=sys.stderr)
        return 2
    findings = result.findings
    for finding in sorted(set(findings), key=lambda f: (f.path, f.rule)):
        print(f"{finding.path}: [{finding.tool} {finding.rule}] {finding.message}")
    if result.refused:  # never silent: name what the login kept out (slice 007)
        print(f"not tested (refused by login): {len(result.refused)} operation(s)")
        for operation in result.refused:
            print(f"  {operation}")
    routes = len({f.path for f in findings})
    verdict = (
        f"{routes} route(s) answered with a server error" if findings else "no server errors found"
    )
    parts = [f"healthkit api: {verdict} in {result.tested} operation(s)"]
    parts += [f"shallow (no valid sample data): {result.shallow}"] if result.shallow else []
    parts += [f"reports: {report_dir}"]
    print(" | ".join(parts))
    return 1 if findings else 0


def _token(name: str | None) -> str | None:
    """Read the token by variable name only; the value is never printed (slice 007)."""
    if not name:
        return None
    token = os.environ.get(name)
    if not token:
        msg = f"--token-env {name}: that environment variable is not set"
        raise ToolError(msg)
    return token
