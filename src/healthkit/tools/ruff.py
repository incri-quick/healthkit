"""ruff adapter. Rules are listed explicitly: ruff's defaults change between versions (L-002).

The project's own ruff settings are ignored (`--isolated`): they could switch the gate off
(slice 005). Suppressions are found by running twice, honouring `# noqa` and ignoring it;
what only the second run reports was suppressed. ruff's own noqa rules decide.
"""

from __future__ import annotations

import ast
import dataclasses
import json
import subprocess
from pathlib import Path

from healthkit import config
from healthkit.findings import Finding, ToolError

NAME = "ruff"
COMMAND = ["uvx", "ruff@0.17.2"]
# The gate set from slice 001 (RESULTS.md, ruff verdict).
GATE_RULES = "F821,F401,F811,I001,RUF052,N806,N814,PLC2701,BLE001"
# For every project, advisory (slice 013, D-023): a quality signal, its threshold a judgement.
ADVISORY = {"C901"}
_BATCH = 200  # keep each command line short (Windows limit)


def run(root: Path, files: list[str]) -> list[Finding]:
    # Plus the checks the project chose in its own config (slice 013).
    rules = ",".join([GATE_RULES, *ADVISORY, *config.load(root).ruff_extra])
    findings: list[Finding] = []
    for start in range(0, len(files), _BATCH):
        batch = files[start : start + _BATCH]
        honoured = set(_check(root, batch, rules))
        everything = _check(root, batch, rules, "--ignore-noqa")
        findings += honoured
        findings += [
            dataclasses.replace(f, suppressed=True) for f in everything if f not in honoured
        ]
    return findings


def _check(root: Path, files: list[str], rules: str, *extra: str) -> list[Finding]:
    args = [
        *COMMAND,
        "check",
        "--isolated",
        "--no-cache",
        "--preview",
        "--select",
        rules,
        "--output-format",
        "json",
        "--exit-zero",
        *extra,
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
    line = item["location"]["row"]
    advisory = item["code"] in ADVISORY
    return Finding(
        tool="ruff",
        rule=item["code"] or "syntax",
        path=path,
        line=line,
        message=item["message"],
        advisory=advisory,
        # A function-level finding covers the function: an edit inside it shows it.
        end_line=_function_end(root / path, line) if advisory else 0,
    )


def _function_end(file: Path, line: int) -> int:
    try:
        tree = ast.parse(file.read_bytes())
    except (OSError, SyntaxError, ValueError):
        return 0
    ends = [
        node.end_lineno or line
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.lineno == line
    ]
    return max(ends, default=0)
