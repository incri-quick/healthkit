"""`healthkit review --base <ref>`: findings on the lines this branch changed.

Exit codes: 0 pass, 1 findings, 2 could not check (never reported as a pass).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from healthkit import gitdiff
from healthkit.findings import ToolError
from healthkit.tools import ruff


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="healthkit")
    commands = parser.add_subparsers(dest="command", required=True)
    review = commands.add_parser("review", help="check the lines this branch changed")
    review.add_argument("--base", required=True, help="branch or commit to compare against")
    args = parser.parse_args(argv)
    return _review(Path.cwd(), args.base)


def _review(cwd: Path, base: str) -> int:
    try:
        root = gitdiff.repo_root(cwd)
        changed = gitdiff.changed_lines(root, base)
    except gitdiff.GitError as exc:
        print(f"healthkit: {exc}", file=sys.stderr)
        return 2
    python_files = sorted(path for path in changed if path.endswith((".py", ".pyi")))
    if not python_files:
        print("healthkit: nothing to review (no changed Python files)")
        return 0
    try:
        findings = ruff.run(root, python_files)
    except ToolError as exc:
        print(f"healthkit: {exc}", file=sys.stderr)
        return 2
    # A set: tools can emit the same finding twice (ruff PLC2701, one per imported name).
    new = {f for f in findings if f.line in changed.get(f.path, set())}
    for finding in sorted(new, key=lambda f: (f.path, f.line, f.rule)):
        print(finding.render())
    print(f"healthkit: {len(new)} finding(s) on changed lines in {len(python_files)} file(s)")
    return 1 if new else 0


if __name__ == "__main__":
    sys.exit(main())
