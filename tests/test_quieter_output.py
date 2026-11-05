"""Quieter output (slice 024): in `scan`, import order and unused imports folded into one
line with the command that fixes them (`review` lists them in full, plus that line); an
undefined name inside a quoted type is a hint. Measured: those two rules were half of
QuickRPA's findings and two thirds of the school project's, and all 17 of its "undefined
name" alarms were SQLAlchemy's quoted types."""

import json

from healthkit import cli
from healthkit.tools import ruff

STYLE_ONLY = "import sys\nimport os\n\n\ndef f():\n    return 1\n"  # I001 + F401 twice
REAL = "def g():\n    try:\n        return 1\n    except Exception:\n        return 0\n"  # BLE001
FIX = "uvx ruff@0.17.2 check --isolated --fix --select I001,F401"

# The school project's models (app/models/people.py, user.py): names SQLAlchemy resolves.
MODELS = """\
from typing import Optional

from sqlalchemy.orm import Mapped, relationship


class Parent:
    user: Mapped["User"] = relationship()
    teacher: Mapped[Optional["Teacher"]] = relationship()
    pupils: Mapped["list[Pupil]"] = relationship()


def report():
    return f"{Missing} and {'Quoted'}"


def lost():
    return Undefined
"""


def review(base: str, *args: str) -> int:
    return cli.main(["review", "--base", base, *args])


def scan(*args: str) -> int:
    return cli.main(["scan", *args])


def test_scan_folds_style_findings_into_one_line_with_the_fix(repo, capsys):
    repo.write("a.py", STYLE_ONLY + "\n\n" + REAL)
    repo.commit("base")

    code = scan()

    out = capsys.readouterr().out
    assert code == 1, out  # still problems: only how they are shown changes
    assert "[ruff BLE001]" in out  # a real finding, in full
    assert "[ruff I001]" not in out
    assert "[ruff F401]" not in out
    assert (
        "style: 3 finding(s), import order (I001) 1, unused imports (F401) 2, in 1 file(s)" in out
    )
    assert f"Fix: {FIX} ." in out  # scan: the folders it scanned


def test_review_lists_style_on_your_lines_in_full_plus_the_fix(repo, capsys):
    repo.write("a.py", "x = 1\n")
    base = repo.commit("base")
    repo.write("a.py", STYLE_ONLY)
    repo.commit()

    code = review(base)

    out = capsys.readouterr().out
    assert code == 1, out
    assert "a.py:1: [ruff I001]" in out  # your own lines keep their line numbers
    assert "a.py:2: [ruff F401]" in out
    assert f"Fix: {FIX} a.py" in out


def test_json_still_lists_every_style_finding(repo, capsys):
    repo.write("a.py", STYLE_ONLY)
    repo.commit("base")

    scan("--format", "json")

    rules = [f["rule"] for f in json.loads(capsys.readouterr().out)["findings"]]
    assert sorted(rules) == ["F401", "F401", "I001"]


def test_markdown_scan_folds_style_too(repo, capsys):
    repo.write("a.py", STYLE_ONLY + "\n\n" + REAL)
    repo.commit("base")

    scan("--format", "markdown")

    out = capsys.readouterr().out
    assert "BLE001" in out
    assert "| ruff I001 |" not in out
    assert "style: 3 finding(s)" in out
    assert FIX in out


def test_the_fix_command_names_ten_files_and_counts_the_rest(repo, capsys):
    repo.write("keep.py", "x = 1\n")
    base = repo.commit("base")
    for n in range(12):
        repo.write(f"m{n:02}.py", "import os\n")
    repo.commit()

    review(base)

    fix = next(line for line in capsys.readouterr().out.splitlines() if "Fix:" in line)
    assert "in 12 file(s)" in fix
    assert f"Fix: {FIX} m00.py m01.py" in fix
    assert fix.endswith("m09.py (and 2 more)")
    assert "m10.py" not in fix


def test_scan_fixes_the_folders_it_scanned(repo, capsys):
    repo.write("pkg/a.py", STYLE_ONLY)
    repo.commit("base")

    code = scan("pkg")

    out = capsys.readouterr().out
    assert code == 1, out
    assert f"Fix: {FIX} pkg" in out


def test_an_undefined_name_inside_a_quoted_type_is_only_a_hint(repo, capsys):
    repo.write("models.py", "x = 1\n")
    base = repo.commit("base")
    repo.write("models.py", MODELS)
    repo.commit()

    code = review(base)

    lines = capsys.readouterr().out.splitlines()
    hints = [line for line in lines if line.startswith("worth a look:") and "F821" in line]
    problems = [line for line in lines if not line.startswith("worth a look:") and "F821" in line]
    assert code == 1  # the unquoted ones are real
    assert len(hints) == 3, hints  # "User", Optional["Teacher"], "list[Pupil]"
    assert all("inside a quoted type" in line for line in hints)
    # Code inside an f-string is code: an undefined name there crashes at runtime.
    assert any("`Missing`" in line for line in problems), problems
    assert any("`Undefined`" in line for line in problems), problems


def test_a_file_that_does_not_parse_keeps_its_finding(tmp_path):
    broken = tmp_path / "broken.py"
    broken.write_text('a: "Gone" = 1\ndef (:\n', encoding="utf-8")

    # Cannot tell whether the name is quoted, so it is never turned into a hint.
    assert ruff.in_quotes(broken, 1, 5) is False
    assert ruff.in_quotes(tmp_path / "missing.py", 1, 1) is False


def test_a_quoted_name_is_told_apart_from_code_in_an_f_string(tmp_path):
    models = tmp_path / "models.py"
    models.write_text(MODELS, encoding="utf-8")
    lines = MODELS.splitlines()
    user = (lines.index('    user: Mapped["User"] = relationship()') + 1, 20)
    missing = (lines.index("    return f\"{Missing} and {'Quoted'}\"") + 1, 15)

    assert ruff.in_quotes(models, *user) is True
    assert ruff.in_quotes(models, *missing) is False


def test_a_name_right_before_a_string_is_not_inside_it(tmp_path):
    # ruff's column for `Y` is 6 (counted from 1); one character later is the quote.
    code = tmp_path / "code.py"
    code.write_text('x = [Y,"s"]\n', encoding="utf-8")

    assert ruff.in_quotes(code, 1, 6) is False
    assert ruff.in_quotes(code, 1, 9) is True  # the `s`


def test_non_ascii_earlier_on_the_line_does_not_shift_the_check(tmp_path):
    # ruff counts characters, Python's parser counts UTF-8 bytes: found by hand after the
    # fresh-agent check (it said "works" without a run). `ééé` is 3 characters, 6 bytes.
    code = tmp_path / "code.py"
    code.write_text('ééé: "Gone" = 1\nnaïve = [Y,"s"]\n', encoding="utf-8")

    assert ruff.in_quotes(code, 1, 7) is True  # `Gone`, as ruff reports it
    assert ruff.in_quotes(code, 2, 10) is False  # `Y`, not the string after it
