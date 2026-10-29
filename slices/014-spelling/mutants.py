"""Slice 014 mutants (run against tests/test_spelling.py)."""

CS = "src/healthkit/tools/codespell.py"
CF = "src/healthkit/config.py"

MUTANTS = [
    ("typos block the run", CS, "message, advisory=True)", "message, advisory=False)"),
    ("short words are reported", CS,
     '            if match and len(match["word"]) >= MIN_LENGTH:\n', "            if match:\n"),
    ("hyphenated words are reported", CS, '"--ignore-regex", _HYPHENATED, "-L"', '"-L"'),
    ("valid variants are reported", CS, 'ACCEPTED = ("unparseable",)', 'ACCEPTED = ("x",)'),
    ("the project's words are ignored", CS,
     "(*ACCEPTED, *config.load(root).spelling_ignore))", "(*ACCEPTED,))"),
    ("the project's words keep their case", CS, "w.lower() for w in", "w for w in"),
    ("a failing codespell reads as a result", CS,
     "        if result.returncode not in (0, _FOUND):\n", "        if False:\n"),
    ("rare words are reported", CS, '"--builtin", "clear", ', ""),
    ("a malformed list is accepted", CF,
     "    if bad := [w for w in words if not isinstance(w, str) or not _WORD.fullmatch(w)]:\n",
     "    if False:\n"),
]
