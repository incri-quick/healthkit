"""`healthkit routes`: API routes no client calls (slice 010, D-022).

Routes come from OpenAPI descriptions (any backend language); callers are folders of
client code, read as text, never run. A route is called when a string in a caller ends
with its path: `/api/v1/robots/{pk}/run/` is called by `` `robots/${id}/run/` ``. The
base prefix (`/api/v1`) may live elsewhere, so only the end must match.

Measured on QuickRPA (slice 010): clients name the method beside the path in only about
29% of path strings, so routes are matched per path, never per method. Comments and docs
do not count: AA-61's `/token-encrypted/` survived only in a comment.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

from healthkit import config, gitdiff
from healthkit.findings import Finding, ToolError

RULE = "route-no-caller"
METHODS = ("get", "post", "put", "patch", "delete")
CODE = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue", ".py", ".sh", ".ps1"}
SKIP_DIRS = {"node_modules", "dist", "build", "coverage", "__tests__", "tests", "test", "venv"}
_TEST_FILE = re.compile(r"\.(?:test|spec)\.[jt]sx?$|^test_.*\.py$|_test\.py$")
# JS/shell `${x}`, Python `{x}`, `%s`, PowerShell/shell `$x` and `$(x)`, Windows `%X%`.
_PLACEHOLDER = re.compile(r"\$\{[^}]*\}|\{[^}]*\}|%\(\w+\)[sd]|%[sd]|\$\([^)]*\)|\$\w+|%\w+%")
_ASSIGN = re.compile(r"(?:\b(?:const|let|var)\s+|^[ \t]*)(\w+)\s*=\s*[fr]?(?=['\"`])", re.MULTILINE)
_RESOLVE = re.compile(r"\$?\{(\w+)\}")
_JOIN = re.compile(r"\s*\+\s*[^'\"`;\n]+?\s*\+\s*")  # "a/" + id + "/b"
_TRAILING = re.compile(r"\s*\+\s*[\w$.()\[\]]+")  # "robots/" + id


def add_parser(commands) -> None:  # noqa: ANN001 - argparse's private subparsers type
    cmd = commands.add_parser("routes", help="list API routes no client calls")
    cmd.add_argument("--schema", action="append", required=True, help="OpenAPI URL or file")
    cmd.add_argument("--callers", action="append", required=True, help="folder of client code")


def run(args) -> int:  # noqa: ANN001 - argparse.Namespace
    try:
        routes, bases = _routes(args.schema)
        callers, files = _caller_paths(args.callers)
    except ToolError as exc:
        print(f"healthkit routes: {exc}", file=sys.stderr)
        return 2
    try:
        settings = config.load(gitdiff.repo_root(Path.cwd()))
    except gitdiff.GitError:
        settings = config.Settings()
    except config.ConfigError as exc:
        print(f"healthkit routes: {exc}", file=sys.stderr)
        return 2
    called = _called(bases, callers)
    shown, allowed = [], 0
    for path, methods in sorted(routes.items()):
        if path in called:
            continue
        finding = Finding("routes", RULE, path, 0, "no known caller")
        if settings.allows(finding):
            allowed += 1
            continue
        shown.append(path)
        print(f"no caller: {', '.join(m.upper() for m in methods)} {path}")
    summary = (
        f"{len(shown)} of {len(routes)} path(s) have no known caller in {files} client file(s)"
    )
    parts = [f"healthkit routes: {summary}", "matched per path, not per method"]
    parts += [f"allowed: {allowed}"] if allowed else []
    print(" | ".join(parts))
    return 1 if shown else 0


def _routes(schemas: list[str]) -> tuple[dict[str, list[str]], dict[str, int]]:
    routes: dict[str, list[str]] = {}
    bases: dict[str, int] = {}
    for source in schemas:
        try:
            if "://" in source:
                with urllib.request.urlopen(source, timeout=30) as reply:  # noqa: S310 - the user's own API
                    data = json.load(reply)
            else:
                data = json.loads(Path(source).read_text(encoding="utf-8-sig"))
            paths = data["paths"]
        except (OSError, ValueError, KeyError, TypeError) as exc:
            msg = f"could not read the schema {source}: {exc}"
            raise ToolError(msg) from exc
        base = _base(list(paths))
        for path, item in paths.items():
            routes.setdefault(path, []).extend(m for m in METHODS if m in item)
            bases[path] = base
    return routes, bases


def _base(paths: list[str]) -> int:
    """Leading segments every path of one API shares (`/api/v1`): its base."""
    split = [[s for s in p.split("/") if s] for p in paths]
    shortest = min((len(s) for s in split), default=1)
    n = 0
    while n < shortest - 1 and "{" not in split[0][n] and all(s[n] == split[0][n] for s in split):
        n += 1
    return n


Callers = dict[str, list[tuple[list[str], bool]]]  # last segment -> (segments, anchored)


def _caller_paths(folders: list[str]) -> tuple[Callers, int]:
    """Every path-like string in the callers, indexed by its last segment."""
    index: Callers = {}
    total = 0
    for folder in folders:
        files = list(_code_files(Path(folder)))
        if not files:
            msg = f"no client files in {folder} (missing, empty, or no code files)"
            raise ToolError(msg)
        total += len(files)
        for file in files:
            text = file.read_bytes().decode("utf-8", "replace")
            constants = _constants(text)
            for raw in _strings(text, hash_comments=file.suffix in {".py", ".sh", ".ps1"}):
                # Placeholders first: `${force ? '?force=true' : ''}` holds spaces.
                literal = _PLACEHOLDER.sub("{}", _resolve(raw, constants))
                for token in literal.split():  # a URL inside a command line (install.sh)
                    if found := _skeleton(token):
                        index.setdefault(found[0][-1], []).append(found)
    return index, total


def _constants(text: str) -> dict[str, str]:
    """`const vaultPath = `/api/v1/vault/${id}`` and `path = f"/bot/x/"`: the first value of
    each name in one file, so `${vaultPath}/vaults` can be read (slice 010 sample)."""
    values: dict[str, str] = {}
    for match in _ASSIGN.finditer(text):
        end = _string_end(text, match.end())
        values.setdefault(match[1], text[match.end() + 1 : end - 1])
    return values


def _resolve(literal: str, constants: dict[str, str]) -> str:
    return _RESOLVE.sub(lambda m: constants.get(m[1], m[0]), literal)


def _code_files(folder: Path):  # noqa: ANN202 - a generator of Paths
    if folder.is_file():  # one file can be a caller: a bot template inside the backend
        yield from [folder] if folder.suffix in CODE else []
        return
    for parent, dirs, names in os.walk(folder):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for name in names:
            if Path(name).suffix in CODE and not _TEST_FILE.search(name):
                yield Path(parent) / name


def _strings(text: str, *, hash_comments: bool) -> list[str]:
    """String literals, comments skipped; `"a/" + x + "/b"` joined as `a/{}/b`."""
    found: list[tuple[int, int, str]] = []
    inside: list[str] = []  # quoted strings inside ''' code templates (bot_export.py)
    i, n = 0, len(text)
    while i < n:
        two = text[i : i + 2]
        if (two == "//" and not hash_comments) or (text[i] == "#" and hash_comments):
            end = text.find("\n", i)
            i = n if end < 0 else end
        elif two == "/*" and not hash_comments:
            end = text.find("*/", i + 2)
            i = n if end < 0 else end + 2
        elif hash_comments and text[i : i + 3] in {'"""', "'''"}:
            # Prose in a docstring is not a caller; code kept in a template quotes its URLs.
            end = text.find(text[i : i + 3], i + 3)
            end = n if end < 0 else end
            inside += _strings(text[i + 3 : end], hash_comments=True)
            i = end + 3
        elif text[i] in "'\"`":
            end = _string_end(text, i)
            found.append((i, end, text[i + 1 : end - 1]))
            i = end
        else:
            i += 1
    joined: list[str] = []
    for k, (start, end, body) in enumerate(found):
        between = text[found[k - 1][1] : start] if k else ""
        if k and _JOIN.fullmatch(between):
            joined[-1] += "{}" + body
        else:
            joined.append(body)
        if _TRAILING.match(text, end) and not (
            k + 1 < len(found) and _JOIN.fullmatch(text[end : found[k + 1][0]])
        ):
            joined[-1] += "{}"
    return joined + inside


