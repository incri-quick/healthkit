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
    rules: tuple[Deny, ...],
    statuses: dict[str, dict[str, set[int]]],
    *,
    writes: bool,
    sizes: dict[str, dict[str, int]] | None = None,
) -> PolicyRun:
    """`statuses`: per user, per operation, what that user's login was answered.
    `sizes`: the largest 2xx answer's records, the same way (slice 022)."""
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
                size = (sizes or {}).get(rule.user, {}).get(operation)
                works = len(statuses) == 1 or _answered_someone(statuses, operation)
                _judge(run, rule, operation, answered[operation], size, compared=works)
    return run


def expected(rules: tuple[Deny, ...], given: list[str]) -> str | None:
    """Said before the run (slice 028): a teammate ran a whole pass before learning which
    users the rules expected. None when every one is given."""
    wanted = sorted({rule.user for rule in rules})
    if not (missing := [user for user in wanted if user not in given]):
        return None
    names = ", ".join(missing)
    flags = " ".join(f"--token-env {user}" for user in missing)
    return (
        f"access policy expects: {', '.join(wanted)}; not given: {names} "
        f"(add {flags}, or its rules are not checked)"
    )


def _answered_someone(statuses: dict[str, dict[str, set[int]]], operation: str) -> bool:
    """Did any user get a 2xx here? A route that refuses everyone (an allowed user's token
    without the permission, a broken route) proves nothing about the denied user (slice 028,
    QuickRPA: "if the approver token is wrong, its refusals look like passes"). The denied
    user's own 2xx never reaches this: it is a leak, judged first."""
    return any(
        200 <= code < 300  # noqa: PLR2004 - 2xx
        for answered in statuses.values()
        for code in answered.get(operation, set())
    )


def _judge(  # noqa: PLR0913 - each argument is one fact about the answer
    run: PolicyRun,
    rule: Deny,
    operation: str,
    codes: set[int],
    size: int | None,
    *,
    compared: bool,
) -> None:
    if leaked := sorted(code for code in codes if 200 <= code < 300):  # noqa: PLR2004 - 2xx
        # How big the answer was tells a real leak from an empty list (slice 022).
        amount = {None: "", 0: " (empty)", 1: " (1 record)"}.get(size, f" ({size} records)")
        message = f"{rule.user} got {leaked[0]}{amount}, the policy says refused: {rule.reason}"
        run.findings.append(
            Finding(tool="policy", rule="must-refuse", path=operation, line=0, message=message)
        )
    elif codes & REFUSED and not compared:
        run.unchecked.append(
            f"{operation} as {rule.user}: refused, but no user got a successful answer here, "
            "so the refusal proves nothing (is an allowed user's token set up?)"
        )
    elif codes & REFUSED:
        run.refused += 1
    else:
        answers = ", ".join(str(code) for code in sorted(codes))
        run.unchecked.append(f"{operation} as {rule.user}: answered only {answers}")
