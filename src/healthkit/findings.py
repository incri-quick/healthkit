"""The one finding format every tool's output is converted to."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    tool: str
    rule: str
    path: str  # repo-relative, forward slashes
    line: int
    message: str
    # Hidden by an inline suppression comment (ruff's noqa, Opengrep's nosemgrep), found
    # with the tool's own rules. On a changed line it needs a human, never a pass
    # (slice 005, D-018).
    suppressed: bool = False
    # Shown for a person to look at, never a failed gate: a rule below the precision a
    # blocking rule needs (slice 008: soft-delete-read, about half real on unseen code).
    advisory: bool = False
    # A finding about a whole function covers its lines: a change anywhere in it counts
    # (slice 011: copies drift through body edits). 0 means the one line above.
    end_line: int = 0

    def touches(self, lines: set[int]) -> bool:
        return any(n in lines for n in range(self.line, max(self.line, self.end_line) + 1))

    def render(self) -> str:
        return f"{self.path}:{self.line}: [{self.tool} {self.rule}] {self.message}"


class ToolError(Exception):
    """A tool did not run, or its output could not be read. Never a pass (L-004)."""


class ToolSkipped(Exception):  # noqa: N818 - a signal, not an error
    """There is nothing for this tool to check against (e.g. no contract). Said out loud."""
