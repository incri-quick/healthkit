"""Which lines did a branch add or change? Read from `git diff --unified=0`."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

# git ends the path with a TAB when it contains a space ("+++ b/Bot Starter Kit/x.py\t").
_NEW_FILE = re.compile(r"^\+\+\+ (?:b/(?P<path>.*?)|/dev/null)\t?$")
_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(?P<start>\d+)(?:,(?P<count>\d+))? @@")


class GitError(Exception):
    """git could not answer: not a repository, or an unknown ref."""


def parse_changed_lines(diff: str) -> dict[str, set[int]]:
    """Map each file to the line numbers, in the new version, that the diff adds or changes."""
    changed: dict[str, set[int]] = {}
    path: str | None = None
    for line in diff.splitlines():
        if file_match := _NEW_FILE.match(line):
            path = file_match["path"]  # None for a deleted file
        elif (hunk := _HUNK.match(line)) and path is not None:
            start, count = int(hunk["start"]), int(hunk["count"] or 1)
            if count:  # count 0 is a pure deletion
                changed.setdefault(path, set()).update(range(start, start + count))
    return changed


def _git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(  # noqa: S603 - argument list, no shell; --base cannot inject
            ["git", "-c", "core.quotepath=false", *args],  # noqa: S607 - git from PATH by design
            cwd=root,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as exc:
        msg = "git is not installed or not on PATH"
        raise GitError(msg) from exc
    if result.returncode != 0:
        raise GitError(result.stderr.decode("utf-8", "replace").strip())
    return result.stdout.decode("utf-8", "surrogateescape")


def repo_root(start: Path) -> Path:
    try:
        return Path(_git(start, "rev-parse", "--show-toplevel").strip())
    except GitError as exc:
        msg = f"not a git repository: {start}"
        raise GitError(msg) from exc


def changed_lines(root: Path, base: str) -> dict[str, set[int]]:
    """Lines changed on this branch since it left `base` (committed changes only)."""
    try:
        _git(root, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}")
    except GitError as exc:
        msg = f"unknown base: {base}"
        raise GitError(msg) from exc
    diff = _git(
        root,
        "diff",
        "--unified=0",
        "--no-color",
        "--no-ext-diff",
        # A branch's own .gitattributes (binary, -diff, a textconv driver) could otherwise
        # make its changes show no lines at all: "nothing to review", exit 0 (slice 005).
        "--text",
        "--no-textconv",
        "-M",
        "--diff-filter=AMR",
        f"{base}...HEAD",
    )
    return parse_changed_lines(diff)


def files_touched_under(root: Path, base: str, folder: str) -> list[str]:
    """Every file under `folder` the branch added, changed, renamed or DELETED.

    Separate from changed_lines on purpose: a deleted rule file has no changed lines,
    and deleting a rule must still reach a human (D-018).

    Matched ignoring case: on Windows `.Healthkit/` is loaded as the config folder, so it
    must be flagged too (slice 004 verifier finding). Not a git pathspec, which is
    case-sensitive.
    """
    names = _git(root, "diff", "--name-only", "--no-renames", f"{base}...HEAD")
    prefix = folder.casefold().rstrip("/") + "/"
    return sorted(name for name in names.splitlines() if name.casefold().startswith(prefix))
