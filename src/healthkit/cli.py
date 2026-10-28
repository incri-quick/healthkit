"""`healthkit review --base <ref>`: findings on the lines this branch changed.
`healthkit scan <folder>`: every line of a folder. `healthkit baseline`: remember today's.

Exit codes: 0 no known problems, 1 findings, 2 could not check (never reported as a
pass), 3 only a `.healthkit/` change that a person must approve (D-018).
Priority when several apply: 2, then 1, then 3.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

from healthkit import apicheck, baseline, checks, config, gitdiff, report, routes
from healthkit.findings import Finding, ToolError, ToolSkipped
from healthkit.tools import codespell, copies, django, importlinter, opengrep, options, ruff

GATE_TOOLS = (ruff, opengrep, importlinter, django, copies, codespell, options)  # D-014
BASELINE = "remember today's findings in these folders, so only new ones show"
FORMAT = "text (default), json (AI, scripts), markdown (a PR comment), github (Actions)"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="healthkit")
    commands = parser.add_subparsers(dest="command", required=True)
    review = commands.add_parser("review", help="check the lines this branch changed")
    review.add_argument("--base", required=True, help="branch or commit to compare against")
    review.add_argument("--format", choices=report.FORMATS, default="text", help=FORMAT)
    for name, text in (("scan", "check every line of these folders"), ("baseline", BASELINE)):
        command = commands.add_parser(name, help=text)
        command.add_argument("folders", nargs="*", default=["."], help="default: the repo")
        command.add_argument("--format", choices=report.FORMATS, default="text", help=FORMAT)
    apicheck.add_parser(commands)
    routes.add_parser(commands)
    args = parser.parse_args(argv)
    if args.command == "api":
        return apicheck.run(args)
    if args.command == "routes":
        return routes.run(args)
    if args.command in {"scan", "baseline"}:
        return _scan(Path.cwd(), args.folders, write=args.command == "baseline", fmt=args.format)
    return _review(Path.cwd(), args.base, args.format)


@dataclass
class _Run:
    findings: set[Finding] = field(default_factory=set)
    ran: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: bool = False


def _review(cwd: Path, base: str, fmt: str = "text") -> int:
    try:
        root = gitdiff.repo_root(cwd)
        changed = gitdiff.changed_lines(root, base)
        referee_changes = gitdiff.files_touched_under(root, base, config.HOME.as_posix())
        settings = config.load(root)
        # Commands from the BASE branch only: a branch's new command must not run before a
        # person approves it (slice 008, D-018).
        approved = config.parse(gitdiff.file_at(root, base, config.CONFIG.as_posix()))
        known = baseline.load(root)
    except (gitdiff.GitError, config.ConfigError) as exc:
        print(f"healthkit: {exc}", file=sys.stderr)
        return 2
    python_files = sorted(path for path in changed if path.endswith((".py", ".pyi")))
    reviewed = [path for path in python_files if not settings.is_excluded(path)]
    run = _run_tools(root, reviewed) if reviewed else _Run()
    project = checks.run(root, approved.checks, sorted(changed))

    on_changed_lines = [
        f
        for f in run.findings
        if f.touches(changed.get(f.path, set())) and not settings.is_excluded(f.path)
    ]
    not_allowed = sorted(
        (f for f in on_changed_lines if not settings.allows(f)),
        key=lambda f: (f.path, f.line, f.tool, f.rule),
    )
    suppressed = [f for f in not_allowed if f.suppressed]
    shown, remembered, _ = baseline.split(root, [f for f in not_allowed if not f.suppressed], known)
    problems = [f for f in shown if not f.advisory]
    advisory = [f for f in shown if f.advisory]
    failed_checks = _merge_checks(project, run)
    new = problems + failed_checks
    # D-018: the referee changed, or a check was switched off inline. A person decides.
    approvals = [f"{path}" for path in referee_changes] + [
        f"{f.path}:{f.line} suppresses {f.tool} {f.rule}" for f in suppressed
    ]

    if not reviewed and not new:
        summary = "healthkit: nothing to review (no changed Python files)"
    elif new:
        summary = f"healthkit: {len(new)} finding(s) in {len(reviewed)} changed file(s) and checks"
    else:
        summary = f"healthkit: no known problems on changed lines in {len(reviewed)} file(s)"
    parts = [summary]
    if reviewed or run.ran:
        parts.append(f"ran: {', '.join(run.ran) or 'nothing'}")
    parts += [f"skipped: {'; '.join(run.skipped)}"] if run.skipped else []
    excluded = len(python_files) - len(reviewed)
    parts += [f"excluded: {excluded} file(s)"] if excluded else []
    allowed = len(on_changed_lines) - len(not_allowed)
    parts += [f"allowed: {allowed}"] if allowed else []
    parts += [f"worth a look: {len(advisory)}"] if advisory else []
    parts += [f"baselined: {remembered}"] if remembered else []
    parts += [f"needs human approval: {len(approvals)} item(s)"] if approvals else []
    code = 2 if run.failed else 1 if new else 3 if approvals else 0
    result = report.Report("review", code, parts, problems, advisory, failed_checks)
    result.tails, result.approvals = project.tails, approvals
    return report.emit(result, fmt)


def _scan(cwd: Path, folders: list[str], *, write: bool, fmt: str = "text") -> int:
    """Every line of the Python files in `folders`. Never runs project commands: there is
    no base branch to take them from (slice 012)."""
    try:
        root = gitdiff.repo_root(cwd)
        settings = config.load(root)
        known = baseline.load(root)
        files = _python_files(root, cwd, folders, settings)
    except (gitdiff.GitError, config.ConfigError) as exc:
        print(f"healthkit: {exc}", file=sys.stderr)
        return 2
    if not files:
        nothing = f"healthkit scan: 0 Python files in {', '.join(folders)}"
        return report.emit(report.Report("scan", 0, [nothing]), fmt)
    run = _run_tools(root, sorted(files))
    found = sorted(
        (f for f in run.findings if f.path in files and not settings.allows(f)),
        key=lambda f: (f.path, f.line, f.tool, f.rule),
    )
    suppressed = sum(f.suppressed for f in found)
    kept = [f for f in found if not f.suppressed]
    if write:
        if run.failed:  # an incomplete run must not become "how things are"
            print("healthkit baseline: not written, a tool could not run", file=sys.stderr)
            return 2
        baseline.save(root, kept, files)
        print(f"healthkit: baseline written: {len(kept)} finding(s) in {len(files)} file(s)")
        return 0
    shown, remembered, gone = baseline.split(root, kept, known, files)
    new = [f for f in shown if not f.advisory]
    advisory = [f for f in shown if f.advisory]
    verdict = f"{len(new)} finding(s)" if new else "no known problems"
    parts = [f"healthkit scan: {verdict} in {len(files)} file(s)", f"ran: {', '.join(run.ran)}"]
    parts += [f"skipped: {'; '.join(run.skipped)}"] if run.skipped else []
    parts += ["project checks are not run by scan"]
    parts += [f"worth a look: {len(advisory)}"] if advisory else []
    parts += [f"suppressed: {suppressed}"] if suppressed else []
    parts += [f"baselined: {remembered}"] if remembered else []
    parts += [f"fixed since the baseline: {gone}"] if gone else []
    code = 2 if run.failed else (1 if new else 0)
    return report.emit(report.Report("scan", code, parts, new, advisory), fmt)


def _python_files(root: Path, cwd: Path, folders: list[str], settings: config.Settings) -> set[str]:
    tracked = [p for p in gitdiff.project_files(root) if p.endswith((".py", ".pyi"))]
    files: set[str] = set()
    for folder in folders:
        target = (cwd / folder).resolve()
        if not target.exists():
            msg = f"no such folder: {folder}"
            raise config.ConfigError(msg)
        prefix = target.relative_to(root.resolve()).as_posix().strip(".")
        files |= {
            p
            for p in tracked
            if (not prefix or p == prefix or p.startswith(prefix.rstrip("/") + "/"))
            and not settings.is_excluded(p)
        }
    return files


def _merge_checks(project: checks.CheckRun, run: _Run) -> list[Finding]:
    """Fold the project checks into the run; return the failed ones (whole-project, not
    tied to a changed line). Errors go to stderr in every format."""
    run.ran += project.ran
    run.skipped += project.skipped
    for error in project.errors:
        print(f"healthkit: {error}", file=sys.stderr)
    run.failed = run.failed or bool(project.errors)
    return project.findings


def _run_tools(root: Path, files: list[str]) -> _Run:
    run = _Run()
    # One try per tool on purpose: a failing tool must not hide the others' findings.
    for tool in GATE_TOOLS:
        try:
            # A set: tools can emit the same finding twice (ruff PLC2701, one per name).
            run.findings |= set(tool.run(root, files))
            run.ran.append(tool.NAME)
            run.skipped += tool.notes(root) if hasattr(tool, "notes") else []
        except ToolSkipped as exc:
            run.skipped.append(f"{tool.NAME} ({exc})")
        except ToolError as exc:
            print(f"healthkit: {tool.NAME}: {exc}", file=sys.stderr)
            run.failed = True
    return run


if __name__ == "__main__":
    sys.exit(main())
