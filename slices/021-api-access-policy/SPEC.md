# Slice 021: the access policy, "this user must be refused on these routes"

Status: **approved** (2026-10-29: "proceed then", after the question "is this the plan?":
a generic mechanism, the rules live in each project, D-022)

## Why (the school project's slice 019 run)

A teacher read all 400 students, all 469 parents, other teachers' attendance and a
parent-only page for a child outside her class. healthkit raised nothing: the cross-user
check (ST402) only asks "can B open an object A created?". Whether a ROLE may use a route
is project knowledge; only the project can say it. Today a person compares by hand.

healthkit still does not judge security: it checks rules a person wrote, as `[[check]]`
runs commands a person wrote.

## What we already measured (slices 019, 020)

The event log gives every response's status per operation, for requests that carried the
user's login, labelled `GET /notes/{note_id}` (the schema's own template).

## Design

```toml
[[api.deny]]
user = "HK_TEACHER"                  # a --token-env name
routes = ["GET /people/students", "GET /finances/**"]
reason = "teachers see only their own class"
```

For each rule and each tested operation its routes match (`*` one path segment, `**`
any):

- any **2xx** answer to that user: a finding, `[policy must-refuse]`. Exit 1.
- else any **401/403**: refused as required.
- else (only 404, 422, 500...): **not checked**, listed with the reason. A 404 can be a
  guessed id as easily as a refusal, so it never counts as proof.

Never silent:
- a pattern that matches no operation tested as that user is exit 2 (a typo must not
  pass), except a write route in a reads-only run, which is listed as not checked;
- a rule for a user not given with `--token-env` is listed as not checked.

Config strict, as the rest: `user`, `routes` (each `METHOD /path`, method may be `*`) and
`reason` required, unknown keys an error. `[[allow]]` with rule `must-refuse` works as for
every finding.

## Tests

On the two-user test API (user a: 403 on `/report`, 200 on any note): a refused route
passes; a 200 is a finding naming the user; a wildcard matches; an unmatched pattern is
exit 2; a write route in a reads-only run and a missing user are listed as not checked;
a route answering only 404 is not checked; malformed rules are a config error. Mutants.
