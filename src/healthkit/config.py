"""Project settings from `.healthkit/config.toml` (slice 004).

Strict on purpose: an unknown key or an allow entry without a reason is an error. A
typo must never silently switch a setting off, and an exception needs a written reason.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from healthkit.findings import Finding

HOME = Path(".healthkit")
CONFIG = HOME / "config.toml"
PROJECT_RULES = HOME / "rules"
# Generated Django migrations only (slice 002 false alarms), by their NNNN_ names: real
# code placed in a migrations folder is still reviewed (slice 005, D-019). And the
# referee's own files.
DEFAULT_EXCLUDE = ("**/migrations/[0-9][0-9][0-9][0-9]_*.py", ".healthkit/**")
# Python test files by the usual conventions: checks about runtime code skip them (they
# read deleted rows, copy helpers, on purpose). Slices 008 and 011.
TEST_FILE = re.compile(
    r"(?:^|/)(?:tests?/|tests?(?:_[^/]*)?\.py$|test_[^/]*\.py$|[^/]*_tests?\.py$)"
)
_TOP_KEYS = {"exclude", "allow", "check", "django", "ruff", "spelling"}
_ALLOW_KEYS = {"rule", "path", "reason"}
_CHECK_KEYS = {"name", "command", "paths", "reason", "timeout"}
_DJANGO_KEYS = {"soft_delete_fields"}
_RUFF_KEYS = {"extra"}
_SPELLING_KEYS = {"ignore"}
_WORD = re.compile(r"[A-Za-z][A-Za-z'-]*")
_RULE_CODE = re.compile(r"[A-Z]{1,4}[0-9]{0,4}")  # "D1", "ANN", "PLR2004"


class ConfigError(Exception):
    """The project's settings cannot be trusted, so nothing is checked (exit 2)."""


@dataclass(frozen=True)
class Allow:
    rule: str
    path: str
    reason: str


@dataclass(frozen=True)
class Check:
    """A project's own guard command (slice 008). Run from the BASE branch's config only."""

    name: str
    command: tuple[str, ...]
    paths: tuple[str, ...]
    reason: str
    timeout: int = 300


@dataclass(frozen=True)
class Settings:
    exclude: tuple[str, ...] = DEFAULT_EXCLUDE
    allow: tuple[Allow, ...] = ()
    checks: tuple[Check, ...] = ()
    soft_delete_fields: tuple[str, ...] = ("is_deleted",)
    ruff_extra: tuple[str, ...] = ()  # ruff checks the project chose (slice 013)
    spelling_ignore: tuple[str, ...] = ()  # words the project accepts (slice 014)

    def is_excluded(self, path: str) -> bool:
        return any(glob_match(path, pattern) for pattern in self.exclude)

    def allows(self, finding: Finding) -> bool:
        return any(a.rule == finding.rule and glob_match(finding.path, a.path) for a in self.allow)


def load(root: Path) -> Settings:
    file = root / CONFIG
    if not file.is_file():
        return Settings()
    try:
        return parse(file.read_text(encoding="utf-8-sig"))  # Windows editors add a BOM
    except UnicodeDecodeError as exc:
        msg = f"{CONFIG.as_posix()}: {exc}"
        raise ConfigError(msg) from exc


def parse(text: str | None) -> Settings:
    if text is None:
        return Settings()
    try:
        data = tomllib.loads(text.removeprefix("\ufeff"))
    except tomllib.TOMLDecodeError as exc:
        msg = f"{CONFIG.as_posix()}: {exc}"
        raise ConfigError(msg) from exc
    _no_unknown_keys(data, _TOP_KEYS, CONFIG.as_posix())
    exclude = [_path(p, "exclude") for p in _list(data.get("exclude", []), "exclude")]
    allow = [_allow(entry) for entry in _list(data.get("allow", []), "allow")]
    checks = [_check(entry) for entry in _list(data.get("check", []), "check")]
    django = _table(data, "django", _DJANGO_KEYS)
    fields = _list(django.get("soft_delete_fields", ["is_deleted"]), "soft_delete_fields")
    extra = _list(_table(data, "ruff", _RUFF_KEYS).get("extra", []), "extra")
    if bad := [
        code for code in extra if not isinstance(code, str) or not _RULE_CODE.fullmatch(code)
    ]:
        msg = f'{CONFIG.as_posix()}: [ruff] extra must be ruff rule codes like "D1": {bad}'
        raise ConfigError(msg)
    words = _list(_table(data, "spelling", _SPELLING_KEYS).get("ignore", []), "ignore")
    if bad := [w for w in words if not isinstance(w, str) or not _WORD.fullmatch(w)]:
        msg = f"{CONFIG.as_posix()}: [spelling] ignore must be a list of words: {bad}"
        raise ConfigError(msg)
    return Settings(
        exclude=DEFAULT_EXCLUDE + tuple(exclude),
        allow=tuple(allow),
        checks=tuple(checks),
        soft_delete_fields=tuple(_text(f, "soft_delete_fields") for f in fields),
        ruff_extra=tuple(extra),
        spelling_ignore=tuple(words),
    )


