"""codespell adapter: clear-cut typos, advisory (slice 014, D-023).

Measured (slice 014): with the `clear` dictionary and words of 4+ letters, about 80% of
reports are real typos; short variable names (`nd`, `ot`) and valid variants (`re-used`,
`unparseable`) were the noise. Exit 65 means typos found, 0 none; a missing file is also
0 with no output, so only existing files are ever passed. The accept list is
case-sensitive: words are lowercased.
"""

from __future__ import annotations

import re
import subprocess
from typing import TYPE_CHECKING

from healthkit import config
from healthkit.findings import Finding, ToolError

if TYPE_CHECKING:
    from pathlib import Path

NAME = "codespell"
RULE = "spelling"
COMMAND = ["uvx", "codespell@2.4.1"]
ACCEPTED = ("unparseable",)  # a recognised spelling it flags
MIN_LENGTH = 4  # shorter "typos" were variable names (nd, ot, ser)
_HYPHENATED = r"\b\w+(?:-\w+)+\b"  # re-used, pre-empts: style variants, not typos
_FOUND = 65
_LINE = re.compile(r"^(?P<path>.+?):(?P<line>\d+): (?P<word>\S+) ==> (?P<fix>.+)$")
_BATCH = 200


def run(root: Path, files: list[str]) -> list[Finding]:
    accepted = ",".join(w.lower() for w in (*ACCEPTED, *config.load(root).spelling_ignore))
    present = [path for path in files if (root / path).is_file()]
    findings = []
    for start in range(0, len(present), _BATCH):
        args = [*COMMAND, "--builtin", "clear", "--quiet-level", "2"]
        args += ["--ignore-regex", _HYPHENATED, "-L", accepted, *present[start : start + _BATCH]]
        try:
            result = subprocess.run(args, cwd=root, capture_output=True, check=False)  # noqa: S603
        except OSError as exc:
            msg = f"could not run codespell: {exc}"
            raise ToolError(msg) from exc
        if result.returncode not in (0, _FOUND):
            error = result.stderr.decode("utf-8", "replace").strip()
            msg = f"codespell failed (exit {result.returncode}): {error}"
            raise ToolError(msg)
        for line in result.stdout.decode("utf-8", "replace").splitlines():
            match = _LINE.match(line.strip())
            if match and len(match["word"]) >= MIN_LENGTH:
                path = match["path"].replace("\\", "/")
                message = f"'{match['word']}' looks misspelt; did you mean {match['fix']}?"
                finding = Finding(NAME, RULE, path, int(match["line"]), message, advisory=True)
                findings.append(finding)
    return findings
