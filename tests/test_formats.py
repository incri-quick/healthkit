"""Output formats (slice 017): text (default), json, markdown, github. Same exit codes."""

import io
import json
import sys

from healthkit import cli, report
from healthkit.findings import Finding

# A branch with one problem (an unused import), one hint (a typo) and a settings change.
CHANGED = 'import os\n\n\ndef greet():\n    return "succesfully done"\n'


def branch(repo) -> str:
    repo.write("app.py", "x = 1\n")
    base = repo.commit("base")
    repo.write("app.py", CHANGED)
    repo.write(".healthkit/config.toml", "exclude = []\n")
    repo.commit()
    return base


def review(base: str, fmt: str) -> int:
    return cli.main(["review", "--base", base, "--format", fmt])


def test_json_has_every_finding_its_kind_and_the_exit_code(repo, capsys):
    code = review(branch(repo), "json")

    data = json.loads(capsys.readouterr().out)
    assert code == data["exit"] == 1
    kinds = {(f["tool"], f["rule"], f["path"], f["line"], f["kind"]) for f in data["findings"]}
    assert ("ruff", "F401", "app.py", 1, "problem") in kinds
    assert ("codespell", "spelling", "app.py", 5, "worth a look") in kinds
    assert data["approvals"] == [".healthkit/config.toml"]
    assert data["summary"].startswith("healthkit: 1 finding(s)")


def test_markdown_is_a_pull_request_comment(repo, capsys):
    review(branch(repo), "markdown")

    out = capsys.readouterr().out
    assert out.startswith("## healthkit")
    assert "| `app.py:1` | ruff F401 |" in out
    assert "### Worth a look" in out
    assert "`app.py:5`" in out
    assert "### Needs a person's approval" in out
    assert "never means" in out  # healthkit never says "safe" (D-017)


def test_github_annotations(repo, capsys):
    review(branch(repo), "github")

    out = capsys.readouterr().out
    assert "::error file=app.py,line=1,title=ruff F401::" in out
    assert "::warning file=app.py,line=5,title=codespell spelling::" in out
    assert "::notice title=needs human approval::.healthkit/config.toml" in out


def test_github_escaping_keeps_one_annotation_per_finding():
    finding = Finding("t", "r", "a,b:c.py", 3, "50% done\nthen more")

    out = report.github_line(finding, "error")

    assert out == "::error file=a%2Cb%3Ac.py,line=3,title=t r::50%25 done%0Athen more"


def test_machine_formats_are_always_utf8(monkeypatch):
    # Found on the live run (slice 017): redirected to a file on Windows, Python wrote
    # cp1252, so a posted comment came out garbled; "→" has no cp1252 byte at all.
    raw = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(raw, encoding="cp1252"))
    finding = Finding("t", "r", "café.py", 1, "naïve → fixed")

    for fmt in ("json", "markdown", "github"):
        report.emit(report.Report("scan", 1, ["healthkit scan: 1 finding(s)"], [finding]), fmt)
    sys.stdout.flush()

    text = raw.getvalue().decode("utf-8")
    assert "naïve → fixed" in text
    assert "café.py" in text


def test_scan_takes_a_format_too(repo, capsys):
    repo.write("pkg/a.py", "import os\n")
    repo.commit()

    code = cli.main(["scan", "pkg", "--format", "json"])

    data = json.loads(capsys.readouterr().out)
    assert code == data["exit"] == 1
    assert data["findings"][0]["rule"] == "F401"


def test_the_text_default_is_unchanged(repo, capsys):
    base = branch(repo)

    code = cli.main(["review", "--base", base])

    out = capsys.readouterr().out
    assert code == 1
    assert "app.py:1: [ruff F401]" in out
    assert "worth a look: app.py:5: [codespell spelling]" in out
    assert "needs human approval: .healthkit/config.toml" in out
