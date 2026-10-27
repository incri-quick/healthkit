"""Replay harness (slice 006): would today's healthkit have pointed at each AA fix?

    uv run python slices/006-replay/replay.py <quickrpa-clone> <worktree-dir>

For every fix commit in aa-fixes.toml: check out its PARENT in a throwaway worktree,
run healthkit's gate tools on the whole Python files the fix touched, and count a hit
when a finding sits on a line the fix changed (old side), or within 3 lines of a pure
insertion. Measurement only; reuses healthkit's adapters and config.
"""

from __future__ import annotations

import collections
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

from healthkit import config
from healthkit.findings import ToolError, ToolSkipped
from healthkit.tools import importlinter, opengrep, ruff

HERE = Path(__file__).parent
WINDOW = 3  # lines around a pure insertion that count as "at the fix"
_OLD_FILE = re.compile(r"^--- (?:a/(?P<path>.*?)|/dev/null)\t?$")
_HUNK = re.compile(r"^@@ -(?P<start>\d+)(?:,(?P<count>\d+))? \+")


def parse_old_lines(diff: str) -> dict[str, set[int]]:
    """Lines of the OLD file that a diff changes or removes (pure insertions: a window)."""
    old: dict[str, set[int]] = {}
    path: str | None = None
    for line in diff.splitlines():
        if match := _OLD_FILE.match(line):
            path = match["path"]
        elif (hunk := _HUNK.match(line)) and path is not None:
            start, count = int(hunk["start"]), int(hunk["count"] or 1)
            lines = range(start, start + count) if count else range(start - WINDOW, start + WINDOW + 1)
            old.setdefault(path, set()).update(n for n in lines if n > 0)
    return old


def is_hit(old: dict[str, set[int]], path: str, line: int) -> bool:
    return line in old.get(path, set())


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "core.quotepath=false", "-c", "core.longpaths=true", *args],
        cwd=repo, capture_output=True, check=True,
    ).stdout.decode("utf-8", "surrogateescape")


def replay_commit(clone: Path, tree: Path, commit: str) -> dict:
    parents = git(clone, "rev-list", "--parents", "-n1", commit).split()[1:]
    if len(parents) != 1:
        return {"commit": commit, "status": "skipped: not a single-parent commit"}
    parent = parents[0]
    git(tree, "checkout", "-q", "--detach", "--force", parent)
    assert git(tree, "rev-parse", "HEAD").strip() == parent, "worktree is not the fix's parent"
    shutil.rmtree(tree / ".healthkit", ignore_errors=True)
    shutil.copytree(clone / ".healthkit", tree / ".healthkit")
    diff = git(clone, "diff", "-U0", "--text", "--no-textconv", "-M", parent, commit)
    old = {p: lines for p, lines in parse_old_lines(diff).items() if p.endswith((".py", ".pyi"))}
    settings = config.load(tree)
    files = sorted(p for p in old if (tree / p).is_file() and not settings.is_excluded(p))
    if not files:
        return {"commit": commit, "status": "no Python lines changed in reviewed files"}
    hits, errors = [], []
    for tool in (ruff, opengrep, importlinter):
        try:
            for f in tool.run(tree, files):
                if not f.suppressed and is_hit(old, f.path, f.line):
                    hits.append(f)
        except ToolSkipped:
            pass
        except ToolError as exc:
            errors.append(f"{tool.NAME}: {exc}")
    status = "not checked" if errors else ("hit" if hits else "miss")
    return {"commit": commit, "status": status, "hits": hits, "errors": errors, "files": files}


def main() -> None:
    clone, tree = Path(sys.argv[1]), Path(sys.argv[2])
    key = tomllib.loads((HERE / "aa-fixes.toml").read_text(encoding="utf-8"))
    derived = key["derived"]
    if not (tree / ".git").exists():
        git(clone, "worktree", "add", "-q", "--detach", "--force", str(tree), "HEAD")
    rows, cache = [], {}
    for aa in key["aa"]:
        runs = []
        for commit in aa["fixes"]:
            if commit not in cache:
                cache[commit] = replay_commit(clone, tree, commit)
            runs.append(cache[commit])
        hits = [f for r in runs for f in r.get("hits", [])]
        statuses = {r["status"] for r in runs}
        status = "hit" if hits else ("not checked" if "not checked" in statuses else
                                     ("miss" if "miss" in statuses else sorted(statuses)[0]))
        rules = sorted({f"{f.tool} {f.rule}" for f in hits})
        judged = [r for r in rules if r in key.get("judged", {}).get(aa["id"], [])]
        rows.append({
            **aa, "status": status, "rules": rules, "judged": judged,
            # Score B: a judged hit by a rule NOT written from these incidents.
            "independent": any(r.split(" ", 1)[1] not in derived for r in judged),
            "notes": "; ".join(e for r in runs for e in r.get("errors", [])),
        })
    print_report(rows, derived)


def print_report(rows: list[dict], derived: dict) -> None:
    scored = [r for r in rows if r["kind"] != "tests" and r["status"] in ("hit", "miss")]
    raw = sum(r["status"] == "hit" for r in scored)
    score_a = sum(bool(r["judged"]) for r in scored)
    score_b = sum(r["independent"] for r in scored)
    print(f"Scored AAs: {len(scored)} (tests-only and not-checked excluded)")
    print(f"Raw line overlap (NOT a score: counts coincidences): {raw}/{len(scored)}")
    print(f"Score A (judged, all rules): {score_a}/{len(scored)}")
    print(f"Score B (judged, excluding rules derived from these AAs: {', '.join(derived)}): "
          f"{score_b}/{len(scored)}")
    kinds = collections.Counter(r["kind"] for r in scored)
    a_by_kind = collections.Counter(r["kind"] for r in scored if r["judged"])
    b_by_kind = collections.Counter(r["kind"] for r in scored if r["independent"])
    print("By kind (B / A / scored):",
          {k: f"{b_by_kind[k]}/{a_by_kind[k]}/{n}" for k, n in sorted(kinds.items())})
    print("\n| AA | kind | judged | caught by | other findings on the changed lines | fix | title |")
    print("|---|---|---|---|---|---|---|")
    for r in rows:
        verdict = ("caught" if r["independent"] else "caught (derived rule only)") if r["judged"] \
            else ("miss" if r["status"] in ("hit", "miss") else r["status"])
        others = [x for x in r["rules"] if x not in r["judged"]]
        print(f"| {r['id']} | {r['kind']} | {verdict} | {', '.join(r['judged']) or '-'} "
              f"| {', '.join(others) or '-'} | {', '.join(r['fixes'])} | {r['title']} |"
              + (f" {r['notes'][:80]}" if r["notes"] else ""))


if __name__ == "__main__":
    main()
