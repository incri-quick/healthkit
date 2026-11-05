"""A new copy of a line the baseline remembers is never hidden (slice 026). Found while
checking slice 025: with `import os` remembered twice, a third copy added by the branch
was reported as "baselined", exit 0."""

from healthkit import cli

TWO = "def f():\n    import os\n\n\ndef h():\n    import os\n"  # F401 on lines 2 and 6
THREE = TWO + "\n\ndef k():\n    import os\n"  # a third copy, line 10


def remembered(repo, text: str) -> str:
    """Commit `text` as pkg/a.py, baseline it, commit the baseline; return that commit."""
    repo.write("pkg/a.py", text)
    repo.commit("code")
    cli.main(["baseline", "pkg"])
    return repo.commit("baseline")


def review(base: str) -> int:
    return cli.main(["review", "--base", base])


def test_a_third_copy_of_a_twice_remembered_line_is_new(repo, capsys):
    base = remembered(repo, TWO)
    capsys.readouterr()
    repo.write("pkg/a.py", THREE)
    repo.commit()

    code = review(base)

    out = capsys.readouterr().out
    assert code == 1, out  # was "baselined", exit 0
    assert "pkg/a.py:10: [ruff F401]" in out
    assert "one more copy of a line the baseline remembers 2 time(s)" in out
    assert "baselined: pkg/a.py:10" not in out


def test_a_remembered_line_that_moved_is_still_remembered(repo, capsys):
    base = remembered(repo, TWO)
    capsys.readouterr()
    repo.write("pkg/a.py", "x = 1\n\n\n" + TWO)  # both copies move down 3 lines
    repo.commit()

    code = review(base)

    out = capsys.readouterr().out
    assert code == 0, out
    assert not [line for line in out.splitlines() if line.startswith("pkg/a.py:")]


def test_one_copy_removed_and_one_added_elsewhere_is_not_new(repo, capsys):
    base = remembered(repo, TWO)
    capsys.readouterr()
    repo.write(
        "pkg/a.py",
        "def f():\n    import os\n\n\ndef h():\n    return 1\n\n\ndef k():\n    import os\n",
    )
    repo.commit()

    code = review(base)

    out = capsys.readouterr().out
    assert code == 0, out  # still two copies: the count, not the place, is remembered


def test_a_copy_in_a_file_with_none_remembered_has_no_note(repo, capsys):
    base = remembered(repo, "x = 1\n")
    capsys.readouterr()
    repo.write("pkg/a.py", "import os\n")
    repo.commit()

    assert review(base) == 1
    out = capsys.readouterr().out
    assert "pkg/a.py:1: [ruff F401]" in out
    assert "one more copy" not in out


def test_scan_says_which_copy_is_new_cannot_be_told(repo, capsys):
    remembered(repo, TWO)
    capsys.readouterr()
    repo.write("pkg/a.py", THREE)
    repo.commit()

    code = cli.main(["scan", "pkg", "--format", "json"])

    out = capsys.readouterr().out
    assert code == 1, out
    assert "one more copy of a line the baseline remembers 2 time(s)" in out
