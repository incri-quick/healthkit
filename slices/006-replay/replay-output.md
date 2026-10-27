Scored AAs: 45 (tests-only and not-checked excluded)
Raw line overlap (NOT a score: counts coincidences): 29/45
Score A (judged, all rules): 11/45
Score B (judged, excluding rules derived from these AAs: exception-text-in-reply, raw-json-body, api-above-services): 9/45
By kind (B / A / scored): {'behaviour': '1/1/15', 'judgement': '0/0/4', 'knowledge': '0/0/13', 'pattern': '8/9/12', 'structure': '0/1/1'}

| AA | kind | judged | caught by | other findings on the changed lines | fix | title |
|---|---|---|---|---|---|---|
| AA-01 | knowledge | miss | - | - | 49d5dc8 | the emailed reset link works as a full API session |
| AA-02 | knowledge | miss | - | - | 49d5dc8 | any session token can reset the password without the old password |
| AA-03 | knowledge | miss | - | - | 4cf0801 | the reset-request throttle re-implements a shared helper, with three defects |
| AA-04 | knowledge | miss | - | - | 4dcd181 | change_password copies the password-write steps and skips one |
| AA-05 | judgement | miss | - | ruff I001 | 2252a17 | apply_password_set is in the wrong module |
| AA-06 | structure | caught (derived rule only) | import-linter api-above-services | ruff BLE001, ruff I001, ruff N814 | 4301ca4 | the service layer depends on the API layer |
| AA-09 | knowledge | miss | - | - | beb9780 | flag arguments nobody sets |
| AA-13 | pattern | caught | ruff RUF052 | - | 6bd4713 | _pca |
| AA-14 | judgement | miss | - | - | 27d9371 | pending, mint, build_body |
| AA-15 | pattern | caught | opengrep exception-text-in-reply, ruff BLE001 | - | b2ab10f | validate_password_match turns any exception into the reply text |
| AA-16 | judgement | miss | - | - | 4cf0801 | check_password_reset_rate_limit raises (a check_ that raises) |
| AA-18 | judgement | miss | - | - | 553c9ee | user-facing grammar |
| AA-19 | pattern | caught | ruff I001 | - | 1f78697 | import hygiene |
| AA-20 | pattern | miss | - | ruff I001 | 32c3e28 | docstrings and type hints |
| AA-22 | tests | miss | - | - | 4cf0801 | the reset throttle has one test |
| AA-26 | behaviour | miss | - | - | c6ff101 | inactive users get a reset email |
| AA-27 | knowledge | miss | - | ruff BLE001 | 3eebb3f, acc6f1a, 02903ea | nothing stops the next token mix-up (incl. an unchecked token reader) |
| AA-32 | pattern | caught | ruff F821 | ruff BLE001, ruff I001, ruff N806 | 198494c | dead auth code |
| AA-33 | behaviour | miss | - | - | 54efa2d | the Forgot-password limit is per address only, not per account |
| AA-35 | knowledge | miss | - | opengrep raw-json-body | 11bfaa9 | retire PATCH /users/change-password/ |
| AA-36 | knowledge | miss | - | ruff I001 | 6b784d3 | password writes that skip the stamp leave old sessions alive |
| AA-37 | behaviour | miss | - | ruff F401 | 1771d89 | a refresh token from before a password change still refreshes |
| AA-39 | tests | no Python lines changed in reviewed files | - | - | acc6f1a | a static guard for password writes (guard only) |
| AA-40 | behaviour | miss | - | ruff F401 | 0eb8d5c | refresh answers 500 for a deactivated or deleted account |
| AA-41 | behaviour | miss | - | - | 383d4ae | a password change does not cancel a half-finished MFA sign-in |
| AA-42 | knowledge | miss | - | opengrep raw-json-body | 3a6ed4c | unused /verifytoken/ that gave wrong answers |
| AA-43 | behaviour | miss | - | - | cb70080 | a re-hash at sign-in can undo a password change (race) |
| AA-44 | behaviour | miss | - | - | 02c0e4d | saving an old copy of a user undoes a password change |
| AA-47 | behaviour | miss | - | - | 978246f | an old copy undoes a deactivation, removal or demotion |
| AA-48 | behaviour | miss | - | - | 3eb56c0 | the profile edit can switch your own account off |
| AA-50 | behaviour | miss | - | ruff F401, ruff I001 | 61cf181, 193e224, b6018bc | self-edit without proof: password, email; old address not told |
| AA-56 | behaviour | miss | - | ruff BLE001, ruff F401 | 21c611c | confirm-your-password checks have no shared wrong-password limit |
| AA-58 | knowledge | miss | - | ruff BLE001, ruff F401, ruff I001, ruff PLC2701, ruff RUF052 | b595c34, 6834f76 | a second, unused Studio sign-in |
| AA-59 | pattern | caught | ruff BLE001 | opengrep raw-json-body, ruff RUF052 | 2e01db0 | token-encrypted echoed decryption errors to anonymous callers |
| AA-60 | behaviour | miss | - | opengrep raw-json-body, ruff BLE001, ruff RUF052 | 2e01db0 | Studio logout said logged out and ended nothing |
| AA-61 | knowledge | miss | - | opengrep raw-json-body, ruff BLE001, ruff RUF052 | 2e01db0 | five auth routes with no caller |
| AA-62 | knowledge | miss | - | ruff BLE001, ruff RUF052 | e65d779 | three sign-ins repeating the same steps |
| AA-63 | pattern | caught | ruff PLC2701 | ruff BLE001, ruff F401, ruff I001, ruff RUF052 | e65d779, 6834f76 | the Studio route imports private helpers from the users route file |
| AA-64 | knowledge | miss | - | ruff I001, ruff N814 | 81ca762 | the cookie-safety rule copied in several places |
| AA-65 | pattern | caught (derived rule only) | opengrep raw-json-body | - | 7dbb9e4 | routes parse the JSON body themselves |
| AA-66 | pattern | miss | - | - | 5910b4e | sign-in-area limits written as numbers in the code |
| AA-67 | pattern | caught | ruff RUF052 | ruff I001 | ca5c64e | /token/'s locals named like unused variables (_password, _ip) |
| AA-68 | pattern | miss | - | ruff I001, ruff RUF052 | ca5c64e | the licence error misspelt |
| AA-69 | pattern | caught | ruff N814 | ruff I001, ruff RUF052 | ca5c64e, 81ca762 | small style fixes (aliased local imports, a swallow-all except) |
| AA-71 | tests | miss | - | opengrep raw-json-body, ruff BLE001, ruff RUF052 | 2e01db0 | Studio sign-out pinned as a no-op by a test (test only) |
| AA-72 | tests | miss | - | - | 0559c9c | sign-out with a non-object body untested (test only) |
| AA-73 | behaviour | miss | - | ruff BLE001 | 28a3c0b | a form upload crashes routes that take JSON |
| AA-74 | behaviour | caught | ruff BLE001 | - | 4a45f36 | sign-out does not say whether it cancelled the token |
| AA-75 | behaviour | miss | - | opengrep raw-json-body | 7dbb9e4 | the profile edit stores any type as a name |
