"""`copy-same-name` (slice 011, D-015): a private helper this branch adds or changes that is
also defined at module level in other files.

Measured before building: similarity tools (pylint, jscpd, healthkit's own normalised
comparison) found only exact copies; QuickRPA's drifted `_get_workspace_or_404` (arguments
swapped, a different access check) scored 0.02. Its name found all 9 copies. Advisory
(D-023): a shared name is a question, not proof of a copy.
"""

from __future__ import annotations

import ast
import re
from typing import TYPE_CHECKING

from healthkit import config, gitdiff
from healthkit.findings import Finding, ToolError

if TYPE_CHECKING:
    from pathlib import Path

NAME = "copies"
RULE = "copy-same-name"
SHOWN = 5  # other files named in the message


def run(root: Path, files: list[str]) -> list[Finding]:
    mine = {
        (path, node.name): node
        for path in files
        if not config.TEST_FILE.search(path)
        for node in _helpers(_parse(root, path))
    }
    if not mine:
        return []
    others = _definitions(root, {name for _, name in mine})
    findings = []
    for (path, name), node in sorted(mine.items()):
        elsewhere = sorted((p, shape) for p, shape in others.get(name, []) if p != path)
        if not elsewhere:
            continue
        versions = len({_shape(node)} | {shape for _, shape in elsewhere})
        names = [p for p, _ in elsewhere]
        listed = ", ".join(names[:SHOWN]) + (", ..." if len(names) > SHOWN else "")
        message = (
            f"{name} is also defined in {len(names)} other file(s), "
            f"{versions} different version(s): {listed}"
        )
        end = node.end_lineno or node.lineno
        finding = Finding(NAME, RULE, path, node.lineno, message, advisory=True, end_line=end)
        findings.append(finding)
    return findings


def _definitions(root: Path, names: set[str]) -> dict[str, list[tuple[str, str]]]:
    """Every module-level definition of these names in the project, with its shape."""
    settings = config.load(root)
    wanted = re.compile(
        rb"^(?:async )?def (" + b"|".join(n.encode() for n in names) + rb")\(", re.MULTILINE
    )
    found: dict[str, list[tuple[str, str]]] = {}
    for path in gitdiff.project_files(root):
        if not path.endswith(".py") or config.TEST_FILE.search(path) or settings.is_excluded(path):
            continue
        if not wanted.search((root / path).read_bytes()):
            continue
        for node in _helpers(_parse(root, path)):
            if node.name in names:
                found.setdefault(node.name, []).append((path, _shape(node)))
    return found


def _helpers(tree: ast.Module) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Private module-level functions: `_name`, never `__dunder__`."""
    return [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("_")
        and not node.name.startswith("__")
    ]


def _shape(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Arguments and body, without the docstring: two copies with one shape are identical."""
    body = node.body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        body = body[1:]
    return ast.dump(node.args) + "".join(ast.dump(statement) for statement in body)


def _parse(root: Path, path: str) -> ast.Module:
    try:
        return ast.parse((root / path).read_bytes(), filename=path)
    except (OSError, SyntaxError, ValueError) as exc:
        msg = f"could not read {path}: {exc}"
        raise ToolError(msg) from exc
