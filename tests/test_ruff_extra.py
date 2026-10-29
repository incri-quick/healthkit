"""Slice 013: ruff checks a project chooses, and complexity for everyone (advisory)."""

from healthkit import cli

MAGIC = "def limit(x):\n    return x > 42\n"  # ruff PLR2004 when chosen
# Complexity 12 (> ruff's default 10): one branch per `if`.
COMPLEX = "def route(x):\n" + "".join(f"    if x == {i}:\n        return {i}\n" for i in range(11))
COMPLEX += "    return -1\n"


def review(base: str) -> int:
    return cli.main(["review", "--base", base])


def test_a_check_the_project_chose_is_reported(repo, capsys):
    repo.write(".healthkit/config.toml", '[ruff]\nextra = ["PLR2004"]\n')
    repo.write("app.py", "x = 1\n")
    base = repo.commit("base")
    repo.write("app.py", MAGIC)
    repo.commit()

    assert review(base) == 1
    assert "app.py:2: [ruff PLR2004]" in capsys.readouterr().out


def test_without_the_projects_choice_it_is_not(repo, capsys):
    repo.write("app.py", "x = 1\n")
    base = repo.commit("base")
    repo.write("app.py", MAGIC)
    repo.commit()

    assert review(base) == 0
    assert "PLR2004" not in capsys.readouterr().out


def test_a_malformed_choice_is_a_config_error(repo, capsys):
    for bad in ('extra = "PLR2004"', 'extra = ["PLR2004; rm"]', "extra = [42]", "extras = []"):
        repo.write(".healthkit/config.toml", f"[ruff]\n{bad}\n")
        repo.write("app.py", "x = 1\n")
        repo.commit()

        assert cli.main(["scan", "."]) == 2, bad
        assert "extra" in capsys.readouterr().err


def test_a_too_complex_function_is_worth_a_look_and_never_blocks(repo, capsys):
    repo.write("app.py", "x = 1\n")
    base = repo.commit("base")
    repo.write("app.py", COMPLEX)
    repo.commit()

    code = review(base)

    out = capsys.readouterr().out
    assert code == 0, out
    assert "worth a look: app.py:1: [ruff C901]" in out


def test_an_edit_deep_inside_a_complex_function_is_enough(repo, capsys):
    repo.write("app.py", COMPLEX)
    base = repo.commit("base")
    repo.write("app.py", COMPLEX.replace("return 9\n", "return 99\n"))  # line 20 of 24
    repo.commit()

    review(base)

    assert "worth a look: app.py:1: [ruff C901]" in capsys.readouterr().out
