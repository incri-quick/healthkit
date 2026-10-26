"""Opengrep adapter: healthkit's own rules only (D-013). Errors are never ignored (L-004).

healthkit does not download Opengrep (slice 003, decision 2): it is found on PATH as
`opengrep`, or at HEALTHKIT_OPENGREP.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from healthkit.findings import Finding, ToolError

NAME = "opengrep"
RULES = Path(__file__).resolve().parents[1] / "rules"
INSTALL_HINT = (
    "Opengrep not found. Install the signed binary from "
    "https://github.com/opengrep/opengrep/releases and put it on PATH as `opengrep`, "
    "or set HEALTHKIT_OPENGREP to its path."
)
_BATCH = 200


def find_binary() -> list[str]:
    path = os.environ.get("HEALTHKIT_OPENGREP") or shutil.which("opengrep")
    if not path:
        raise ToolError(INSTALL_HINT)
    return [path]


def run(root: Path, files: list[str]) -> list[Finding]:
    command = find_binary()
    findings: list[Finding] = []
    for start in range(0, len(files), _BATCH):
        findings += _run_batch(root, command, files[start : start + _BATCH])
    return findings


def _run_batch(root: Path, command: list[str], files: list[str]) -> list[Finding]:
    args = [*command, "scan", "--config", str(RULES), "--json", "-q", *files]
    try:
        result = subprocess.run(args, cwd=root, capture_output=True, check=False)  # noqa: S603
    except OSError as exc:
        msg = f"could not run opengrep at {command[0]}: {exc}"
        raise ToolError(msg) from exc
    try:
        data = json.loads(result.stdout)
    except ValueError as exc:
        msg = "opengrep gave unreadable output (not JSON)"
        raise ToolError(msg) from exc
    if errors := data.get("errors"):
        # Opengrep reports these with exit code 0; a timed-out file was not checked.
        described = "; ".join(f"{e.get('type')} in {e.get('path')}" for e in errors)
        msg = f"opengrep could not check everything: {described}"
        raise ToolError(msg)
    if result.returncode != 0:
        msg = f"opengrep failed (exit {result.returncode})"
        raise ToolError(msg)
    return [_to_finding(item) for item in data["results"]]


def _to_finding(item: dict) -> Finding:
    return Finding(
        tool=NAME,
        rule=item["check_id"].rsplit(".", 1)[-1],  # the id is prefixed with the rule file path
        path=item["path"].replace("\\", "/"),
        line=item["start"]["line"],
        message=" ".join(item["extra"]["message"].split()),
    )
