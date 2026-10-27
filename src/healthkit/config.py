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
# Generated migrations (slice 002 false alarms) and the referee's own files.
DEFAULT_EXCLUDE = ("**/migrations/**", ".healthkit/**")
_TOP_KEYS = {"exclude", "allow"}
_ALLOW_KEYS = {"rule", "path", "reason"}


class ConfigError(Exception):
    """The project's settings cannot be trusted, so nothing is checked (exit 2)."""


@dataclass(frozen=True)
class Allow:
    rule: str
    path: str
    reason: str


@dataclass(frozen=True)
class Settings:
    exclude: tuple[str, ...] = DEFAULT_EXCLUDE
    allow: tuple[Allow, ...] = ()

    def is_excluded(self, path: str) -> bool:
        return any(glob_match(path, pattern) for pattern in self.exclude)

    def allows(self, finding: Finding) -> bool:
        return any(a.rule == finding.rule and glob_match(finding.path, a.path) for a in self.allow)


def load(root: Path) -> Settings:
    file = root / CONFIG
    if not file.is_file():
        return Settings()
    try:
        data = tomllib.loads(file.read_text(encoding="utf-8-sig"))  # Windows editors add a BOM
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        msg = f"{CONFIG.as_posix()}: {exc}"
        raise ConfigError(msg) from exc
    _no_unknown_keys(data, _TOP_KEYS, CONFIG.as_posix())
    exclude = [_path(p, "exclude") for p in _list(data.get("exclude", []), "exclude")]
    allow = [_allow(entry) for entry in _list(data.get("allow", []), "allow")]
    return Settings(exclude=DEFAULT_EXCLUDE + tuple(exclude), allow=tuple(allow))


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
    parts = re.split(r"(\*\*/|/\*\*|\*\*|\*|\?)", pattern)
    tokens = {"**/": "(?:.*/)?", "/**": "(?:/.*)?", "**": ".*", "*": "[^/]*", "?": "[^/]"}
    return re.compile("".join(tokens.get(part, re.escape(part)) for part in parts))
