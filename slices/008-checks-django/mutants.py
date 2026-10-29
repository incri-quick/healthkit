"""Slice 008 mutants. Run: uv run python slices/mutate.py slices/008-checks-django/mutants.py"""

CLI = "src/healthkit/cli.py"
CHECKS = "src/healthkit/checks.py"
DJ = "src/healthkit/tools/django.py"

MUTANTS = [
    # Project checks
    ("checks are read from the branch, not the base", CLI,
     "        approved = config.parse(gitdiff.file_at(root, base, config.CONFIG.as_posix()))\n",
     "        approved = settings\n"),
    ("checks run even when no matching file changed", CHECKS,
     "        if not any(glob_match(path, pattern) for path in changed for pattern in check.paths):\n",
     "        if False:\n"),
    ("a failing check reads as a pass", CHECKS, "        if code == 0:\n", "        if True:\n"),
    ("a check that cannot start is skipped quietly", CHECKS,
     '            result.errors.append(f"{label}: {exc}")\n',
     "            result.skipped.append(label)\n"),
    ("no time limit", CHECKS, "            timeout=check.timeout,\n", ""),
    # soft-delete-read
    ("flag inherited from a base class is ignored", DJ,
     "    return [cls, *(a for base in cls.bases for a in _ancestry(classes, base, seen | {name}))]\n",
     "    return [cls]\n"),
    ("a manager that filters is not recognised", DJ,
     "    if cls.queryset_names is not None:\n", "    if False:\n"),
    ("writes and projections are flagged", DJ,
     "    if not methods & _READS or methods & (_WRITES | _PROJECTIONS):\n",
     "    if not methods & _READS:\n"),
    ("the flag in the query is not seen", DJ,
     "        return names(node.arg) or (live and node.arg in soft.cleared)\n",
     "        return live and node.arg in soft.cleared\n"),
    ("a field the delete method clears is not seen", DJ,
     "        return names(node.arg) or (live and node.arg in soft.cleared)\n",
     "        return names(node.arg)\n"),
    ("test files are checked", DJ,
     "        if _TEST_FILE.search(path) or _NOT_CHECKED.search(path):\n",
     "        if _NOT_CHECKED.search(path):\n"),
    ("models only found in models.py", DJ,
     "        if not _MODEL_CLASS.search((root / path).read_bytes()):\n",
     '        if not path.endswith("models.py"):\n'),
    ("unreadable managers are hidden", DJ, "    if not unchecked:\n", "    if True:\n"),
    ("a model file that does not parse is skipped", DJ,
     "        raise ToolError(msg) from exc\n", "        return ast.Module(body=[], type_ignores=[])\n"),
    ("the advisory rule blocks the gate", DJ,
     "message, advisory=True))", "message))"),
    ("advisory findings block the gate", CLI,
     "    new = [f for f in not_allowed if not f.suppressed and not f.advisory]\n",
     "    new = [f for f in not_allowed if not f.suppressed]\n"),
]
