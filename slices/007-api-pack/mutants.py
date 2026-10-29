"""Slice 007 mutants. Run: uv run python slices/mutate.py slices/007-api-pack/mutants.py"""

ST = "src/healthkit/tools/schemathesis.py"
API = "src/healthkit/apicheck.py"

MUTANTS = [
    ("runs from the user's project folder", ST, "cwd=report_dir", "cwd=None"),
    ("500s never become findings", ST,
     "        for failure in data.get(\"failures\", [])\n",
     "        for failure in []\n"),
    ("non-local hosts allowed", ST,
     "        if host and host not in LOCAL_HOSTS and host not in allowed:\n",
     "        if False:\n"),
    ("everything refused for auth reads as a pass", ST,
     "    if refused and len(refused) * 2 > tested:\n", "    if False:\n"),
    ("any refused route fails the whole run again", ST,
     "    if refused and len(refused) * 2 > tested:\n", "    if refused:\n"),
    ("refused routes are not reported", API,
     "    if result.refused:  # never silent", "    if False:  # never silent"),
    ("an incomplete run reads as a pass", ST,
     "    if not data.get(\"complete\") or data.get(\"stop_reason\") != \"completed\":\n",
     "    if False:\n"),
    ("UTF-8 not forced (Windows console crash)", ST,
     "    env = {**os.environ, \"PYTHONUTF8\": \"1\"}", "    env = {**os.environ}"),
    ("the token is never sent", ST,
     "    args += [\"-H\", f\"Authorization: Bearer {token}\"] if token else []\n", ""),
    ("an unset token variable is ignored", API,
     "    if not token:\n        msg = f\"--token-env {name}: that environment variable is not set\"\n        raise ToolError(msg)\n",
     ""),
]
