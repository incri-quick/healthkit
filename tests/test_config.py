"""`.healthkit/config.toml`: globs, defaults, and a strict loader (slice 004)."""

import re

import pytest

from healthkit import config
from healthkit.config import ConfigError, glob_match


@pytest.mark.parametrize(
    ("path", "pattern", "expected"),
    [
        # Real QuickRPA paths (dev 7fadfe3).
        ("users/migrations/0037_permission_override_nulls.py", "**/migrations/**", True),
        ("studio_workflow/migrations/0010_x.py", "**/migrations/**", True),
        ("commons/migrations_helper.py", "**/migrations/**", False),
        # Flask-Migrate / Alembic keep migrations at the top of the repo.
        ("migrations/versions/0001_initial.py", "**/migrations/**", True),
        ("src/healthkit/rules/raw-json-body.py", "src/healthkit/rules/*.py", True),
        ("src/healthkit/rules/sub/x.py", "src/healthkit/rules/*.py", False),
        (".healthkit/rules/no-local-workspace-lookup.py", ".healthkit/**", True),
        ("commons/payload.py", "commons/payload.py", True),
        ("Bot Starter Kit/app/bot.py", "Bot Starter Kit/**", True),
    ],
)
def test_glob(path, pattern, expected):
    assert glob_match(path, pattern) is expected


def write_config(tmp_path, text):
    (tmp_path / ".healthkit").mkdir(exist_ok=True)
    (tmp_path / ".healthkit" / "config.toml").write_text(text, encoding="utf-8")


def test_no_config_means_the_defaults(tmp_path):
    settings = config.load(tmp_path)

    assert settings.is_excluded("users/migrations/0001_initial.py")
    assert settings.is_excluded(".healthkit/rules/x.py")
    assert not settings.is_excluded("users/tests/test_login.py")  # test code is code
    assert settings.allow == ()


def test_project_exclusions_add_to_the_defaults_with_backslashes_normalised(tmp_path):
    write_config(tmp_path, 'exclude = ["src\\\\healthkit\\\\rules\\\\*.py"]\n')

    settings = config.load(tmp_path)

    assert settings.is_excluded("src/healthkit/rules/raw-json-body.py")
    assert settings.is_excluded("users/migrations/0001_initial.py")


def test_a_config_saved_with_a_byte_order_mark_is_read(tmp_path):
    # Windows editors add a BOM; refusing the whole review for it helps nobody.
    (tmp_path / ".healthkit").mkdir()
    (tmp_path / ".healthkit" / "config.toml").write_bytes(b'\xef\xbb\xbfexclude = ["build/**"]\n')

    assert config.load(tmp_path).is_excluded("build/x.py")


def test_invalid_toml_names_the_file(tmp_path):
    write_config(tmp_path, "exclude = [\n")

    with pytest.raises(ConfigError, match=re.escape("config.toml")):
        config.load(tmp_path)


def test_an_unknown_key_is_an_error_not_ignored(tmp_path):
    write_config(tmp_path, 'exlude = ["build/**"]\n')

    with pytest.raises(ConfigError, match="exlude"):
        config.load(tmp_path)


@pytest.mark.parametrize("reason", ["", "   "])
def test_an_allow_entry_needs_a_written_reason(tmp_path, reason):
    write_config(
        tmp_path,
        f'[[allow]]\nrule = "raw-json-body"\npath = "commons/payload.py"\nreason = "{reason}"\n',
    )

    with pytest.raises(ConfigError, match=re.escape("commons/payload.py")):
        config.load(tmp_path)


def test_an_allow_entry_without_a_reason_key_is_an_error(tmp_path):
    write_config(tmp_path, '[[allow]]\nrule = "raw-json-body"\npath = "commons/payload.py"\n')

    with pytest.raises(ConfigError, match="reason"):
        config.load(tmp_path)
