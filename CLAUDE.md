# CLAUDE.md — healthkit

healthkit is a code-health toolkit for Python projects: a pre-merge review gate and
a module health check. "healthkit" is a working name.

This project is built with AI assistance under the rules below. They exist because
the research on AI-written code (see DECISIONS.md, D-009) names eight things AI
reliably misses. Each rule answers one of them. They are not optional.

## The working agreement

| # | AI weakness | Rule |
|---|---|---|
| 1 | Unwritten rules | Nothing is built that is not written down first. Read DECISIONS.md before changing direction; record every new decision there. |
| 2 | Copies instead of reuse | Search before writing. Before adding a function, say what was searched for and why nothing existing fits. One tool per job. Core budget: about 1,500 lines; report the count after every slice. |
| 3 | Unhappy paths skipped | Every slice lists its failure modes before any code (not a git repo, tool missing, garbage tool output, Windows paths, huge diff, non-UTF-8 file). Each gets a test. |
| 4 | Unsafe defaults | No `shell=True`. Pin tool versions. No network by default. Never modify user files unless `--fix` is passed. |
| 5 | Tests that prove nothing | Tests first, shown failing before the code exists. Test data comes from real incidents, not invented examples. Never delete, skip or weaken a test without the owner's explicit OK. |
| 6 | Overconfidence | No "it works" without pasted command output. Each slice is checked by a fresh agent that tries to refute it, plus a real run on a real project. |
| 7 | Nobody understands the code | Slices stay under about 300 lines of diff. Each ends with: what, why, how to test, what is uncertain, one lesson. The owner reads the diff before commit. |
| 8 | Destructive actions | Feature branches only. Claude never pushes or merges. |

## The loop for every slice

1. **Spec**: goal, out of scope, failure modes, acceptance check. The owner approves.
2. **Test**: write tests from real cases; run them; show them failing.
3. **Build**: the minimum code that passes; search before writing.
4. **Prove**: tests green, healthkit run on its own repo, line count. Pasted output.
5. **Verify**: a fresh agent tries to refute it; a real run on a target project.
6. **Explain**: what changed, why, what is uncertain, one lesson (add to LEARNINGS.md).
7. **Review**: the owner reads the diff; commit on the branch.

## Stop and ask the owner when

- a test's expectation would change
- a dependency would be added
- a slice would exceed its budget
- a recorded decision would change
- anything is uncertain

## Evidence over opinion

Any agent's claim, including Claude's own, counts only when backed by output that
was actually run. A reviewing agent once "refuted" a real bug by misreading code;
a two-minute test settled it.

## Files

- `DECISIONS.md`: what was decided and why (append-only; supersede, never delete)
- `LEARNINGS.md`: what went wrong and what changed because of it
