"""`healthkit scorecard`: one row of facts per module, no invented grade (slice 018).

Measured: pyscn's per-module grade hid what matters (QuickRPA's `studio_workflow`, 44,716
lines and 42 too-complex functions, scored the same B as a 2,618-line module), so the card
shows counts, worst first, and pyscn's overall score only as one trend line.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

from healthkit import config
from healthkit.tools import pyscn

if TYPE_CHECKING:
    from pathlib import Path

    from healthkit.findings import Finding


@dataclass
class Row:
    module: str
    files: int = 0
    lines: int = 0
    too_complex: int = 0
    most_complex: dict | None = None  # {"name", "complexity"}; None: no function
    problems: int = 0
    hints: int = 0


def build(root: Path, folders: list[str], files: set[str], findings: list[Finding]) -> dict:
    """Rows for the modules of `files`, from one pyscn run plus healthkit's findings.

    Files and lines come from healthkit's own list: pyscn skipped some folders (QuickRPA's
    `docs/`, `.claude/`), which left rows with 0 files beside real findings."""
    data = pyscn.analyze(root, folders)
    rows: dict[str, Row] = {}

    def row(path: str) -> Row | None:
        return rows.setdefault(_module(path), Row(_module(path))) if path in files else None

    for path in sorted(files):
        found = row(path)
        found.files += 1
        text = (root / path).read_bytes().decode("utf-8", "replace")
        found.lines += sum(1 for line in text.splitlines() if line.strip())
    for function in data.get("complexity", {}).get("functions", []):
        if function.get("scope_kind") == "module":
            continue  # a file's top-level code, reported as "<module>": not a function
        if found := row(pyscn.path(function["file_path"])):
            complexity = function["metrics"]["complexity"]
            found.too_complex += function["risk_level"] == "high"
            if complexity > (found.most_complex or {"complexity": 0})["complexity"]:
                found.most_complex = {"name": function["name"], "complexity": complexity}
    for finding in findings:
        if not finding.suppressed and (found := row(finding.path)):
            found.hints += finding.advisory
            found.problems += not finding.advisory
    ordered = sorted(rows.values(), key=lambda r: (-r.too_complex, -r.problems, -r.lines))
    summary = data.get("summary", {})
    overall = {"health_score": summary.get("health_score"), "grade": summary.get("grade")}
    return {"overall": overall, "modules": [asdict(r) for r in ordered]}


def emit(card: dict, fmt: str) -> None:
    if fmt != "text" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # machine formats are UTF-8 (slice 017)
    if fmt == "json":
        print(json.dumps(card, indent=2))
        return
    head = ["Module", "Files", "Lines", "Too complex", "Most complex", "Problems", "Hints"]
    rows = [
        [
            m["module"],
            str(m["files"]),
            str(m["lines"]),
            str(m["too_complex"]),
            _most(m["most_complex"]),
            str(m["problems"]),
            str(m["hints"]),
        ]
        for m in card["modules"]
    ]
    overall = card["overall"]
    trend = f"overall (pyscn): {overall['health_score']} ({overall['grade']})"
    if fmt == "markdown":
        lines = [f"| {' | '.join(head)} |", f"|{'---|' * len(head)}"]
        lines += [f"| {' | '.join(r)} |" for r in rows]
        print("\n".join(["## healthkit scorecard", "", *lines, "", trend]))
        return
    widths = [max(len(c) for c in col) for col in zip(head, *rows, strict=False)]
    for line in (head, *rows):
        print("  ".join(cell.ljust(width) for cell, width in zip(line, widths, strict=True)))
    print(trend)


def _most(most: dict | None) -> str:
    return f"{most['name']} ({most['complexity']})" if most else "-"


def _module(path: str) -> str:
    """The first folder of a path; files at the top of the repo are "(top)"."""
    first, _, rest = path.partition("/")
    return first if rest else "(top)"


def app_files(files: set[str]) -> set[str]:
    """Application code only: test files read and copy things on purpose."""
    return {path for path in files if not config.TEST_FILE.search(path)}
