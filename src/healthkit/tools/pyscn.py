"""pyscn adapter for the module scorecard (slice 018; kept for it in slice 001).

Measured: `analyze --json --output -` writes the report to stdout and nothing into the
project (by default it writes `.pyscn/`); paths come back with the system's separator;
a function's `risk_level` is "high" above complexity 19. About 3 seconds on QuickRPA.
"""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

from healthkit.findings import ToolError

if TYPE_CHECKING:
    from pathlib import Path

NAME = "pyscn"
COMMAND = ["uvx", "pyscn@1.33.0"]


def analyze(root: Path, folders: list[str]) -> dict:
    """The full pyscn report for these folders (relative to root)."""
    args = [*COMMAND, "analyze", "--json", "--output", "-", "--no-open", *folders]
    try:
        result = subprocess.run(args, cwd=root, capture_output=True, check=False)  # noqa: S603
    except OSError as exc:
        msg = f"could not run pyscn: {exc}"
        raise ToolError(msg) from exc
    if result.returncode != 0:
        error = result.stderr.decode("utf-8", "replace").strip()
        msg = f"pyscn failed (exit {result.returncode}): {error}"
        raise ToolError(msg)
    try:
        return json.loads(result.stdout)
    except ValueError as exc:
        msg = "pyscn gave an unreadable report (not JSON)"
        raise ToolError(msg) from exc


def path(raw: str) -> str:
    return raw.replace("\\", "/").removeprefix("./")
