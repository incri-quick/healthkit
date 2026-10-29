"""Slice 013 mutants (run against tests/test_ruff_extra.py)."""

RF = "src/healthkit/tools/ruff.py"
CF = "src/healthkit/config.py"

MUTANTS = [
    ("the project's choice is ignored", RF,
     '    rules = ",".join([GATE_RULES, *ADVISORY, *config.load(root).ruff_extra])\n',
     '    rules = ",".join([GATE_RULES, *ADVISORY])\n'),
    ("complexity is never checked", RF, 'ADVISORY = {"C901"}\n', "ADVISORY = set()\n"),
    ("complexity blocks the run", RF, '    advisory = item["code"] in ADVISORY\n',
     "    advisory = False\n"),
    ("complexity covers only the def line", RF,
     "        end_line=_function_end(root / path, line) if advisory else 0,\n",
     "        end_line=0,\n"),
    ("any text passes as a rule code", CF, "not _RULE_CODE.fullmatch(code)\n",
     "not _RULE_CODE.match(code)\n"),
    ("a typo'd key is ignored", CF, '    _no_unknown_keys(table, known, f"[{name}]")\n', ""),
]
