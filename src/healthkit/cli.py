"""`healthkit review --base <ref>`: findings on the lines this branch changed.

Exit codes: 0 no known problems, 1 findings, 2 could not check (never reported as a
pass), 3 only a `.healthkit/` change that a person must approve (D-018).
Priority when several apply: 2, then 1, then 3.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

from healthkit import config, gitdiff
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


@dataclass
class _Run:
    findings: set[Finding] = field(default_factory=set)
    ran: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: bool = False


def _review(cwd: Path, base: str) -> int:
    try:
        root = gitdiff.repo_root(cwd)
        changed = gitdiff.changed_lines(root, base)
        referee_changes = gitdiff.files_touched_under(root, base, config.HOME.as_posix())
        settings = config.load(root)
    except (gitdiff.GitError, config.ConfigError) as exc:
        print(f"healthkit: {exc}", file=sys.stderr)
        return 2
    python_files = sorted(path for path in changed if path.endswith((".py", ".pyi")))
    reviewed = [path for path in python_files if not settings.is_excluded(path)]
    run = _run_tools(root, reviewed) if reviewed else _Run()

    on_changed_lines = [
        f
        for f in run.findings
        if f.line in changed.get(f.path, set()) and not settings.is_excluded(f.path)
    ]
    new = sorted(
        (f for f in on_changed_lines if not settings.allows(f)),
        key=lambda f: (f.path, f.line, f.tool, f.rule),
    )
    for finding in new:
        print(finding.render())
    for path in referee_changes:  # D-018: the referee changed; a person must approve
        print(f"needs human approval: {path}")

    if not reviewed:
        summary = "healthkit: nothing to review (no changed Python files)"
    elif new:
        summary = f"healthkit: {len(new)} finding(s) on changed lines in {len(reviewed)} file(s)"
    else:
        summary = f"healthkit: no known problems on changed lines in {len(reviewed)} file(s)"
    parts = [summary]
    if reviewed:
        parts.append(f"ran: {', '.join(run.ran) or 'nothing'}")
    parts += [f"skipped: {'; '.join(run.skipped)}"] if run.skipped else []
    excluded = len(python_files) - len(reviewed)
    parts += [f"excluded: {excluded} file(s)"] if excluded else []
    allowed = len(on_changed_lines) - len(new)
    parts += [f"allowed: {allowed}"] if allowed else []
    parts += [f"needs human approval: {len(referee_changes)} file(s)"] if referee_changes else []
    print(" | ".join(parts))

    if run.failed:
        return 2
    if new:
        return 1
    return 3 if referee_changes else 0


def _run_tools(root: Path, files: list[str]) -> _Run:
    run = _Run()
    # One try per tool on purpose: a failing tool must not hide the others' findings.
    for tool in GATE_TOOLS:
        try:
            # A set: tools can emit the same finding twice (ruff PLC2701, one per name).
            run.findings |= set(tool.run(root, files))
            run.ran.append(tool.NAME)
        except ToolSkipped as exc:
            run.skipped.append(f"{tool.NAME} ({exc})")
        except ToolError as exc:
            print(f"healthkit: {tool.NAME}: {exc}", file=sys.stderr)
            run.failed = True
    return run


if __name__ == "__main__":
    sys.exit(main())
