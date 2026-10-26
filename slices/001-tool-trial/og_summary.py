"""Summarise an Opengrep JSON output by rule and area (slice 001 measurement)."""
import collections
import json
import sys
from pathlib import Path

raw_file = sys.argv[1]
show_rule = sys.argv[2] if len(sys.argv) > 2 else None
data = json.loads(Path(raw_file).read_text(encoding="utf-8"))
results = data["results"]
EXCLUDE = ("/tests/", "/migrations/", "/packages/", "bot starter kit", "/qrlib/", "test_", ".claude/")


def area(path: str) -> str:
    path = "/" + path.replace("\\", "/").lower()
    return "other" if any(part in path for part in EXCLUDE) else "app"


print(f"{raw_file}: {len(results)} findings, errors={len(data.get('errors', []))}")
by_rule = collections.Counter(r["check_id"].split(".")[-1] for r in results)
by_area = collections.Counter(area(r["path"]) for r in results)
print("  areas:", dict(by_area))
print("  rules:", ", ".join(f"{k}={v}" for k, v in by_rule.most_common(15)))
if show_rule:
    for r in results:
        if r["check_id"].endswith(show_rule) and area(r["path"]) == "app":
            path = r["path"].replace("\\", "/")
            print(f'   {path}:{r["start"]["line"]}  {r["extra"]["lines"].strip()[:100]}')
