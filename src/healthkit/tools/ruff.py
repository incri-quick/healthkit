"""ruff adapter. Rules are listed explicitly: ruff's defaults change between versions (L-002)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from healthkit.findings import Finding, ToolError

COMMAND = ["uvx", "ruff@0.17.2"]
# The gate set from slice 001 (RESULTS.md, ruff verdict).
GATE_RULES = "F821,F401,F811,I001,RUF052,N806,N814,PLC2701,BLE001"
_BATCH = 200  # keep each command line short (Windows limit)


def run(root: Path, files: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    for start in range(0, len(files), _BATCH):
        findings += _run_batch(root, files[start : start + _BATCH])
    return findings


def _run_batch(root: Path, files: list[str]) -> list[Finding]:
    args = [
        *COMMAND,
        "check",
        "--no-cache",
        "--preview",
        "--select",
        GATE_RULES,
        "--output-format",
        "json",
        "--exit-zero",
        *files,
    ]
    try:
        result = subprocess.run(args, cwd=root, capture_output=True, check=False)  # noqa: S603
    except FileNotFoundError as exc:
        msg = f"could not run ruff: {COMMAND[0]} not found"
        raise ToolError(msg) from exc
    if result.returncode != 0:
        msg = f"ruff failed (exit {result.returncode}): {result.stderr.decode('utf-8', 'replace')}"
        raise ToolError(msg.strip())
    try:
        raw = json.loads(result.stdout)
    except ValueError as exc:
        msg = "ruff gave unreadable output (not JSON)"
        raise ToolError(msg) from exc
    return [_to_finding(root, item) for item in raw]


def _to_finding(root: Path, item: dict) -> Finding:
    path = Path(item["filename"]).resolve().relative_to(root.resolve()).as_posix()
    return Finding(
        tool="ruff",
        rule=item["code"] or "syntax",
        path=path,
        line=item["location"]["row"],
        message=item["message"],
    )
