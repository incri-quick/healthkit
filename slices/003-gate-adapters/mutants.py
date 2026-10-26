"""Break the slice-003 code on purpose, one way at a time; every mutant must fail a test.

Run from the repo root: `uv run python slices/003-gate-adapters/mutants.py`.
Each mutant edits one file, runs pytest, then restores the original byte for byte.
"""

import subprocess
import sys
from pathlib import Path

MUTANTS = [
    ("opengrep ignores its errors list", "src/healthkit/tools/opengrep.py",
     "    if errors := data.get(\"errors\"):", "    if errors := []:"),
    ("opengrep reports the line after", "src/healthkit/tools/opengrep.py",
     "line=item[\"start\"][\"line\"],", "line=item[\"start\"][\"line\"] + 1,"),
    ("import-linter does not unwrap", "src/healthkit/tools/importlinter.py",
     "if joined and joined[-1].count(\"(\") > joined[-1].count(\")\"):", "if False:"),
    ("import-linter treats a config error as clean", "src/healthkit/tools/importlinter.py",
     "        raise ToolError(msg)\n    links", "        return []\n    links"),
    ("import-linter ignores package __init__", "src/healthkit/tools/importlinter.py",
     "path = module_file if (root", "path = module_file if True or (root"),
    ("cli reports a failed tool as a pass", "src/healthkit/cli.py",
     "    if failed:\n        return 2", "    if failed:\n        return 0"),
]

survivors = []
for name, file, old, new in MUTANTS:
    path = Path(file)
    original = path.read_bytes()
    text = original.decode("utf-8")
    if text.count(old) != 1:
        sys.exit(f"mutant '{name}': pattern found {text.count(old)} times, expected 1")
    path.write_bytes(text.replace(old, new).encode("utf-8"))
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider"],
            capture_output=True, text=True,
        )
    finally:
        path.write_bytes(original)
    caught = result.returncode != 0
    print(f"{'caught  ' if caught else 'SURVIVED'} {name}: {result.stdout.strip().splitlines()[-1]}")
    if not caught:
        survivors.append(name)

sys.exit(1 if survivors else 0)
