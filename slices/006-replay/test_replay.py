"""Tests for the replay harness's own logic. Fixtures are real QuickRPA diffs (L-006).

Run: uv run pytest slices/006-replay/test_replay.py -q
"""

from pathlib import Path

from replay import is_hit, parse_old_lines

FIXTURES = Path(__file__).parent / "fixtures"


def test_changed_lines_are_read_from_the_old_side():
    # 6bd4713 renamed `_pca` on lines 24-25 of users/services/tokens.py (AA-13).
    old = parse_old_lines((FIXTURES / "diff-6bd4713.txt").read_text(encoding="utf-8"))

    assert old == {"users/services/tokens.py": {24, 25}}


def test_a_pure_insertion_gets_a_three_line_window():
    # 3eb56c0 only added lines after line 427 of studio_workflow/api/users.py (AA-48).
    old = parse_old_lines((FIXTURES / "diff-3eb56c0.txt").read_text(encoding="utf-8"))

    assert old == {"studio_workflow/api/users.py": set(range(424, 431))}


def test_a_hit_needs_the_same_file_and_a_changed_line():
    old = {"users/services/tokens.py": {24, 25}}

    assert is_hit(old, "users/services/tokens.py", 25)
    assert not is_hit(old, "users/services/tokens.py", 26)
    assert not is_hit(old, "users/services/login.py", 25)
