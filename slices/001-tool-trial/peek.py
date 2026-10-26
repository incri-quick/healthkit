"""Print findings of given codes from a raw ruff JSON output (slice 001 measurement)."""
import json
import sys
from pathlib import Path

raw_file, *codes = sys.argv[1:]
for finding in json.loads(Path(raw_file).read_text(encoding="utf-8")):
    if finding["code"] in codes:
        path = finding["filename"].replace("\\", "/").split("quickrpa-integrated-backend/")[-1]
        path = path.split("qrpa-pre-review/")[-1]
        print(f'{finding["code"]:7} {path}:{finding["location"]["row"]}  {finding["message"][:90]}')