def _string_end(text: str, start: int) -> int:
    quote, i = text[start], start + 1
    while i < len(text):
        char = text[i]
        if char == "\\":
            i += 2
            continue
        if char == quote:
            return i + 1
        if char == "\n" and quote != "`":  # ' and " end at the line: a stray quote is harmless
            return i
        i += 1
    return len(text)


def _skeleton(token: str) -> tuple[list[str], bool] | None:
    """`${base}/api/v1/robots/${id}/run/?x=1` -> (["api", "v1", "robots", "{}", "run"], False).

    Anchored (True) when the path starts with fixed text: it then sits right below the API
    base. A path that starts with a variable may follow any prefix (`${vaultPath}/x`).
    """
    if "/" not in token:
        return None
    # Drop scheme and host, even when they are variables: `${scheme}://${baseUrl}/agent/v1/x`.
    text = re.sub(r"^[^/]*://[^/]*", "", _PLACEHOLDER.sub("{}", token))
    text = re.sub(r"(?:\{\})+", "{}", text.split("?")[0].split("#")[0])
    segments = [s for s in text.split("/") if s]
    anchored = not (segments and segments[0] == "{}")
    while segments and segments[0] == "{}":
        segments.pop(0)
    if not any(re.search(r"[A-Za-z]", s) for s in segments):
        return None
    return segments, anchored


def _called(bases: dict[str, int], callers: Callers) -> set[str]:
    """Routes some caller names.

    An anchored caller names the route right below its API's base, optionally with the end
    of the base: `/logout/` is /api/v1/logout/, never /api/v1/auth/logout (AA-61
    measurement). A caller after a variable prefix only has to match a route's end, so it
    counts only when that end fits exactly one route: the agent's
    `{self._auth_base()}/logout` is Supabase's API, not either of ours. `/x/{slug}` and
    `/x/{slug}/` are one route spelled twice, not two.
    """
    called: set[str] = set()
    loose: dict[tuple[str, ...], set[str]] = {}
    shape = {path: tuple(_PLACEHOLDER.sub("{}", s) for s in path.split("/") if s) for path in bases}
    for path, base in bases.items():
        route = list(shape[path])
        below = len(route) - base
        for caller, anchored in callers.get(route[-1], []) + callers.get("{}", []):
            extra = len(caller) - below
            fits = 0 <= extra <= base if anchored else len(caller) <= len(route)
            start = base - extra if anchored else len(route) - len(caller)
            if not fits or not all(
                c in ("{}", r) for c, r in zip(caller, route[start:], strict=True)
            ):
                continue
            if anchored:
                called.add(path)
            else:
                loose.setdefault(tuple(caller), set()).add(path)
    for caller, paths in loose.items():
        # Prefer routes whose parameters line up with the caller's: `.../nodes/${node.id}`
        # names /nodes/{node_id}, not /nodes/bulk-delete (slice 010 third sample).
        exact = {p for p in paths if shape[p][len(shape[p]) - len(caller) :] == caller}
        if len({shape[p] for p in exact or paths}) == 1:
            called.update(exact or paths)
    return called
