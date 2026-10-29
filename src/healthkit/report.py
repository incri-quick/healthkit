"""How results are shown (slice 017): text for a person, JSON for an AI assistant or a
script, Markdown for a pull-request comment, GitHub workflow commands for Actions.

Every format carries the same results and the command keeps the same exit code. healthkit
never posts anything: a comment is the person's action (`gh pr comment <n> -F <file>`).
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from healthkit.findings import Finding

FORMATS = ("text", "json", "markdown", "github")


@dataclass
class Report:
    command: str
    exit: int
    parts: list[str]  # the summary line: verdict first, then details
    problems: list[Finding] = field(default_factory=list)
    advisory: list[Finding] = field(default_factory=list)
    checks: list[Finding] = field(default_factory=list)  # a project's own failing checks
    tails: dict[str, list[str]] = field(default_factory=dict)  # their last output lines
    approvals: list[str] = field(default_factory=list)


def emit(report: Report, fmt: str) -> int:
    """Print the report in `fmt`; return its exit code, the same in every format."""
    render = {"json": _json, "markdown": _markdown, "github": _github}.get(fmt, _text)
    if fmt != "text" and hasattr(sys.stdout, "reconfigure"):
        # Machine formats are UTF-8 everywhere. Redirected on Windows, Python writes cp1252:
        # a posted comment came out garbled, and "→" crashed it (slice 017 live run).
        sys.stdout.reconfigure(encoding="utf-8")
    print(render(report))
    return report.exit


def _text(report: Report) -> str:
    lines = [f.render() for f in report.problems]
    lines += [f"worth a look: {f.render()}" for f in report.advisory]
    for finding in report.checks:
        lines += [finding.render(), *(f"    {line}" for line in report.tails[finding.rule])]
    lines += [f"needs human approval: {item}" for item in report.approvals]
    return "\n".join([*lines, " | ".join(report.parts)])


def _json(report: Report) -> str:
    def entry(finding: Finding, kind: str) -> dict:
        return {
            "kind": kind,
            "tool": finding.tool,
            "rule": finding.rule,
            "path": finding.path,
            "line": finding.line,
            "end_line": finding.end_line or finding.line,
            "message": finding.message,
        }

    findings = [entry(f, "problem") for f in report.problems]
    findings += [entry(f, "worth a look") for f in report.advisory]
    findings += [entry(f, "check") | {"output": report.tails[f.rule]} for f in report.checks]
    data = {
        "command": report.command,
        "exit": report.exit,
        "summary": report.parts[0],
        "details": report.parts[1:],
        "findings": findings,
        "approvals": report.approvals,
    }
    return json.dumps(data, indent=2)


def _markdown(report: Report) -> str:
    def cell(text: str) -> str:
        return text.replace("|", "\\|").replace("\n", " ")

    lines = [f"## {report.parts[0]}", ""]
    if report.problems:
        lines += [f"### Problems ({len(report.problems)})", "", "| Where | Check | What |"]
        lines += ["|---|---|---|"]
        lines += [
            f"| `{f.path}:{f.line}` | {f.tool} {f.rule} | {cell(f.message)} |"
            for f in report.problems
        ]
        lines += [""]
    if report.checks:
        lines += ["### The project's own checks failed", ""]
        for finding in report.checks:
            output = "\n".join(report.tails[finding.rule])
            lines += [
                f"- **{finding.rule}**: {cell(finding.message)}",
                "",
                f"```\n{output}\n```",
                "",
            ]
    if report.advisory:
        lines += [f"### Worth a look ({len(report.advisory)})", ""]
        lines += ["Hints: about half are real, so read the code before acting on one.", ""]
        lines += [
            f"- `{f.path}:{f.line}` {f.tool} {f.rule}: {cell(f.message)}" for f in report.advisory
        ]
        lines += [""]
    if report.approvals:
        lines += ["### Needs a person's approval", ""]
        lines += [f"- `{item}`" for item in report.approvals]
        lines += [""]
    footer = 'healthkit reports what its tools know; a clean result never means "safe".'
    return "\n".join([*lines, "---", " | ".join(report.parts[1:]), "", f"_{footer}_"])


def _github(report: Report) -> str:
    lines = [github_line(f, "error") for f in report.problems]
    lines += [github_line(f, "warning") for f in report.advisory]
    lines += [f"::error title=check {_property(f.rule)}::{_data(f.message)}" for f in report.checks]
    lines += [f"::notice title=needs human approval::{_data(item)}" for item in report.approvals]
    return "\n".join([*lines, " | ".join(report.parts)])


def github_line(finding: Finding, level: str) -> str:
    """One GitHub workflow command; its text rules escape %, CR and LF (and , : in
    properties), or a message would end the annotation early."""
    where = f"file={_property(finding.path)},line={finding.line}"
    title = _property(f"{finding.tool} {finding.rule}")
    return f"::{level} {where},title={title}::{_data(finding.message)}"


def _data(text: str) -> str:
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _property(text: str) -> str:
    return _data(text).replace(":", "%3A").replace(",", "%2C")
