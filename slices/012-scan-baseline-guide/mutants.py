"""Slice 012 mutants. Run against tests/test_scan.py (every mutant is in code it exercises):
uv run python slices/mutate.py slices/012-scan-baseline-guide/mutants.py (full suite, slow)."""

BL = "src/healthkit/baseline.py"
CLI = "src/healthkit/cli.py"

MUTANTS = [
    ("line numbers instead of line text", BL,
     "    return finding.tool, finding.rule, finding.path, _line(root, finding.path, finding.line)\n",
     "    return finding.tool, finding.rule, finding.path, str(finding.line)\n"),
    ("a second copy of a remembered line is hidden", BL,
     "        if left[key] > 0:\n", "        if key in left:\n"),
    ("fixed findings are never counted", BL,
     "    gone = sum(n for key, n in left.items() if scanned is not None and key[2] in scanned)\n",
     "    gone = 0\n"),
    ("a broken baseline reads as empty", BL, "        raise ConfigError(msg) from exc\n",
     "        return Counter()\n"),
    ("indentation counts as a change", BL,
     '    return lines[number - 1].strip() if 0 < number <= len(lines) else ""\n',
     '    return lines[number - 1] if 0 < number <= len(lines) else ""\n'),
    ("baselining one folder forgets the others", BL,
     "    kept = Counter({key: n for key, n in load(root).items() if key[2] not in scanned})\n",
     "    kept = Counter()\n"),
    ("review ignores the baseline", CLI,
     "    shown, remembered, _ = baseline.split(root, [f for f in not_allowed if not f.suppressed], known)\n",
     "    shown, remembered = [f for f in not_allowed if not f.suppressed], 0\n"),
    ("scan ignores the baseline", CLI,
     "    shown, remembered, gone = baseline.split(root, kept, known, files)\n",
     "    shown, remembered, gone = kept, 0, 0\n"),
    ("a baseline is written after a tool failed", CLI,
     '        if run.failed:  # an incomplete run must not become "how things are"\n',
     "        if False:\n"),
    ("a missing folder reads as no files", CLI, "        if not target.exists():\n",
     "        if False:\n"),
    ("other folders are scanned too", CLI,
     '            if (not prefix or p == prefix or p.startswith(prefix.rstrip("/") + "/"))\n',
     "            if True\n"),
    ("suppressions are not counted", CLI,
     '    parts += [f"suppressed: {suppressed}"] if suppressed else []\n', ""),
    ("a failed tool exits as a result", CLI,
     "    return 2 if run.failed else (1 if new else 0)\n",
     "    return 1 if new else 0\n"),
]
