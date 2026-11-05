"""Project rules skip test files and keep their severity; a function passed along as a
value is not "never passed" (slice 027). From QuickRPA: its 8 project rules each repeated
a test-file exclusion, one rule's `severity: WARNING` was ignored, and
`asyncio.to_thread(execute_node, ..., execution_id=...)` was read as "never passed"."""

from healthkit import cli

RULE = """\
rules:
  - id: no-print
    pattern: print(...)
    message: no print in product code
    languages: [python]
    severity: {severity}
{metadata}"""

# QuickRPA users/api, the raw-json-body incident: a built-in rule marked WARNING.
SHARED_READER = """\
import json


def read_json_object(request):
    data = json.loads(request.body) if request.body else {}
    return data
"""

# QuickRPA studio_workflow: the node runs in a thread, every option passed through it.
EXECUTOR = """\
def execute_node(node, params, *, execution_id=None, meta_out=None):
    return node, params, execution_id, meta_out
"""
CALLER = """\
import asyncio

from engine import execute_node


async def run(node, params, run_id, meta):
    return await asyncio.to_thread(execute_node, node, params, execution_id=run_id, meta_out=meta)
"""


def rule(severity: str = "ERROR", metadata: str = "") -> str:
    return RULE.format(severity=severity, metadata=metadata)


def scan(capsys, *folders: str) -> tuple[int, str]:
    code = cli.main(["scan", *folders])
    return code, capsys.readouterr().out


def test_a_project_rule_skips_test_files(repo, capsys):
    repo.write(".healthkit/rules/print.yaml", rule())
    repo.write("app/a.py", "print(1)\n")
    repo.write("app/tests/test_a.py", "print(2)\n")
    repo.write("app/test_b.py", "print(3)\n")
    repo.commit()

    code, out = scan(capsys, "app")

    assert code == 1, out
    assert "app/a.py:1: [opengrep no-print]" in out
    assert "test_a.py" not in out
    assert "test_b.py" not in out


def test_a_rule_meant_for_tests_can_say_so(repo, capsys):
    repo.write(
        ".healthkit/rules/print.yaml", rule(metadata="    metadata:\n      healthkit-tests: true\n")
    )
    repo.write("app/a.py", "print(1)\n")
    repo.write("app/tests/test_a.py", "print(2)\n")
    repo.commit()

    _, out = scan(capsys, "app")

    assert "app/tests/test_a.py:1: [opengrep no-print]" in out


def test_a_warning_project_rule_is_worth_a_look(repo, capsys):
    repo.write(".healthkit/rules/print.yaml", rule("WARNING"))
    repo.write("app/a.py", "print(1)\n")
    repo.commit()

    code, out = scan(capsys, "app")

    assert code == 0, out  # a hint never fails the run (D-023)
    assert "worth a look: app/a.py:1: [opengrep no-print]" in out


def test_an_error_project_rule_is_a_problem(repo, capsys):
    repo.write(".healthkit/rules/print.yaml", rule("ERROR"))
    repo.write("app/a.py", "print(1)\n")
    repo.commit()

    code, out = scan(capsys, "app")

    assert code == 1, out
    assert "worth a look" not in out


def test_a_project_rule_with_a_built_in_id_is_still_a_project_rule(repo, capsys):
    # Found by the fresh agent (its log, 2026-11-05): told apart by id alone, a project
    # rule named like healthkit's own was taken for it and its WARNING ignored.
    repo.write(".healthkit/rules/mine.yaml", rule("WARNING").replace("no-print", "raw-json-body"))
    repo.write("app/a.py", "print(1)\n")
    repo.commit()

    code, out = scan(capsys, "app")

    assert code == 0, out
    assert "worth a look: app/a.py:1: [opengrep raw-json-body]" in out


def test_healthkits_own_rules_still_check_test_files(repo, capsys):
    # Unchanged on purpose: only project rules gained the test-file default.
    repo.write("users/tests/test_users.py", SHARED_READER)
    repo.commit()

    _, out = scan(capsys, "users")

    assert "users/tests/test_users.py:5: [opengrep raw-json-body]" in out


def test_healthkits_own_warning_rules_still_block(repo, capsys):
    repo.write("users/api/users.py", SHARED_READER)
    repo.commit()

    code, out = scan(capsys, "users")

    assert code == 1, out
    assert "users/api/users.py:5: [opengrep raw-json-body]" in out
    assert "worth a look: users/api/users.py:5" not in out


def test_a_function_passed_to_a_thread_is_not_never_passed(repo, capsys):
    repo.write("engine.py", EXECUTOR)
    repo.write("runner.py", CALLER)  # no direct call to execute_node anywhere
    repo.write("other.py", "from engine import execute_node\n\nexecute_node(1, 2)\n")
    repo.commit()

    _, out = scan(capsys, ".")

    assert "option-never-passed" not in out


def test_a_function_passed_as_a_keyword_value_is_silent_too(repo, capsys):
    repo.write("hooks.py", "def handler(event, *, retry=False):\n    return event, retry\n")
    repo.write("wire.py", "from hooks import handler\n\nhandler(1)\nsubscribe(callback=handler)\n")
    repo.commit()

    _, out = scan(capsys, ".")

    assert "option-never-passed" not in out


def test_a_function_only_ever_called_directly_is_still_reported(repo, capsys):
    repo.write("hooks.py", "def handler(event, *, retry=False):\n    return event, retry\n")
    repo.write("wire.py", "from hooks import handler\n\nhandler(1)\n")
    repo.commit()

    _, out = scan(capsys, ".")

    assert "option `retry` of handler() is never passed" in out
