"""`review` never passes silently on uncommitted work (slice 023). Cases A-E are the ones
measured on 2026-11-04; every real-use source reported C ("nothing to review", exit 0
with the work uncommitted), and D and E were found while measuring it."""

import pytest

from healthkit import cli

GOOD = "def f():\n    return 1\n"
UNUSED_IMPORT = GOOD + "\n\ndef g():\n    import os\n    return 2\n"  # F401 on line 6
WITH_DOCSTRING = '"""Doc."""\n\n\n' + UNUSED_IMPORT  # the same F401, now on line 9


def review(base: str, *args: str) -> int:
    return cli.main(["review", "--base", base, *args])


def said(capsys) -> str:
    captured = capsys.readouterr()
    return captured.out + captured.err


@pytest.fixture
def base(repo):
    repo.write("a.py", GOOD)
    return repo.commit("base")


def test_a_committed_problem_with_a_clean_tree_is_found(repo, base, capsys):  # case A
    repo.write("a.py", UNUSED_IMPORT)
    repo.commit()

    assert review(base) == 1
    assert "a.py:6: [ruff F401]" in said(capsys)


@pytest.mark.parametrize("how", ["staged", "unstaged", "staged then edited"])
def test_uncommitted_work_alone_is_never_a_silent_pass(repo, base, capsys, how):  # case C
    repo.write("a.py", UNUSED_IMPORT if how != "staged then edited" else GOOD + "\n")
    if how != "unstaged":
        repo.git("add", "a.py")
    if how == "staged then edited":
        repo.write("a.py", UNUSED_IMPORT)

    code = review(base)

    out = said(capsys)
    assert code == 2, out
    assert "--working-tree" in out
    assert "a.py" in out


@pytest.mark.parametrize("how", ["staged", "unstaged", "staged then edited"])
def test_working_tree_mode_reviews_uncommitted_work(repo, base, capsys, how):
    repo.write("a.py", UNUSED_IMPORT if how != "staged then edited" else GOOD + "\n")
    if how != "unstaged":
        repo.git("add", "a.py")
    if how == "staged then edited":
        repo.write("a.py", UNUSED_IMPORT)

    code = review(base, "--working-tree")

    out = said(capsys)
    assert code == 1, out
    assert "a.py:6: [ruff F401]" in out
    assert "working tree (uncommitted changes included)" in out


def test_an_uncommitted_edit_cannot_hide_a_committed_problem(repo, base, capsys):  # case D
    repo.write("a.py", UNUSED_IMPORT)
    repo.commit()
    repo.write("a.py", WITH_DOCSTRING)  # uncommitted: moves the F401 from line 6 to 9

    code = review(base)

    out = said(capsys)
    assert code == 2, out  # was "no known problems", exit 0
    assert "a.py" in out
    assert "--working-tree" in out


def test_working_tree_mode_finds_it_where_it_now_is(repo, base, capsys):
    repo.write("a.py", UNUSED_IMPORT)
    repo.commit()
    repo.write("a.py", WITH_DOCSTRING)

    assert review(base, "--working-tree") == 1
    assert "a.py:9: [ruff F401]" in said(capsys)


def test_a_new_untracked_file_is_reviewed_in_working_tree_mode(repo, base, capsys):  # case B
    repo.write("new file.py", "import sys\n")  # a space in the name, as git quotes it

    assert review(base, "--working-tree") == 1
    assert "new file.py:1: [ruff F401]" in said(capsys)


def test_other_uncommitted_files_are_listed_but_do_not_change_the_verdict(
    repo, base, capsys
):  # case B, default mode
    repo.write("b.py", GOOD)
    repo.commit()  # a clean committed change
    repo.write("new file.py", "import sys\n")  # untracked, outside the review

    code = review(base)

    out = said(capsys)
    assert code == 0, out
    assert "not reviewed (uncommitted): 1 file(s)" in out
    assert "new file.py" in out


def test_an_ignored_untracked_file_is_never_reviewed(repo, base, capsys):
    repo.write(".gitignore", "build/\n")
    repo.commit()
    repo.write("build/gen.py", "import sys\n")

    code = review(base, "--working-tree")

    out = said(capsys)
    assert code == 0, out
    assert "build/gen.py" not in out


def test_an_uncommitted_deletion_does_not_crash(repo, base, capsys):
    (repo.root / "a.py").unlink()

    assert review(base, "--working-tree") == 0
    assert "Traceback" not in said(capsys)


@pytest.mark.parametrize("mode", [[], ["--working-tree"]])
def test_an_uncommitted_change_to_the_referee_needs_a_human(repo, base, capsys, mode):  # E
    repo.write("a.py", UNUSED_IMPORT)
    repo.commit()
    repo.write(".healthkit/config.toml", 'exclude = ["a.py"]\n')  # uncommitted, hides a.py

    code = review(base, *mode)

    out = said(capsys)
    assert code != 0, out  # was "nothing to review", exit 0
    assert "needs human approval" in out
    assert ".healthkit/config.toml" in out


def test_an_untracked_project_rule_needs_a_human(repo, base, capsys):
    repo.write(".healthkit/rules/mine.yaml", "rules: []\n")

    code = review(base, "--working-tree")

    out = said(capsys)
    assert code == 3, out
    assert ".healthkit/rules/mine.yaml" in out


def test_a_clean_branch_with_nothing_to_review_still_passes(base, capsys):
    assert review(base) == 0
    assert "nothing to review" in said(capsys)


def test_an_excluded_uncommitted_file_never_blocks_a_review(repo, capsys):
    repo.write(".healthkit/config.toml", 'exclude = ["generated/**"]\n')
    repo.write("a.py", GOOD)
    base = repo.commit("base, with the exclusion already approved")
    repo.write("b.py", GOOD)
    repo.commit()
    repo.write("generated/api.py", "import sys\n")  # regenerated, never committed

    code = review(base)

    out = said(capsys)
    assert code == 0, out
    assert "generated/api.py" not in out
