"""Break code on purpose, one way at a time; every mutant must fail at least one test.

    uv run python slices/mutate.py slices/<slice>/mutants.py

The mutants file defines MUTANTS = [(name, file, old_text, new_text), ...]. Each mutant
edits one file, runs pytest, then restores the original byte for byte. A pattern that is
not found exactly once stops the run (a stale mutant must not pass silently).
"""

import runpy
import subprocess
import sys
from pathlib import Path

mutants = runpy.run_path(sys.argv[1])["MUTANTS"]
survivors = []
for name, file, old, new in mutants:
    path = Path(file)
    original = path.read_bytes()
    text = original.decode("utf-8")
    if text.count(old) != 1:
        sys.exit(f"mutant '{name}': pattern found {text.count(old)} times, expected 1")
    path.write_bytes(text.replace(old, new).encode("utf-8"))
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider"],
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        path.write_bytes(original)
    caught = result.returncode != 0
    last = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "(no output)"
    print(f"{'caught  ' if caught else 'SURVIVED'} {name}: {last}")
    if not caught:
        survivors.append(name)

sys.exit(1 if survivors else 0)
