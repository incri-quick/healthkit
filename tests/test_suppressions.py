"""A suppression on a changed line reaches a human (slice 005, D-018).

Cases come from the slice 004 repro (three silencing commits) and QuickRPA's real
justified suppression at users/api/users.py:288 (dev 7fadfe3).
"""

import pytest

from healthkit import cli

RAW_BODY = "import json\n\n\ndef f(request):\n    return json.loads(request.body){}\n"


def review(base):
    return cli.main(["review", "--base", base])


def test_a_new_noqa_with_a_code_needs_a_human(repo, capsys):
    repo.write("b.py", "x = 1\n")
    base = repo.commit("base")
    repo.write("b.py", "x = 1\nimport sys  # noqa: F401\n")
    repo.commit()

    assert review(base) == 3
    assert "needs human approval: b.py:2 suppresses ruff F401" in capsys.readouterr().out


def test_a_bare_noqa_needs_a_human(repo, capsys):
    repo.write("b.py", "x = 1\n")
    base = repo.commit("base")
    repo.write("b.py", "x = 1\nimport re  # noqa\n")
    repo.commit()

    assert review(base) == 3
    assert "needs human approval: b.py:2 suppresses ruff F401" in capsys.readouterr().out


def test_a_file_level_ruff_noqa_needs_a_human(repo, capsys):
    repo.write("d.py", "x = 1\n")
    base = repo.commit("base")
    repo.write("d.py", "# ruff: noqa\nx = 1\nimport json\n")
    repo.commit()

    assert review(base) == 3
    assert "needs human approval: d.py:3 suppresses ruff F401" in capsys.readouterr().out


def test_a_new_nosemgrep_needs_a_human(repo, capsys):
    repo.write("c.py", RAW_BODY.format("").replace("json.loads(request.body)", "request"))
    base = repo.commit("base")
    repo.write("c.py", RAW_BODY.format("  # nosemgrep"))
    repo.commit()

    assert review(base) == 3
    out = capsys.readouterr().out
    assert "needs human approval: c.py:5 suppresses opengrep raw-json-body" in out


def test_an_old_suppression_on_an_untouched_line_is_left_alone(repo, capsys):
    repo.write("b.py", "import sys  # noqa: F401\nx = 1\n")
    base = repo.commit("base")
    repo.write("b.py", "import sys  # noqa: F401\nx = 2\n")
    repo.commit()

    assert review(base) == 0
    assert "needs human approval" not in capsys.readouterr().out


def test_a_changed_line_that_keeps_its_noqa_needs_a_human(repo, capsys):
    # QuickRPA users/api/users.py:288: a justified suppression whose line changes.
    before = (
        "import logging\n\nlogger = logging.getLogger(__name__)\n\n\n"
        "def refresh(token):\n"
        "    try:\n"
        "        token.blacklist()\n"
        "    except Exception:  # noqa: BLE001 - refusing is the control; spending is cleanup\n"
        "        pass\n"
    )
    repo.write("users/api/users.py", before)
    base = repo.commit("base")
    repo.write(
        "users/api/users.py",
        before.replace("except Exception:  # noqa", "except Exception as exc:  # noqa").replace(
            "        pass\n", "        logger.warning('not spent: %s', type(exc).__name__)\n"
        ),
    )
    repo.commit()

    assert review(base) == 3
    out = capsys.readouterr().out
    assert "needs human approval: users/api/users.py:9 suppresses ruff BLE001" in out


def test_ignore_files_cannot_hide_a_changed_file(repo, capsys):
    repo.write(".semgrepignore", "e.py\n")
    repo.write(".opengrepignore", "e.py\n")
    repo.write("e.py", "x = 1\n")
    base = repo.commit("base")
    repo.write("e.py", RAW_BODY.format(""))
    repo.commit()

    assert review(base) == 1
    assert "e.py:5: [opengrep raw-json-body]" in capsys.readouterr().out


@pytest.mark.parametrize(
    "attributes",
    ["*.py binary\n", "*.py -diff\n", "*.py diff=hide\n"],
)
def test_git_attributes_cannot_hide_the_changed_lines(repo, capsys, attributes):
    # Found by hand in slice 005 (the verifier did not report it): with these attributes
    # git shows no changed lines, so the gate said "nothing to review", exit 0.
    repo.git("config", "diff.hide.textconv", "true")  # a textconv that prints nothing
    repo.write("a.py", "x = 1\n")
    base = repo.commit("base")
    repo.write(".gitattributes", attributes)
    repo.write("a.py", "x = 1\nimport os\n")
    repo.commit()

    assert review(base) == 1
    assert "a.py:2: [ruff F401]" in capsys.readouterr().out


def test_a_real_finding_outranks_a_suppression_and_both_are_shown(repo, capsys):
    repo.write("a.py", "x = 1\n")
    repo.write("b.py", "x = 1\n")
    base = repo.commit("base")
    repo.write("a.py", "x = 1\nimport os\n")
    repo.write("b.py", "x = 1\nimport sys  # noqa: F401\n")
    repo.commit()

    assert review(base) == 1
    out = capsys.readouterr().out
    assert "a.py:2: [ruff F401]" in out
    assert "needs human approval: b.py:2 suppresses ruff F401" in out