def _table(data: dict, name: str, known: set[str]) -> dict:
    table = data.get(name, {})
    if not isinstance(table, dict):
        msg = f"{CONFIG.as_posix()}: [{name}] must be a table"
        raise ConfigError(msg)
    _no_unknown_keys(table, known, f"[{name}]")
    return table


def _check(entry: object) -> Check:
    if not isinstance(entry, dict):
        msg = f"{CONFIG.as_posix()}: each [[check]] entry must be a table"
        raise ConfigError(msg)
    where = f"[[check]] {entry.get('name')!r}"
    _no_unknown_keys(entry, _CHECK_KEYS, where)
    for key in ("name", "reason"):
        _text(entry.get(key), f"{where}: '{key}'")
    command = entry.get("command")
    if not isinstance(command, list) or not command:  # never a shell string
        msg = f"{CONFIG.as_posix()}: {where}: 'command' must be a list of arguments"
        raise ConfigError(msg)
    timeout = entry.get("timeout", 300)
    if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
        msg = f"{CONFIG.as_posix()}: {where}: 'timeout' must be a positive number of seconds"
        raise ConfigError(msg)
    return Check(
        name=entry["name"].strip(),
        command=tuple(_text(arg, f"{where}: 'command'") for arg in command),
        paths=tuple(_path(p, "paths") for p in _list(entry.get("paths", ["**"]), "paths")),
        reason=entry["reason"].strip(),
        timeout=timeout,
    )


def _text(value: object, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        msg = f"{CONFIG.as_posix()}: {where} must be non-empty text"
        raise ConfigError(msg)
    return value


def _allow(entry: object) -> Allow:
    if not isinstance(entry, dict):
        msg = f"{CONFIG.as_posix()}: each [[allow]] entry must be a table"
        raise ConfigError(msg)
    where = f"[[allow]] {entry.get('rule')!r} for {entry.get('path')!r}"
    _no_unknown_keys(entry, _ALLOW_KEYS, where)
    for key in ("rule", "path", "reason"):
        if not isinstance(entry.get(key), str) or not entry[key].strip():
            msg = f"{CONFIG.as_posix()}: {where}: '{key}' must be non-empty text"
            raise ConfigError(msg)
    return Allow(entry["rule"].strip(), _path(entry["path"], "allow"), entry["reason"].strip())


def _no_unknown_keys(table: dict, known: set[str], where: str) -> None:
    if unknown := sorted(set(table) - known):
        msg = f"{CONFIG.as_posix()}: unknown key(s) {', '.join(unknown)} in {where}"
        raise ConfigError(msg)


def _list(value: object, key: str) -> list:
    if not isinstance(value, list):
        msg = f"{CONFIG.as_posix()}: '{key}' must be a list"
        raise ConfigError(msg)
    return value


def _path(value: object, key: str) -> str:
    if not isinstance(value, str) or not value.strip():
        msg = f"{CONFIG.as_posix()}: '{key}' paths must be non-empty text"
        raise ConfigError(msg)
    return value.strip().replace("\\", "/")


def glob_match(path: str, pattern: str) -> bool:
    """`*` stays inside one folder; `**` crosses folders (also zero of them)."""
    return _glob_regex(pattern).fullmatch(path) is not None


@cache
def _glob_regex(pattern: str) -> re.Pattern[str]:
    parts = re.split(r"(\*\*/|/\*\*|\*\*|\*|\?|\[!?[^\]/]+\])", pattern)
    tokens = {"**/": "(?:.*/)?", "/**": "(?:/.*)?", "**": ".*", "*": "[^/]*", "?": "[^/]"}
    return re.compile("".join(tokens.get(part, _literal_or_class(part)) for part in parts))


def _literal_or_class(part: str) -> str:
    """`[0-9]` and `[!0-9]` are character classes (never matching "/"); the rest is literal."""
    if len(part) > 2 and part[0] == "[" and part[-1] == "]":  # noqa: PLR2004 - "[x]" is 3+ chars
        body = part[1:-1]
        negate = body.startswith("!")
        body = re.escape(body.removeprefix("!")).replace(r"\-", "-")
        return f"[^/{body}]" if negate else f"[{body}]"
    return re.escape(part)
