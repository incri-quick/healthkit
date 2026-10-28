"""Slice 018 mutants (run against tests/test_scorecard.py)."""

SC = "src/healthkit/scorecard.py"
PY = "src/healthkit/tools/pyscn.py"
CLI = "src/healthkit/cli.py"

MUTANTS = [
    ("sorted by name, not by need", SC,
     "    ordered = sorted(rows.values(), key=lambda r: (-r.too_complex, -r.problems, -r.lines))\n",
     "    ordered = sorted(rows.values(), key=lambda r: r.module)\n"),
    ("too-complex functions not counted", SC,
     '            found.too_complex += function["risk_level"] == "high"\n',
     "            found.too_complex += 0\n"),
    ("the most complex function not found", SC,
     '            if complexity > (found.most_complex or {"complexity": 0})["complexity"]:\n',
     "            if False:\n"),
    ("hints not counted", SC, "            found.hints += finding.advisory\n",
     "            found.hints += 0\n"),
    ("hints counted as problems", SC, "            found.problems += not finding.advisory\n",
     "            found.problems += 1\n"),
    ("suppressed findings counted", SC,
     "        if not finding.suppressed and (found := row(finding.path)):\n",
     "        if found := row(finding.path):\n"),
    ("test files counted", SC,
     "    return {path for path in files if not config.TEST_FILE.search(path)}\n",
     "    return set(files)\n"),
    ("a failing pyscn reads as a card", PY, "    if result.returncode != 0:\n", "    if False:\n"),
    ("paths not normalised (Windows)", PY,
     '    return raw.replace("\\\\", "/").removeprefix("./")\n', "    return raw\n"),
    ("a card shown after a tool failed", CLI,
     "    if run.failed:\n        return 2\n    scorecard.emit(card, fmt)\n",
     "    scorecard.emit(card, fmt)\n"),
]
MUTANTS += [
    ("files counted from pyscn's list, not healthkit's", SC, "        found.files += 1\n",
     "        found.files += 0\n"),
    ("a file's top-level code counted as a function", SC,
     '            continue  # a file\'s top-level code, reported as "<module>": not a function\n',
     "            pass\n"),
    ("no function shown as an empty cell", SC, 'if most else "-"', 'if most else ""'),
]
