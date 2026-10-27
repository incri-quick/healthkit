"""Slice 004 mutants. Run: uv run python slices/mutate.py slices/004-project-config/mutants.py"""

CONFIG = "src/healthkit/config.py"
CLI = "src/healthkit/cli.py"
GITDIFF = "src/healthkit/gitdiff.py"

MUTANTS = [
    # globs
    ("glob: '*' crosses folders", CONFIG, '"*": "[^/]*"', '"*": ".*"'),
    ("glob: '**/' needs at least one folder", CONFIG, '"**/": "(?:.*/)?"', '"**/": ".*/"'),
    # allow entries
    ("allow: rule ignored, path only", CONFIG, "a.rule == finding.rule and ", ""),
    ("allow: path ignored, rule only", CONFIG, " and glob_match(finding.path, a.path)", ""),
    # exit priority and the human-approval flag
    ("exit: approval outranks findings", CLI,
     "    if new:\n        return 1\n    return 3 if referee_changes else 0",
     "    if referee_changes:\n        return 3\n    return 1 if new else 0"),
    ("referee: deletions not seen", GITDIFF, '"--no-renames",', '"--no-renames", "--diff-filter=AMR",'),
    ("referee: folder case must match", GITDIFF,
     "if name.casefold().startswith(prefix)", "if name.startswith(prefix)"),
    # exclusions applied to tool findings too (import-linter scans the whole project)
    ("exclude: not applied to findings", CLI, " and not settings.is_excluded(f.path)", ""),
]
