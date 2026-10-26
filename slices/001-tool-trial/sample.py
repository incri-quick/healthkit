"""Stratified sample of ruff findings in app code, with the source line (slice 001).

Two findings per rule code, app code only (no tests, migrations, packages, starter kit),
picked deterministically (evenly spaced) so the sample can be reproduced.
"""
import json
import sys
from pathlib import Path

raw_file, per_code, *codes = sys.argv[1:]
findings = json.loads(Path(raw_file).read_text(encoding="utf-8"))
EXCLUDE = ("/tests/", "/migrations/", "/packages/", "bot starter kit", "/qrlib/")


def is_app_code(name: str) -> bool:
    name = name.replace("\\", "/").lower()
    return not any(part in name for part in EXCLUDE)


for code in codes:
    hits = [f for f in findings if f["code"] == code and is_app_code(f["filename"])]
    step = max(1, len(hits) // int(per_code))
    for finding in hits[::step][: int(per_code)]:
        path = Path(finding["filename"])
        row = finding["location"]["row"]
        line = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()[row - 1].strip()
        short = str(path).replace("\\", "/").split("quickrpa-integrated-backend/")[-1]
        print(f"{code:8} {short}:{row}\n         msg : {finding['message'][:100]}\n         code: {line[:110]}")
