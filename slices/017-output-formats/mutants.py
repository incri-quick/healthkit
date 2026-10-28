"""Slice 017 mutants (run against tests/test_formats.py)."""

RP = "src/healthkit/report.py"

MUTANTS = [
    ("the format is ignored", RP,
     '    render = {"json": _json, "markdown": _markdown, "github": _github}.get(fmt, _text)\n',
     "    render = _text\n"),
    ("a format changes the exit code", RP, "    return report.exit\n", "    return 0\n"),
    ("json calls hints problems", RP, 'entry(f, "worth a look") for f', 'entry(f, "problem") for f'),
    ("json misreports the exit code", RP, '        "exit": report.exit,\n', '        "exit": 0,\n'),
    ("markdown drops the problems", RP, "    if report.problems:\n", "    if False:\n"),
    ("markdown drops the approvals", RP, "    if report.approvals:\n", "    if False:\n"),
    ("markdown claims safety", RP, 'a clean result never means "safe".', 'a clean result means "safe".'),
    ("github hints are errors", RP, 'github_line(f, "warning")', 'github_line(f, "error")'),
    ("github text is not escaped", RP,
     '    return text.replace("%", "%25").replace("\\r", "%0D").replace("\\n", "%0A")\n',
     "    return text\n"),
    ("github properties are not escaped", RP,
     '    return _data(text).replace(":", "%3A").replace(",", "%2C")\n',
     "    return _data(text)\n"),
]
MUTANTS.append(
    ("machine formats keep the console encoding", RP,
     '        sys.stdout.reconfigure(encoding="utf-8")\n', "        pass\n")
)
