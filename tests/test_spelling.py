"""Spelling (slice 014): clear-cut typos, advisory; words the project accepts are skipped."""

import sys

from healthkit import cli
from healthkit.tools import codespell

# QuickRPA studio_robot/api/robots.py:1172 at ca5c64e^ (Susheel #44, AA-68).
TYPO = 'def check():\n    raise ValueError(402, "Invalid liscense")\n'


def review_change(repo, before: str, after: str) -> int:
    repo.write("app.py", before)
    base = repo.commit("base")
    repo.write("app.py", after)
    repo.commit()
    return cli.main(["review", "--base", base])


def test_a_typo_in_a_message_is_worth_a_look_and_never_blocks(repo, capsys):
    code = review_change(repo, "x = 1\n", TYPO)

    out = capsys.readouterr().out
    assert code == 0, out
    assert "worth a look: app.py:2: [codespell spelling] 'liscense'" in out
    assert "license" in out


def test_short_words_hyphenated_words_and_valid_variants_are_not_reported(repo, capsys):
    # QuickRPA studio_workflow/api/workflow.py:1591 (`nd`), commons/storage_keys.py:705.
    after = (
        "def f(node_data):\n"
        "    nd = node_data\n"
        '    note = "a key is never re-used; unparseable input; a loner"\n'
        "    return nd, note\n"
    )

    review_change(repo, "x = 1\n", after)

    assert "codespell" not in capsys.readouterr().out.split("ran:")[0]


def test_a_word_the_project_accepts_is_not_reported(repo, capsys):
    # Capitalised on purpose: codespell's accept list is case-sensitive (measured).
    repo.write(".healthkit/config.toml", '[spelling]\nignore = ["Liscense"]\n')

    review_change(repo, "x = 1\n", TYPO)

    assert "liscense" not in capsys.readouterr().out


def test_a_malformed_accept_list_is_a_config_error(repo, capsys):
    for bad in ('ignore = "liscense"', "ignore = [42]", 'ignores = ["x"]'):
        repo.write(".healthkit/config.toml", f"[spelling]\n{bad}\n")
        repo.write("app.py", "x = 1\n")
        repo.commit()

        assert cli.main(["scan", "."]) == 2, bad
        assert "ignore" in capsys.readouterr().err


def test_a_failing_codespell_is_never_a_pass(repo, capsys, monkeypatch):
    fail = "import sys; print('boom', file=sys.stderr); sys.exit(3)"
    monkeypatch.setattr(codespell, "COMMAND", [sys.executable, "-c", fail])

    assert review_change(repo, "x = 1\n", TYPO) == 2
    assert "codespell failed (exit 3)" in capsys.readouterr().err


def test_a_missing_codespell_is_never_a_pass(repo, capsys, monkeypatch):
    monkeypatch.setattr(codespell, "COMMAND", ["no-such-codespell-healthkit-test"])

    assert review_change(repo, "x = 1\n", TYPO) == 2
    assert "codespell" in capsys.readouterr().err
