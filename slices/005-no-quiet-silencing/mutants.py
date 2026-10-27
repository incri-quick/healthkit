"""Slice 005 mutants. Run: uv run python slices/mutate.py slices/005-no-quiet-silencing/mutants.py"""

RUFF = "src/healthkit/tools/ruff.py"
OPENGREP = "src/healthkit/tools/opengrep.py"
CLI = "src/healthkit/cli.py"
GITDIFF = "src/healthkit/gitdiff.py"
CONFIG = "src/healthkit/config.py"

MUTANTS = [
    ("migrations: whole folder excluded again", CONFIG,
     'DEFAULT_EXCLUDE = ("**/migrations/[0-9][0-9][0-9][0-9]_*.py",',
     'DEFAULT_EXCLUDE = ("**/migrations/**",'),
    ("glob: character classes taken literally", CONFIG,
     "    return re.compile(\"\".join(tokens.get(part, _literal_or_class(part)) for part in parts))",
     "    return re.compile(\"\".join(tokens.get(part, re.escape(part)) for part in parts))"),
    ("git: .gitattributes binary/-diff hide the lines again", GITDIFF, '        "--text",\n', ""),
    ("git: a textconv driver rewrites the diff again", GITDIFF, '        "--no-textconv",\n', ""),
    ("ruff reads the project's settings again", RUFF, '        "--isolated",\n', ""),
    ("ruff: suppressed findings never collected", RUFF,
     "        findings += [\n            dataclasses.replace(f, suppressed=True) for f in everything if f not in honoured\n        ]\n",
     ""),
    ("ruff: suppressed findings look like normal ones", RUFF,
     "dataclasses.replace(f, suppressed=True)", "dataclasses.replace(f, suppressed=False)"),
    ("opengrep honours nosemgrep again", OPENGREP, '"--disable-nosem", ', ""),
    ("opengrep: is_ignored not read", OPENGREP,
     'suppressed=bool(item["extra"].get("is_ignored")),', "suppressed=False,"),
    ("cli: suppressions silently dropped", CLI,
     '    approvals = [f"{path}" for path in referee_changes] + [\n'
     '        f"{f.path}:{f.line} suppresses {f.tool} {f.rule}" for f in suppressed\n    ]\n',
     '    approvals = [f"{path}" for path in referee_changes]\n'),
]
