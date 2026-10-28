"""The module scorecard (slice 018): facts per module, no invented grade."""

import json
import sys

from healthkit import cli
from healthkit.tools import pyscn

# Complexity 22: pyscn calls it high risk (above 19); ruff calls it too complex (above 10).
ROUTE = "def route(x):\n" + "".join(f"    if x == {i}:\n        return {i}\n" for i in range(21))
ROUTE += "    return -1\n"


def project(repo) -> None:
    # "zeta" sorts last by name and first by need: the card must order by need.
    # One problem (the unused os); the suppressed sys import must not count.
    repo.write("zeta/core.py", "import os\nimport sys  # noqa: F401\n\n\n" + ROUTE)
    repo.write("beta/util.py", "def add(a, b):\n    return a + b\n")
    repo.write("zeta/tests/test_core.py", "import sys\n\n\n" + ROUTE)  # left out
    repo.commit()


def test_one_row_of_facts_per_module_worst_first(repo, capsys):
    project(repo)

    code = cli.main(["scorecard", "--format", "json"])

    data = json.loads(capsys.readouterr().out)
    assert code == 0
    zeta, beta = data["modules"]
    assert zeta["module"] == "zeta"
    assert zeta["files"] == 1
    assert zeta["too_complex"] == 1
    assert zeta["most_complex"] == {"name": "route", "complexity": 22}
    assert zeta["problems"] == 1
    assert zeta["hints"] == 1  # ruff C901, advisory
    assert beta == {
        "module": "beta",
        "files": 1,
        "lines": beta["lines"],
        "too_complex": 0,
        "most_complex": {"name": "add", "complexity": 1},
        "problems": 0,
        "hints": 0,
    }
    assert data["overall"]["grade"] in "ABCDF"


def test_text_and_markdown_tables(repo, capsys):
    project(repo)

    cli.main(["scorecard"])
    text = capsys.readouterr().out
    cli.main(["scorecard", "--format", "markdown"])
    markdown = capsys.readouterr().out

    assert text.index("zeta") < text.index("beta")  # worst first, not by name
    assert "route (22)" in text
    assert "overall (pyscn):" in text
    assert "| Module | Files | Lines | Too complex | Most complex | Problems | Hints |" in markdown
    assert "| zeta | 1 |" in markdown


def test_files_and_lines_come_from_healthkits_own_list(repo, capsys, monkeypatch):
    # QuickRPA live run (slice 018): pyscn skipped `docs/` and `.claude/`, so their rows
    # showed 0 files beside real findings. Counts now come from the files healthkit checks.
    project(repo)
    repo.write("consts/values.py", "X = 1\n\nY = 2\n")
    repo.commit()
    real = pyscn.analyze
    monkeypatch.setattr(
        pyscn, "analyze", lambda root, folders: real(root, folders) | {"module_quality": []}
    )

    cli.main(["scorecard", "--format", "json"])
    rows = {m["module"]: m for m in json.loads(capsys.readouterr().out)["modules"]}
    cli.main(["scorecard"])
    text = capsys.readouterr().out

    assert rows["zeta"]["files"] == 1
    assert rows["consts"]["lines"] == 2  # non-blank lines
    assert rows["consts"]["most_complex"] is None
    assert "consts" in text
    assert " - " in text.split("consts", 1)[1].splitlines()[0]  # no function: "-"


def test_a_folder_limits_the_card(repo, capsys):
    project(repo)

    cli.main(["scorecard", "beta", "--format", "json"])

    assert [m["module"] for m in json.loads(capsys.readouterr().out)["modules"]] == ["beta"]


def test_a_failing_pyscn_is_never_a_card(repo, capsys, monkeypatch):
    project(repo)
    fail = "import sys; print('boom', file=sys.stderr); sys.exit(3)"
    monkeypatch.setattr(pyscn, "COMMAND", [sys.executable, "-c", fail])

    assert cli.main(["scorecard"]) == 2
    captured = capsys.readouterr()
    assert "pyscn failed (exit 3)" in captured.err
    assert "zeta" not in captured.out


def test_another_tool_failing_means_no_card(repo, capsys, monkeypatch):
    project(repo)
    monkeypatch.setenv("HEALTHKIT_OPENGREP", "no-such-opengrep-healthkit-test")

    assert cli.main(["scorecard"]) == 2
    assert "zeta" not in capsys.readouterr().out  # a partial card would look whole


def test_a_missing_pyscn_is_never_a_card(repo, capsys, monkeypatch):
    project(repo)
    monkeypatch.setattr(pyscn, "COMMAND", ["no-such-pyscn-healthkit-test"])

    assert cli.main(["scorecard"]) == 2
    assert "pyscn" in capsys.readouterr().err
