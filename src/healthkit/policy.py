"""The access policy: users that must be refused on routes (slice 021).

The project writes the rules (`[[api.deny]]`); healthkit checks them against what each
user was actually answered during `healthkit api`. It never decides who may see what.

- any 2xx answer to that user: a finding (`policy must-refuse`);
- else any 401 or 403: refused as required;
- else: not checked, with the reason. A 404 can be a guessed id as easily as a refusal,
  so it is never taken as proof.
A pattern that matches nothing tested is an error: a typo must never pass (L-004).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from healthkit.config import Deny, glob_match
from healthkit.findings import Finding

REFUSED = {401, 403}
READS = {"GET", "*"}


@dataclass
class PolicyRun:
    findings: list[Finding] = field(default_factory=list)
    refused: int = 0  # matched operations refused as required
    unchecked: list[str] = field(default_factory=list)  # "<route> as <user>: <why>"
    errors: list[str] = field(default_factory=list)


def check(
    rules: tuple[Deny, ...], statuses: dict[str, dict[str, set[int]]], *, writes: bool
) -> PolicyRun:
    """`statuses`: per user, per operation, what that user's login was answered."""
    run = PolicyRun()
    for rule in rules:
        if rule.user not in statuses:
            run.unchecked += [
                f"{r} as {rule.user}: not given with --token-env" for r in rule.routes
            ]
            continue
        answered = statuses[rule.user]
        for pattern in rule.routes:
            matched = sorted(op for op in answered if glob_match(op, pattern))
            if not matched:
                if not writes and pattern.split(" ", 1)[0] not in READS:
                    run.unchecked.append(
                        f"{pattern} as {rule.user}: reads only (add --allow-writes)"
                    )
                else:
                    run.errors.append(
                        f"[[api.deny]] {rule.user}: {pattern} matches no route tested as that user"
                    )
            for operation in matched:
                _judge(run, rule, operation, answered[operation])
    return run


def _judge(run: PolicyRun, rule: Deny, operation: str, codes: set[int]) -> None:
    if leaked := sorted(code for code in codes if 200 <= code < 300):  # noqa: PLR2004 - 2xx
        message = f"{rule.user} got {leaked[0]}, the policy says refused: {rule.reason}"
        run.findings.append(
            Finding(tool="policy", rule="must-refuse", path=operation, line=0, message=message)
        )
    elif codes & REFUSED:
        run.refused += 1
    else:
        answers = ", ".join(str(code) for code in sorted(codes))
        run.unchecked.append(f"{operation} as {rule.user}: answered only {answers}")
