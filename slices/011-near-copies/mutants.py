"""Slice 011 mutants. Run: uv run python slices/mutate.py slices/011-near-copies/mutants.py

(The full-suite harness takes ~3.5 min per mutant; slice 011 ran each mutant against the
tests that exercise its file: tests/test_copies.py for copies.py and findings.py,
tests/test_gate_tools.py for the rule. See RESULTS.md.)
"""

CP = "src/healthkit/tools/copies.py"
FN = "src/healthkit/findings.py"
RL = "src/healthkit/rules/cache-read-modify-write.yaml"

MUTANTS = [
    ("other files are never reported", CP, "        if not elsewhere:\n", "        if True:\n"),
    ("dunder functions count as helpers", CP,
     '        and not node.name.startswith("__")\n', ""),
    ("public functions count as helpers", CP,
     '        and node.name.startswith("_")\n', ""),
    ("methods count as helpers", CP,
     "        for node in tree.body\n", "        for node in ast.walk(tree)\n"),
    ("copies in test files count", CP,
     '        if not path.endswith(".py") or config.TEST_FILE.search(path) or settings.is_excluded(path):\n',
     '        if not path.endswith(".py") or settings.is_excluded(path):\n'),
    ("copies in excluded paths count", CP,
     '        if not path.endswith(".py") or config.TEST_FILE.search(path) or settings.is_excluded(path):\n',
     '        if not path.endswith(".py") or config.TEST_FILE.search(path):\n'),
    ("versions are never told apart", CP,
     "        versions = len({_shape(node)} | {shape for _, shape in elsewhere})\n",
     "        versions = 1\n"),
    ("a docstring counts as a different version", CP,
     "    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):\n",
     "    if False:\n"),
    ("the finding covers only the def line", CP, "advisory=True, end_line=end)",
     "advisory=True, end_line=0)"),
    ("the check blocks the gate", CP, "advisory=True, end_line=end)",
     "advisory=False, end_line=end)"),
    ("a line range is ignored", FN,
     "        return any(n in lines for n in range(self.line, max(self.line, self.end_line) + 1))\n",
     "        return self.line in lines\n"),
    ("an unparsable file is skipped", CP, "        raise ToolError(msg) from exc\n",
     "        return ast.Module(body=[], type_ignores=[])\n"),
    ("the rule misses the + 1 write", RL, "          - pattern: $C.set($K, $V + $N, ...)\n",
     "          - pattern: $C.set($K, $V - $N, ...)\n"),
    ("the rule misses `get(...) or 0`", RL,
     "          - pattern-inside: |\n              $V = $C.get($K, ...) or $D\n              ...\n",
     ""),
    ("the rule fires on another key", RL, "          - pattern: $C.set($K, $V + $N, ...)\n",
     "          - pattern: $C.set($J, $V + $N, ...)\n"),
]
