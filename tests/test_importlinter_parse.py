"""Parsing import-linter's text output. Fixtures are real output (L-006)."""

from pathlib import Path

import pytest

from healthkit.findings import ToolError
from healthkit.tools.importlinter import parse_broken_links

FIXTURES = Path(__file__).parent / "fixtures"


def test_links_from_real_output_including_wrapped_line_numbers():
    # QuickRPA dev 7fadfe3, slice 001 contract. Line numbers wrap: "(l.32, \nl.963)".
    text = (FIXTURES / "importlinter-broken-wrapped.txt").read_text(encoding="utf-8")

    links = {(importer, imported, line) for importer, imported, line, _ in parse_broken_links(text)}

    assert ("studio_robot.watchdog", "studio_robot.api.robots", 410) in links
    assert ("studio_robot.services", "studio_workflow.execution.history_codec", 32) in links
    assert ("studio_robot.services", "studio_workflow.execution.history_codec", 963) in links
    assert ("studio_workflow.api.workflow", "studio_robot.api.robots", 4027) in links


def test_a_config_error_is_not_mistaken_for_no_broken_links():
    # import-linter exits 1 for this too; only the text tells them apart.
    text = (FIXTURES / "importlinter-config-error.txt").read_text(encoding="utf-8")

    with pytest.raises(ToolError, match="nosuchpkg"):
        parse_broken_links(text)
