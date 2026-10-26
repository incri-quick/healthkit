"""import-linter adapter. Text output only.

Exit code 1 means a broken contract OR a configuration error; only the text tells
them apart (captured in slice 003). Long lines wrap, even inside "(l.32, l.963)".
"""

from __future__ import annotations

import configparser
import re
import subprocess
from pathlib import Path

from healthkit.findings import Finding, ToolError, ToolSkipped

NAME = "import-linter"
COMMAND = ["uvx", "--from", "import-linter==2.15", "lint-imports"]
CONTRACT = Path(".healthkit") / "importlinter.ini"
_BROKEN = "Broken contracts"
_LINK = re.compile(r"(?P<importer>[\w.]+) -> (?P<imported>[\w.]+) \(l\.(?P<lines>[^)]*)\)")


def run(root: Path, _files: list[str]) -> list[Finding]:
    if not (root / CONTRACT).is_file():
        msg = f"no {CONTRACT.as_posix()}"
        raise ToolSkipped(msg)
    args = [*COMMAND, "--config", str(CONTRACT), "--no-cache"]
    try:
        result = subprocess.run(args, cwd=root, capture_output=True, check=False)  # noqa: S603
    except OSError as exc:
        msg = f"could not run import-linter: {exc}"
        raise ToolError(msg) from exc
    text = (result.stdout + result.stderr).decode("utf-8", "replace")
    if result.returncode == 0:
        return []
    ids = _contract_ids(root / CONTRACT)
    return [
        Finding(
            tool=NAME,
            rule=ids.get(contract, contract),
            path=_module_path(root, importer),
            line=line,
            message=f"{importer} imports {imported} ({contract})",
        )
        for importer, imported, line, contract in parse_broken_links(text)
    ]


def parse_broken_links(text: str) -> list[tuple[str, str, int, str]]:
    """(importer, imported, line, contract name) for every link in a broken contract."""
    if _BROKEN not in text:
        last = [line for line in text.splitlines() if line.strip()][-1:] or ["no output"]
        msg = f"import-linter could not check: {last[0].strip()}"
        raise ToolError(msg)
    links: list[tuple[str, str, int, str]] = []
    contract = ""
    lines = _unwrap(text.split(_BROKEN, 1)[1].splitlines())
    for index, line in enumerate(lines):
        underline = lines[index + 1] if index + 1 < len(lines) else ""
        # A contract name is underlined with exactly as many dashes as it has characters.
        if line.strip() and underline.strip() == "-" * len(line.strip()):
            contract = line.strip()
        for match in _LINK.finditer(line):
            links += [
                (match["importer"], match["imported"], int(number), contract)
                for number in re.findall(r"\d+", match["lines"])
            ]
    return links


def _unwrap(lines: list[str]) -> list[str]:
    """Join a line to the next while a "(" is still open (terminal-width wrapping)."""
    joined: list[str] = []
    for line in lines:
        if joined and joined[-1].count("(") > joined[-1].count(")"):
            joined[-1] = joined[-1].rstrip() + " " + line.strip()
        else:
            joined.append(line)
    return joined


def _contract_ids(config: Path) -> dict[str, str]:
    parser = configparser.ConfigParser()
    parser.read(config, encoding="utf-8")
    prefix = "importlinter:contract:"
    return {
        parser[section].get("name", section): section.removeprefix(prefix)
        for section in parser.sections()
        if section.startswith(prefix)
    }


def _module_path(root: Path, module: str) -> str:
    base = Path(*module.split("."))
    module_file = base.with_suffix(".py")
    path = module_file if (root / module_file).is_file() else base / "__init__.py"
    return path.as_posix()
