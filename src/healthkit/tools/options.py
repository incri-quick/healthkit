"""`option-never-passed` (slice 015): a function option (a parameter with a default) that
no call in the project ever passes, so its other value is dead code.

Susheel's #23 (AA-09): `complete_login(..., enforce_mfa=True)` and
`apply_password_set(..., blacklist_refresh=True)` were never passed; the "off" paths were a
bypass waiting to be used. Measured on today's QuickRPA: 14 of 20 real (the misses: an SDK
called from outside the repo, signatures a framework dictates), so advisory (D-023).
"""

from __future__ import annotations

import ast
import re
from typing import TYPE_CHECKING

from healthkit import config, gitdiff
from healthkit.findings import Finding, ToolError

if TYPE_CHECKING:
    from pathlib import Path

NAME = "options"
RULE = "option-never-passed"
Call = tuple[set[str], int, bool]  # keywords passed, positional count, uses * or **


def run(root: Path, files: list[str]) -> list[Finding]:
    functions = [
        (path, node)
        for path in files
        if not config.TEST_FILE.search(path)
        for node in ast.walk(_parse(root, path))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("__")
        and _options(node)
    ]
    if not functions:
        return []
    calls = _calls(root, {node.name for _, node in functions})
    findings = []
    for path, node in functions:
        sites = calls.get(node.name, [])
        if not sites or any(star for _, _, star in sites):
            continue  # never called by name (a route, a hook), or unknowable
        for option, position, default in _options(node):
            if any(option in keywords or count > position for keywords, count, _ in sites):
                continue
            message = (
                f"option `{option}` of {node.name}() is never passed by any of its "
                f"{len(sites)} call(s); it is always {ast.unparse(default)}"
            )
            # The signature: adding or changing an option shows it; a body edit does not.
            end = node.body[0].lineno - 1 if node.body[0].lineno > node.lineno else node.lineno
            findings.append(
                Finding(NAME, RULE, path, node.lineno, message, advisory=True, end_line=end)
            )
    return findings


def _options(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[tuple[str, float, ast.expr]]:
    """(name, position or infinity for keyword-only, default) for each parameter with one."""
    args = node.args
    positional = args.posonlyargs + args.args
    first = len(positional) - len(args.defaults)
    found = [
        (arg.arg, i, default)
        for i, (arg, default) in enumerate(zip(positional[first:], args.defaults, strict=True))
    ]
    found = [(name, position + first, default) for name, position, default in found]
    found += [
        (arg.arg, float("inf"), default)
        for arg, default in zip(args.kwonlyargs, args.kw_defaults, strict=True)
        if default is not None
    ]
    return [option for option in found if option[0] not in {"self", "cls"}]


def _calls(root: Path, names: set[str]) -> dict[str, list[Call]]:
    """Every call by these names across the project, tests included (a test is a caller)."""
    settings = config.load(root)
    wanted = re.compile(rb"\b(" + b"|".join(n.encode() for n in names) + rb")\s*\(")
    calls: dict[str, list[Call]] = {}
    for path in gitdiff.project_files(root):
        if not path.endswith(".py") or settings.is_excluded(path):
            continue
        if not wanted.search((root / path).read_bytes()):
            continue
        for node in ast.walk(_parse(root, path)):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            if name in names:
                star = any(isinstance(a, ast.Starred) for a in node.args) or any(
                    k.arg is None for k in node.keywords
                )
                calls.setdefault(name, []).append(
                    ({k.arg for k in node.keywords if k.arg}, len(node.args), star)
                )
    return calls


def _parse(root: Path, path: str) -> ast.Module:
    try:
        return ast.parse((root / path).read_bytes(), filename=path)
    except (OSError, SyntaxError, ValueError) as exc:
        msg = f"could not read {path}: {exc}"
        raise ToolError(msg) from exc
