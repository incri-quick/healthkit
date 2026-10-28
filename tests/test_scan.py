"""`healthkit scan` and `healthkit baseline` (slice 012): every line of a folder, and only
new problems once today's are remembered."""

import json
import sys
from pathlib import Path

from healthkit import cli

UNUSED = "import os\n"  # ruff F401, on any line it sits


def scan(*folders: str) -> int:
    return cli.main(["scan", *folders])


def baseline(*folders: str) -> int:
    return cli.main(["baseline", *folders])


def test_every_line_of_the_folder_is_checked_and_only_that_folder(repo, capsys):
    repo.write("pkg/a.py", "x = 1\n" + UNUSED)
    repo.write("other/b.py", UNUSED)
    repo.commit()  # nothing is "changed": scan does not look at the diff

    code = scan("pkg")

    out = capsys.readouterr().out
    assert code == 1
    assert "pkg/a.py:2: [ruff F401]" in out
    assert "other/b.py" not in out
    assert "1 finding(s) in 1 file(s)" in out


def test_a_folder_that_does_not_exist_is_never_a_pass(repo, capsys):
    repo.write("pkg/a.py", "x = 1\n")
    repo.commit()

    assert scan("nowhere") == 2
    assert "nowhere" in capsys.readouterr().err


def test_a_folder_without_python_says_so(repo, capsys):
    repo.write("docs/readme.md", "hello\n")
    repo.commit()

    assert scan("docs") == 0
    assert "0 Python files" in capsys.readouterr().out


def test_scan_never_runs_project_commands(repo, capsys, tmp_path):
    marker = tmp_path / "ran.txt"
    command = f"['{Path(sys.executable).as_posix()}', '-c', 'open(r\"{marker}\", \"w\").close()']"
    repo.write(
        ".healthkit/config.toml",
        f'[[check]]\nname = "c"\ncommand = {command}\npaths = ["**"]\nreason = "r"\n',
    )
    repo.write("pkg/a.py", "x = 1\n")
    repo.commit()

    scan("pkg")

    assert not marker.exists()
    assert "project checks are not run by scan" in capsys.readouterr().out


def test_an_inline_suppression_is_counted_not_hidden(repo, capsys):
    repo.write("pkg/a.py", "import os  # noqa: F401\n")
    repo.commit()

    assert scan("pkg") == 0
    assert "suppressed: 1" in capsys.readouterr().out


def test_a_baseline_hides_todays_findings_and_counts_them(repo, capsys):
    repo.write("pkg/a.py", UNUSED)
    repo.commit()

    assert baseline("pkg") == 0
    assert scan("pkg") == 0

    out = capsys.readouterr().out
    assert "F401" not in out.split("baseline written")[-1]
    assert "baselined: 1" in out


def test_a_baselined_finding_still_matches_after_the_code_moves(repo, capsys):
    repo.write("pkg/a.py", UNUSED)
    repo.commit()
    baseline("pkg")
    repo.write("pkg/a.py", "x = 1\n" * 10 + UNUSED)

    assert scan("pkg") == 0
    assert "baselined: 1" in capsys.readouterr().out


def test_a_second_copy_of_a_baselined_line_is_new(repo, capsys):
    repo.write("pkg/a.py", UNUSED)
    repo.commit()
    baseline("pkg")
    repo.write("pkg/a.py", UNUSED + "def f():\n    import os\n")

    assert scan("pkg") == 1
    out = capsys.readouterr().out
    assert "pkg/a.py:3: [ruff F401]" in out
    assert "baselined: 1" in out


def test_a_fixed_finding_is_counted(repo, capsys):
    repo.write("pkg/a.py", UNUSED)
    repo.commit()
    baseline("pkg")
    repo.write("pkg/a.py", "x = 1\n")

    assert scan("pkg") == 0
    assert "fixed since the baseline: 1" in capsys.readouterr().out


def test_a_broken_baseline_is_never_a_pass(repo, capsys):
    repo.write("pkg/a.py", UNUSED)
    repo.write(".healthkit/baseline.json", "{not json")
    repo.commit()

    assert scan("pkg") == 2
    assert "baseline" in capsys.readouterr().err


def test_no_baseline_is_written_when_a_tool_failed(repo, monkeypatch):
    monkeypatch.setenv("HEALTHKIT_OPENGREP", "no-such-opengrep-healthkit-test")
    repo.write("pkg/a.py", UNUSED)
    repo.commit()

    assert baseline("pkg") == 2
    assert not (repo.root / ".healthkit" / "baseline.json").exists()


def test_a_failing_tool_does_not_hide_the_others(repo, capsys, monkeypatch):
    monkeypatch.setenv("HEALTHKIT_OPENGREP", "no-such-opengrep-healthkit-test")
    repo.write("pkg/a.py", UNUSED)
    repo.commit()

    assert scan("pkg") == 2
    assert "pkg/a.py:1: [ruff F401]" in capsys.readouterr().out


def test_review_skips_baselined_findings_on_changed_lines(repo, capsys):
    # Code moved into a block: its lines are "changed" (re-indented), its old problem is
    # not new. The text matches once indentation is set aside.
    repo.write("pkg/a.py", "def f():\n    import os\n")
    repo.commit()
    baseline("pkg")
    base = repo.commit("baseline")
    repo.write("pkg/a.py", "def f(flag):\n    if flag:\n        import os\n")
    repo.commit()

    code = cli.main(["review", "--base", base])

    out = capsys.readouterr().out
    assert code == 0, out
    assert "baselined: 1" in out


def test_review_shows_an_old_problem_on_a_line_that_now_says_something_else(repo, capsys):
    repo.write("pkg/a.py", UNUSED)
    repo.commit()
    baseline("pkg")
    base = repo.commit("baseline")
    repo.write("pkg/a.py", "import os  # still unused\n")
    repo.commit()

    assert cli.main(["review", "--base", base]) == 1
    assert "pkg/a.py:1: [ruff F401]" in capsys.readouterr().out


def test_baselining_one_folder_keeps_the_others(repo, capsys):
    repo.write("pkg/a.py", UNUSED)
    repo.write("other/b.py", UNUSED)
    repo.commit()
    baseline("pkg")
    baseline("other")

    assert scan(".") == 0
    assert "baselined: 2" in capsys.readouterr().out


def test_the_baseline_file_is_readable_and_stable(repo):
    repo.write("pkg/a.py", UNUSED)
    repo.commit()
    baseline("pkg")

    data = json.loads((repo.root / ".healthkit" / "baseline.json").read_bytes())

    assert data["findings"] == [
        {"tool": "ruff", "rule": "F401", "path": "pkg/a.py", "text": "import os", "count": 1}
    ]
    assert b"\r" not in (repo.root / ".healthkit" / "baseline.json").read_bytes()
