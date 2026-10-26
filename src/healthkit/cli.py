"""`healthkit review --base <ref>`: findings on the lines this branch changed.

Exit codes: 0 pass, 1 findings, 2 could not check (never reported as a pass).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from healthkit import gitdiff
from healthkit.findings import Finding, ToolError, ToolSkipped
from healthkit.tools import importlinter, opengrep, ruff

GATE_TOOLS = (ruff, opengrep, importlinter)  # D-014: the pre-push gate


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

    findings: set[Finding] = set()
    ran: list[str] = []
    skipped: list[str] = []
    failed = False
    # One try per tool on purpose: a failing tool must not hide the others' findings.
    for tool in GATE_TOOLS:
        try:
            # A set: tools can emit the same finding twice (ruff PLC2701, one per name).
            findings |= set(tool.run(root, python_files))
            ran.append(tool.NAME)
        except ToolSkipped as exc:  # noqa: PERF203 - see above
            skipped.append(f"{tool.NAME} ({exc})")
        except ToolError as exc:
            print(f"healthkit: {tool.NAME}: {exc}", file=sys.stderr)
            failed = True

    new = sorted(
        (f for f in findings if f.line in changed.get(f.path, set())),
        key=lambda f: (f.path, f.line, f.tool, f.rule),
    )
    for finding in new:
        print(finding.render())
    summary = f"healthkit: {len(new)} finding(s) on changed lines in {len(python_files)} file(s)"
    summary += f" | ran: {', '.join(ran) or 'nothing'}"
    if skipped:
        summary += f" | skipped: {'; '.join(skipped)}"
    print(summary)
    if failed:
        return 2
    return 1 if new else 0


if __name__ == "__main__":
    sys.exit(main())
