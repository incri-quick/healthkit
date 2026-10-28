"""Django pack, `soft-delete-read` (slice 008, D-022).

A model whose rows are marked deleted with a flag (`is_deleted` by default) still returns
those rows from `Model.objects` unless its manager hides them. A read that never names the
flag shows deleted records as live. The models are found by reading the project's code
(Python's own parser: nothing is imported or run), never listed by hand, so the rule works
on a project it has never seen.

Measured on QuickRPA history: e938910, f0a3b4e and ac8a630 each fixed such a read.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from healthkit import config, gitdiff
from healthkit.findings import Finding, ToolError, ToolSkipped

if TYPE_CHECKING:
    from pathlib import Path

NAME = "django"
RULE = "soft-delete-read"
# Models live anywhere (gtech-mulearn/mulearnbackend: db/*.py). Only files with a class
# based on a model, manager or queryset are parsed.
_MODEL_CLASS = re.compile(rb"^[ \t]*class \w+\([^)]*(?:Model|Manager|QuerySet)", re.MULTILINE)
_DJANGO_OWN = {"Manager", "BaseManager", "QuerySet"}  # Django's managers never filter
_READS = {"get", "filter"}
_WRITES = {"update", "delete"}
# Ids or names pulled for scoping, never a record acted on (QuickRPA hand-read, slice 008).
_PROJECTIONS = {"values", "values_list"}
_BY_NAME = {"get_object_or_404", "get_list_or_404"}
# Tests and one-off admin scripts read deleted rows on purpose (QuickRPA hand-read).
_NOT_CHECKED = re.compile(r"(?:^|/)management/commands/")
_TEST_FILE = config.TEST_FILE


@dataclass
class _Class:
    bases: list[str]
    fields: set[str] = field(default_factory=set)
    manager: str | None = None  # the class behind `objects = ...`
    queryset_names: set[str] | None = None  # names used in get_queryset, if it has one
    sets: dict[str, set[tuple[str, bool]]] = field(default_factory=dict)  # method: self.x = bool


@dataclass(frozen=True)
class _Soft:
    flag: str
    cleared: frozenset[str]  # fields the delete method sets False: `field=True` is live


def run(root: Path, files: list[str]) -> list[Finding]:
    soft, _ = _soft_delete_models(root)
    findings = []
    for path in files:
        if _TEST_FILE.search(path) or _NOT_CHECKED.search(path):
            continue
        tree = _parse(root, path)
        parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
        for node in ast.walk(tree):
            model, query = _read(node, parents, soft)
            if model and not any(_names_flag(n, soft[model]) for n in ast.walk(query)):
                message = (
                    f"{model} rows can be soft-deleted ({soft[model].flag}); this read does not "
                    f"filter them out"
                )
                findings.append(Finding(NAME, RULE, path, node.lineno, message, advisory=True))
    return findings


def notes(root: Path) -> list[str]:
    """Models that have the flag but a manager healthkit cannot read: said, never hidden."""
    _, unchecked = _soft_delete_models(root)
    if not unchecked:
        return []
    names = ", ".join(sorted(unchecked))
    return [f"django: not checked for {RULE}: {names} (manager from outside the repo)"]


def _read(node: ast.AST, parents: dict, soft: dict[str, _Soft]) -> tuple[str | None, ast.AST]:
    """(model, whole query) when `node` starts a read of a soft-delete model."""
    if isinstance(node, ast.Call) and _name(node.func) in _BY_NAME and node.args:
        model = _name(node.args[0]) if isinstance(node.args[0], ast.Name) else None
        return (model, node) if model in soft else (None, node)
    is_objects = isinstance(node, ast.Attribute) and node.attr == "objects"
    if not (is_objects and isinstance(node.value, ast.Name) and node.value.id in soft):
        return None, node
    top, methods = node, set()
    while True:  # climb the whole chain: Model.objects.select_related(...).get(...)
        parent = parents.get(top)
        if isinstance(parent, ast.Attribute) and parent.value is top:
            methods.add(parent.attr)
        elif not (isinstance(parent, ast.Call) and parent.func is top):
            break
        top = parent
    if not methods & _READS or methods & (_WRITES | _PROJECTIONS):
        return None, node
    return node.value.id, top


def _names_flag(node: ast.AST, soft: _Soft) -> bool:
    def names(text: str | None) -> bool:
        flag = soft.flag
        return text is None or text == flag or text.startswith(f"{flag}__")  # None: **kwargs

    if isinstance(node, ast.keyword):
        live = isinstance(node.value, ast.Constant) and node.value.value is True
        return names(node.arg) or (live and node.arg in soft.cleared)
    return isinstance(node, ast.Constant) and isinstance(node.value, str) and names(node.value)


def _soft_delete_models(root: Path) -> tuple[dict[str, _Soft], list[str]]:
    """{model: flag} for the models to check, and the models whose manager is unreadable."""
    flags = config.load(root).soft_delete_fields
    classes = _classes(root)
    soft, unchecked = {}, []
    for name in classes:
        line = _ancestry(classes, name)
        flag = next((f for cls in line for f in flags if f in cls.fields), None)
        if flag is None:
            continue
        manager = next((cls.manager for cls in line if cls.manager), None)
        hides = _manager_hides(classes, manager, flag)
        if hides is None:
            unchecked.append(name)
        elif not hides:
            deletes = {m for cls in line for m, sets in cls.sets.items() if (flag, True) in sets}
            cleared = {
                attr
                for cls in line
                for method, sets in cls.sets.items()
                if method in deletes
                for attr, value in sets
                if value is False
            }
            soft[name] = _Soft(flag, frozenset(cleared))
    return soft, unchecked


def _classes(root: Path) -> dict[str, _Class]:
    classes: dict[str, _Class] = {}
    settings = config.load(root)
    for path in sorted(gitdiff.project_files(root)):
        if not path.endswith(".py") or _TEST_FILE.search(path) or settings.is_excluded(path):
            continue
        if not _MODEL_CLASS.search((root / path).read_bytes()):
            continue
        for node in _parse(root, path).body:
            if isinstance(node, ast.ClassDef):
                classes.setdefault(node.name, _class(node))
    if not classes:
        msg = "no Django models found"
        raise ToolSkipped(msg)
    return classes


def _ancestry(classes: dict[str, _Class], name: str, seen: frozenset = frozenset()) -> list[_Class]:
    """The class and its bases defined in the repo (outside bases cannot be read)."""
    if name in seen or name not in classes:
        return []
    cls = classes[name]
    return [cls, *(a for base in cls.bases for a in _ancestry(classes, base, seen | {name}))]


def _manager_hides(
    classes: dict[str, _Class], name: str | None, flag: str, seen: frozenset = frozenset()
) -> bool | None:
    """Does this manager filter the flag out? None: it comes from outside the repo."""
    if name is None or name in _DJANGO_OWN:
        return False
    if name in seen or name not in classes:
        return None
    cls = classes[name]
    if cls.queryset_names is not None:
        return any(
            _names_flag(ast.Constant(n), _Soft(flag, frozenset())) for n in cls.queryset_names
        )
    verdicts = [_manager_hides(classes, base, flag, seen | {name}) for base in cls.bases]
    return next((v for v in verdicts if v is not None), None)


def _class(node: ast.ClassDef) -> _Class:
    cls = _Class(bases=[_name(base) for base in node.bases])
    for stmt in node.body:
        target = stmt.targets[0] if isinstance(stmt, ast.Assign) else getattr(stmt, "target", None)
        value = getattr(stmt, "value", None)
        if isinstance(target, ast.Name) and isinstance(value, ast.Call):
            cls.fields.add(target.id)
            if target.id == "objects":
                cls.manager = _manager_class(value)
        if isinstance(stmt, ast.FunctionDef):
            cls.sets[stmt.name] = _self_flags(stmt)
        if isinstance(stmt, ast.FunctionDef) and stmt.name == "get_queryset":
            cls.queryset_names = {
                n.arg if isinstance(n, ast.keyword) else n.value
                for n in ast.walk(stmt)
                if (isinstance(n, ast.keyword) and n.arg)
                or (isinstance(n, ast.Constant) and isinstance(n.value, str))
            }
    return cls


def _self_flags(method: ast.FunctionDef) -> set[tuple[str, bool]]:
    """`self.x = True/False` in a method: how soft_delete() sets the flag and clears others."""
    return {
        (target.attr, assign.value.value)
        for assign in ast.walk(method)
        if isinstance(assign, ast.Assign)
        and isinstance(assign.value, ast.Constant)
        and isinstance(assign.value.value, bool)
        for target in assign.targets
        if isinstance(target, ast.Attribute)
        and isinstance(target.value, ast.Name)
        and target.value.id == "self"
    }


def _manager_class(call: ast.Call) -> str:
    func = call.func
    if isinstance(func, ast.Call):  # Manager.from_queryset(QuerySet)()
        func = func.func.value if isinstance(func.func, ast.Attribute) else func.func
    elif isinstance(func, ast.Attribute) and func.attr == "as_manager":  # QuerySet.as_manager()
        func = func.value
    return _name(func)


def _name(node: ast.AST) -> str:
    if isinstance(node, ast.Attribute):
        return node.attr
    return node.id if isinstance(node, ast.Name) else ""


def _parse(root: Path, path: str) -> ast.Module:
    try:
        return ast.parse((root / path).read_bytes(), filename=path)
    except (OSError, SyntaxError, ValueError) as exc:
        msg = f"could not read {path}: {exc}"
        raise ToolError(msg) from exc
