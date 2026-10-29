"""Project checks: a project's own guard commands, run before push (slice 008, D-022).

healthkit never copies a project's guards; it makes sure they run. The commands are
taken from the BASE branch's config by the caller: a branch that adds a command must
not be able to run it on the reviewer's machine before a person approves it (D-018).
"""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from healthkit.config import CONFIG, glob_match
from healthkit.findings import Finding, ToolError

if TYPE_CHECKING:
    from healthkit.config import Check

TAIL = 5  # lines of a failing check's output printed; the rest goes to a report file


@dataclass
class CheckRun:
    findings: list[Finding] = field(default_factory=list)
    tails: dict[str, list[str]] = field(default_factory=dict)
    ran: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def run(root: Path, checks: tuple[Check, ...], changed: list[str]) -> CheckRun:
    result = CheckRun()
    report_dir: Path | None = None
    for check in checks:
        label = f"check {check.name}"
        if not any(glob_match(path, pattern) for path in changed for pattern in check.paths):
            result.skipped.append(f"{label} (no matching changes)")
            continue
        try:
            code, output = _execute(root, check)
        except ToolError as exc:
            result.errors.append(f"{label}: {exc}")
            continue
        result.ran.append(label)
        if code == 0:
            continue
        report_dir = report_dir or Path(tempfile.mkdtemp(prefix="healthkit-checks-"))
        report = report_dir / f"{len(result.findings) + 1}.txt"
        report.write_bytes(output.encode("utf-8"))  # never CRLF (L-011)
        message = f"failed (exit {code}); full output: {report}"
        finding = Finding(
            tool="check", rule=check.name, path=CONFIG.as_posix(), line=0, message=message
        )
        result.findings.append(finding)
        result.tails[check.name] = output.rstrip().splitlines()[-TAIL:]
    return result


def _execute(root: Path, check: Check) -> tuple[int, str]:
    try:
        done = subprocess.run(  # noqa: S603 - argument list from the base branch's config
            list(check.command),
            cwd=root,
            capture_output=True,
            timeout=check.timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        msg = f"timed out after {check.timeout}s"
        raise ToolError(msg) from exc
    except OSError as exc:
        msg = f"could not start {check.command[0]}: {exc}"
        raise ToolError(msg) from exc
    output = (done.stdout + done.stderr).decode("utf-8", "replace")
    return done.returncode, output
