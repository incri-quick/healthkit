"""Clearer output (slice 025): `review` names what it hid on your lines (allowed, with the
reason, or baselined), and `scan` names the project checks it skipped. From a teammate:
"allowed: 1 and baselined: 1 don't name the finding, so I can't tell whether it's mine"."""

import json

from healthkit import cli

BLIND = "def g():\n    try:\n        return 1\n    except Exception:\n        return 0\n"
ALLOW = (
    '[[allow]]\nrule = "BLE001"\npath = "jobs.py"\n'
    'reason = "a background job must never die on one bad item"\n'
)


def review(base: str, *args: str) -> int:
    return cli.main(["review", "--base", base, *args])


def test_an_allowed_finding_on_your_lines_is_named_with_its_reason(repo, capsys):
    repo.write(".healthkit/config.toml", ALLOW)
    repo.write("jobs.py", "x = 1\n")
    base = repo.commit("base, with the exception approved")
    repo.write("jobs.py", BLIND)
    repo.commit()

    code = review(base)

    out = capsys.readouterr().out
    assert code == 0, out
    assert (
        "allowed: jobs.py:4: [ruff BLE001] Do not catch blind exception: `Exception` "
        "(reason: a background job must never die on one bad item)"
    ) in out
    assert "allowed: 1" in out  # the summary count stays


def test_a_baselined_finding_on_your_lines_is_named(repo, capsys):
    # Code moved into a block: its lines are "changed", its old problem is remembered.
    repo.write("pkg/a.py", "def f():\n    import os\n")
    repo.commit()
    cli.main(["baseline", "pkg"])
    base = repo.commit("baseline")
    repo.write("pkg/a.py", "def f(flag):\n    if flag:\n        import os\n")
    repo.commit()
    capsys.readouterr()

    code = review(base)

    out = capsys.readouterr().out
    assert code == 0, out
    assert "baselined: pkg/a.py:3: [ruff F401]" in out
    assert "baselined: 1" in out


def test_json_carries_what_was_hidden(repo, capsys):
    repo.write(".healthkit/config.toml", ALLOW)
    repo.write("jobs.py", "x = 1\n")
    base = repo.commit("base")
    repo.write("jobs.py", BLIND)
    repo.commit()

    review(base, "--format", "json")

    hidden = json.loads(capsys.readouterr().out)["hidden"]
    assert hidden == [
        {
            "kind": "allowed",
            "tool": "ruff",
            "rule": "BLE001",
            "path": "jobs.py",
            "line": 4,
            "message": "Do not catch blind exception: `Exception`",
            "reason": "a background job must never die on one bad item",
        }
    ]


def test_a_pull_request_comment_names_them_too(repo, capsys):
    repo.write(".healthkit/config.toml", ALLOW)
    repo.write("jobs.py", "x = 1\n")
    base = repo.commit("base")
    repo.write("jobs.py", BLIND)
    repo.commit()

    review(base, "--format", "markdown")

    out = capsys.readouterr().out
    assert "### Hidden on the changed lines" in out
    assert "allowed: jobs.py:4: [ruff BLE001]" in out


def test_an_allowed_finding_off_your_lines_is_not_listed(repo, capsys):
    repo.write(".healthkit/config.toml", ALLOW)
    repo.write("jobs.py", BLIND)
    base = repo.commit("base: the exception is old")
    repo.write("jobs.py", BLIND + "\n\ndef h():\n    return 2\n")
    repo.commit()

    review(base)

    assert "allowed:" not in capsys.readouterr().out


def test_scan_names_the_project_checks_it_did_not_run(repo, capsys):
    repo.write(
        ".healthkit/config.toml",
        '[[check]]\nname = "tenancy guard"\ncommand = ["python", "-V"]\nreason = "r"\n'
        '[[check]]\nname = "route table"\ncommand = ["python", "-V"]\nreason = "r"\n',
    )
    repo.write("pkg/a.py", "x = 1\n")
    repo.commit()

    cli.main(["scan", "pkg"])

    assert (
        "project checks are not run by scan: tenancy guard, route table (run healthkit review)"
        in capsys.readouterr().out
    )


def test_scan_says_nothing_about_checks_a_project_does_not_have(repo, capsys):
    repo.write("pkg/a.py", "x = 1\n")
    repo.commit()

    cli.main(["scan", "pkg"])

    assert "project checks" not in capsys.readouterr().out
