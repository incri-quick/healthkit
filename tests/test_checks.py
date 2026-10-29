"""Project checks (slice 008): a project's own guard commands, run before push. Commands
come from the BASE branch's config, so a branch can never run a new command on the
reviewer's machine before a person approves it (D-018)."""

import sys
from pathlib import Path

from healthkit import cli

PY = Path(sys.executable).as_posix()


def check(name: str, script: str, *, paths: str = '["**/*.py"]', extra: str = "") -> str:
    return f"""\
[[check]]
name = "{name}"
command = ['{PY}', '-c', '{script}']
paths = {paths}
reason = "the project's own guard"
{extra}"""


def review(base: str) -> int:
    return cli.main(["review", "--base", base])


def branch_with(repo, config: str, change: str = "app.py") -> str:
    repo.write(".healthkit/config.toml", config)
    repo.write("app.py", "x = 1\n")
    repo.write("README.md", "hello\n")
    base = repo.commit("base")
    repo.write(change, "x = 2\n" if change.endswith(".py") else "changed\n")
    repo.commit()
    return base


def test_a_passing_check_runs_and_is_named(repo, capsys):
    base = branch_with(repo, check("guards", "print(1)"))

    assert review(base) == 0
    assert "check guards" in capsys.readouterr().out


def test_a_failing_check_is_one_finding_with_its_last_lines(repo, capsys):
    script = "import sys; print(chr(10).join(map(str, range(50)))); sys.exit(1)"
    base = branch_with(repo, check("guards", script))

    assert review(base) == 1
    out = capsys.readouterr().out
    assert out.count("[check guards]") == 1
    assert "failed (exit 1)" in out
    assert "    49" in out  # the last lines, where the reason usually is
    assert "    3\n" not in out  # not the whole output
    report = next(line for line in out.splitlines() if "full output:" in line)
    assert Path(report.split("full output: ")[1]).read_text(encoding="utf-8").startswith("0")


def test_a_check_that_cannot_start_is_never_a_pass(repo, capsys):
    config = check("guards", "x").replace(f"'{PY}'", "'no-such-program-healthkit'")
    base = branch_with(repo, config)

    assert review(base) == 2
    assert "guards" in capsys.readouterr().err


def test_a_check_that_runs_too_long_is_never_a_pass(repo, capsys):
    base = branch_with(repo, check("guards", "import time; time.sleep(30)", extra="timeout = 1\n"))

    assert review(base) == 2
    assert "timed out" in capsys.readouterr().err


def test_a_check_is_skipped_when_no_matching_file_changed(repo, capsys):
    base = branch_with(repo, check("guards", "import sys; sys.exit(1)"), change="README.md")

    assert review(base) == 0
    assert "check guards (no matching changes)" in capsys.readouterr().out


def test_a_check_added_by_the_branch_does_not_run(repo, capsys, tmp_path):
    marker = tmp_path / "ran.txt"
    repo.write("app.py", "x = 1\n")
    base = repo.commit("base")
    script = f'open(r"{marker}", "w").close()'
    repo.write(".healthkit/config.toml", check("sneaky", script))
    repo.write("app.py", "x = 2\n")
    repo.commit()

    assert review(base) == 3  # the config change needs a person
    assert not marker.exists()
    assert "needs human approval: .healthkit/config.toml" in capsys.readouterr().out


def test_a_check_changed_by_the_branch_runs_as_the_base_has_it(repo, capsys):
    base = branch_with(repo, check("guards", "import sys; sys.exit(1)"))
    repo.write(".healthkit/config.toml", check("guards", "print(1)"))  # "fixed" by the branch
    repo.commit("silence the guard")

    assert review(base) == 1  # the base's failing command ran
    assert "[check guards] failed" in capsys.readouterr().out


def test_a_check_without_a_reason_is_a_config_error(repo, capsys):
    config = check("guards", "print(1)").replace('reason = "the project\'s own guard"\n', "")
    base = branch_with(repo, config)

    assert review(base) == 2
    assert "reason" in capsys.readouterr().err


def test_a_command_written_as_one_string_is_a_config_error(repo, capsys):
    config = check("guards", "print(1)").replace(
        f"command = ['{PY}', '-c', 'print(1)']", f"command = '{PY} -c print(1)'"
    )
    base = branch_with(repo, config)

    assert review(base) == 2
    assert "command" in capsys.readouterr().err
