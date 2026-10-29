"""Slice 016 mutants (run against tests/test_api_users.py, then tests/test_api_pack.py)."""

ST = "src/healthkit/tools/schemathesis.py"
API = "src/healthkit/apicheck.py"
CF = "src/healthkit/config.py"

MUTANTS = [
    ("real values are not passed on", ST,
     '    lines = ["[parameters]", *(f"{json.dumps(k)} = {json.dumps(v)}" for k, v in parameters)]\n',
     '    lines = ["[parameters]"]\n'),
    ("the project's values are not read", API,
     "        parameters = _settings().api_parameters\n", "        parameters = ()\n"),
    ("the users are not listed as peers", ST,
     '            f"peers = {json.dumps(users)}",\n', ""),
    ("the cross-user check is not asked for", ST,
     '        checks += ",object_level_authorization"\n', "        pass\n"),
    ("the token file is left behind", ST,
     "        (report_dir / AUTH_FILE).unlink(missing_ok=True)  # never leave a token behind\n",
     "        pass\n"),
    ("one user's token is not sent", ST,
     '    args += ["-H", f"Authorization: Bearer {tokens[0]}"] if len(tokens) == 1 else []\n',
     ""),
    ("bad values are accepted", CF,
     "        not isinstance(v, (str, int, float, bool)) for v in values.values()\n",
     "        False for v in values.values()\n"),
    ("the summary hides how many users", API,
     '    parts += [f"users: {len(tokens)} (cross-user reads checked)"] if len(tokens) > 1 else []\n',
     ""),
]
MUTANTS.append(
    ("allow entries are ignored", API,
     "    findings = [f for f in result.findings if not settings.allows(f)]\n",
     "    findings = list(result.findings)\n")
)
