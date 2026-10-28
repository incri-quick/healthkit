"""Slice 015 mutants (run against tests/test_options.py)."""

OP = "src/healthkit/tools/options.py"

MUTANTS = [
    ("it blocks the run", OP, "message, advisory=True, end_line=end)",
     "message, advisory=False, end_line=end)"),
    ("passing by keyword is not seen", OP,
     "            if any(option in keywords or count > position for keywords, count, _ in sites):\n",
     "            if any(count > position for keywords, count, _ in sites):\n"),
    ("passing by position is not seen", OP,
     "            if any(option in keywords or count > position for keywords, count, _ in sites):\n",
     "            if any(option in keywords for keywords, count, _ in sites):\n"),
    ("star callers are trusted", OP,
     "        if not sites or any(star for _, _, star in sites):\n", "        if not sites:\n"),
    ("never-called functions are reported", OP,
     "        if not sites or any(star for _, _, star in sites):\n",
     "        if any(star for _, _, star in sites):\n"),
    ("tests are not callers", OP,
     '        if not path.endswith(".py") or settings.is_excluded(path):\n',
     '        if not path.endswith(".py") or settings.is_excluded(path) or config.TEST_FILE.search(path):\n'),
    ("functions in tests are checked", OP, "        if not config.TEST_FILE.search(path)\n", ""),
    ("a body edit shows it", OP,
     "            end = node.body[0].lineno - 1 if node.body[0].lineno > node.lineno else node.lineno\n",
     "            end = node.end_lineno or node.lineno\n"),
    ("an unparsable file is skipped", OP, "        raise ToolError(msg) from exc\n",
     "        return ast.Module(body=[], type_ignores=[])\n"),
    ("keyword-only options have a position", OP, '(arg.arg, float("inf"), default)',
     "(arg.arg, 0, default)"),
    ("positions are miscounted", OP,
     "    found = [(name, position + first, default) for name, position, default in found]\n",
     "    found = [(name, position, default) for name, position, default in found]\n"),
]
