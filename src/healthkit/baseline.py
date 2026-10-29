"""The baseline (slice 012): today's findings, remembered so that only new ones show.

A finding is remembered by tool, rule, file and the text of its line, never the line
number: code that moves keeps its match. Counts make a second copy of a remembered line
new. The file lives in `.healthkit/`, so changing it needs a person's approval (D-018).
"""

from __future__ import annotations

import json
from collections import Counter
from typing import TYPE_CHECKING

from healthkit.config import HOME, ConfigError

if TYPE_CHECKING:
    from pathlib import Path

    from healthkit.findings import Finding

FILE = HOME / "baseline.json"
Key = tuple[str, str, str, str]  # tool, rule, path, line text


def load(root: Path) -> Counter[Key]:
    file = root / FILE
    if not file.is_file():
        return Counter()
    try:
        data = json.loads(file.read_bytes())
        return Counter(
            {
                (e["tool"], e["rule"], e["path"], e["text"]): int(e["count"])
                for e in data["findings"]
            }
        )
    except (ValueError, KeyError, TypeError) as exc:
        msg = f"{FILE.as_posix()} cannot be read ({exc}); fix it or write a new baseline"
        raise ConfigError(msg) from exc


def save(root: Path, findings: list[Finding], scanned: set[str]) -> None:
    """Remember these findings; entries for files outside `scanned` are kept."""
    kept = Counter({key: n for key, n in load(root).items() if key[2] not in scanned})
    known = kept + Counter(_key(root, f) for f in findings)
    entries = [
        {"tool": t, "rule": r, "path": p, "text": x, "count": n}
        for (t, r, p, x), n in sorted(known.items())
    ]
    text = json.dumps({"version": 1, "findings": entries}, indent=2) + "\n"
    (root / FILE).parent.mkdir(exist_ok=True)
    (root / FILE).write_bytes(text.encode("utf-8"))  # never CRLF (L-011)


def split(
    root: Path, findings: list[Finding], known: Counter[Key], scanned: set[str] | None = None
) -> tuple[list[Finding], int, int]:
    """(new findings, how many were remembered, how many remembered are gone).

    "Gone" is counted only for files that were fully scanned: `review` sees changed lines
    only, so it cannot tell a fixed finding from one it did not look at.
    """
    left = Counter(known)
    new, remembered = [], 0
    for finding in findings:
        key = _key(root, finding)
        if left[key] > 0:
            left[key] -= 1
            remembered += 1
        else:
            new.append(finding)
    gone = sum(n for key, n in left.items() if scanned is not None and key[2] in scanned)
    return new, remembered, gone


def _key(root: Path, finding: Finding) -> Key:
    return finding.tool, finding.rule, finding.path, _line(root, finding.path, finding.line)


def _line(root: Path, path: str, number: int) -> str:
    try:
        lines = (root / path).read_bytes().decode("utf-8", "replace").splitlines()
    except OSError:
        return ""
    return lines[number - 1].strip() if 0 < number <= len(lines) else ""
