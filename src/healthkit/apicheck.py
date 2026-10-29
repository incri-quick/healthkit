"""`healthkit api`: send every route good and bad input; any 500 is a finding (slice 007).

Whole-API and slow (D-014), so not part of `review`. Exit codes as `review`: 0 no
server errors found, 1 findings, 2 could not check (never reported as a pass).
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

from healthkit import config, gitdiff, policy
from healthkit.findings import Finding, ToolError
from healthkit.tools import schemathesis

# The summary counts each kind apart (slice 022); any other rule counts as "other".
KINDS = {"ST101": "server errors", "must-refuse": "access leaks", "ST402": "cross-user reads"}


def add_parser(commands) -> None:  # noqa: ANN001 - argparse's private subparsers type
    api = commands.add_parser("api", help="send bad input to every route; a 500 is a finding")
    api.add_argument("--schema", required=True, help="OpenAPI URL or file")
    api.add_argument("--base-url", help="API base URL (needed when --schema is a file)")
    api.add_argument(
        "--token-env",
        action="append",
        default=[],
        metavar="NAME",
        help="environment variable holding a user's bearer token; give two or more users: "
        "each is tested, and one user must not read another's objects",
    )
    api.add_argument(
        "--allow-writes",
        action="store_true",
        help="also send POST, PUT, PATCH and DELETE: this CHANGES DATA (default: reads only)",
    )
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
    """The reports hold every answer the API gave, personal data included (another
    project's: 469 parents' details). A temp folder is deleted when the run ends, failed
    runs too; a folder named with --report-dir is kept, as asked (slice 022)."""
    if args.report_dir:
        return _run(args, args.report_dir, kept=True)
    report_dir = Path(tempfile.mkdtemp(prefix="healthkit-api-"))
    try:
        return _run(args, report_dir, kept=False)
    finally:
        shutil.rmtree(report_dir, ignore_errors=True)


def _run(args, report_dir: Path, *, kept: bool) -> int:  # noqa: ANN001 - argparse.Namespace
    try:
        urls = [u for u in (args.schema, args.base_url) if u and "://" in u]
        schemathesis.check_hosts_are_local(urls, args.allow_remote_host)
        users = _users(args.token_env)
        settings = _settings()
        result = schemathesis.run(
            args.schema,
            args.base_url,
            users,
            args.max_examples,
            report_dir,
            parameters=settings.api_parameters,
            writes=args.allow_writes,
        )
    except (ToolError, config.ConfigError) as exc:
        print(f"healthkit api: {exc}", file=sys.stderr)
        return 2
    # A route the project accepts, with a written reason: e.g. a capability URL, where the
    # token in the path is the credential (QuickRPA's agent status, slice 016).
    access = policy.check(
        settings.api_deny, result.statuses, writes=args.allow_writes, sizes=result.sizes
    )
    found = result.findings + access.findings
    findings = [f for f in found if not settings.allows(f)]
    allowed = len(found) - len(findings)
    for finding in sorted(set(findings), key=lambda f: (f.path, f.rule)):
        print(f"{finding.path}: [{finding.tool} {finding.rule}] {finding.message}")
    # Never silent: name what the login kept out (slice 007), for each user (slice 019),
    # and what had no valid sample data (slice 020).
    _per_user("not tested (refused by login)", result.refused, several=len(users) > 1)
    _per_user("shallow (no valid sample data)", result.shallow, several=len(users) > 1)
    if access.unchecked:  # and what the access policy could not prove (slice 021)
        print(f"access policy not checked: {len(access.unchecked)}")
        for line in access.unchecked:
            print(f"  {line}")
    routes = len({f.path for f in findings})
    verdict = f"{routes} route(s) failed a check" if findings else "no server errors found"
    parts = [f"healthkit api: {verdict} in {result.tested} operation(s)", *_kinds(findings)]
    parts += (
        [f"users: {len(users)}, each tested (cross-user reads checked)"] if len(users) > 1 else []
    )
    parts += ["writes on: this run may have changed data"] if args.allow_writes else ["reads only"]
    parts += [f"allowed: {allowed}"] if allowed else []
    if settings.api_deny:
        parts += [f"access policy: {access.refused} route(s) refused as required"]
    shallow = len({op for operations in result.shallow.values() for op in operations})
    parts += [f"shallow (no valid sample data): {shallow}"] if shallow else []
    parts += [f"reports: {report_dir}" if kept else "reports: deleted (keep them: --report-dir)"]
    print(" | ".join(parts))
    for error in access.errors:
        print(f"healthkit api: {error}", file=sys.stderr)
    return 2 if access.errors else 1 if findings else 0


def _kinds(findings: list[Finding]) -> list[str]:
    counts: dict[str, int] = {}
    for finding in set(findings):
        kind = KINDS.get(finding.rule, "other")
        counts[kind] = counts.get(kind, 0) + 1
    order = [*KINDS.values(), "other"]
    return [f"{kind}: {counts[kind]}" for kind in order if kind in counts]


def _per_user(title: str, operations: dict[str, list[str]], *, several: bool) -> None:
    for name, listed in operations.items():
        who = f" as {name}" if several else ""
        print(f"{title}{who}: {len(listed)} operation(s)")
        for operation in listed:
            print(f"  {operation}")


def _settings() -> config.Settings:
    """The project's `.healthkit/config.toml`, when run inside a git repository."""
    try:
        return config.load(gitdiff.repo_root(Path.cwd()))
    except gitdiff.GitError:
        return config.Settings()


def _users(names: list[str]) -> dict[str, str]:
    """Each user, named by the variable holding its token (slice 019)."""
    users = {name: _token(name) for name in names}
    if len(users) < len(names):
        msg = "the same --token-env was given twice"
        raise ToolError(msg)
    return users


def _token(name: str) -> str:
    """Read the token by variable name only; the value is never printed (slice 007)."""
    token = os.environ.get(name)
    if not token:
        msg = f"--token-env {name}: that environment variable is not set"
        raise ToolError(msg)
    return token
