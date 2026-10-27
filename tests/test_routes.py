"""`healthkit routes` (slice 010): API routes no client calls. Routes come from OpenAPI;
callers are folders of client code, read as text. Fixture lines are real (QuickRPA
frontend, agent, qrlib, the runner installer), as are the incident routes."""

import json

from healthkit import cli

CALLERS = {
    # frontend src/components/Editor/EditorWrapper.jsx:145, :275
    "fe/src/Editor.jsx": (
        "const { data } = await axiosInstance.get(`robots/${id}/`);\n"
        "await axiosInstance.patch(`robots/${id}/robot-version/${robot.active_version.id}/`, f);\n"
    ),
    # frontend src/components/FileArtifactModal.tsx:184
    "fe/src/FileArtifactModal.tsx": (
        "const res = await fetch(`${getApiBase()}/api/v1/media/file-artifact/${workflowId}"
        "/${fileId}/download`, {\n"
    ),
    # frontend src/pages/Auth/ChangePassword/index.jsx:28 (AA-35: really called)
    "fe/src/ChangePassword.jsx": '      .patch("/users/change-password/", values)\n',
    # frontend src/pages/Auth/Login/index.jsx:184 (AA-61: only a comment names it)
    "fe/src/Login.jsx": (
        "// ADR-0020 MFA gate: /token/ (and /token-encrypted/) may answer 202 with\n"
        "/* also /check_refresh_token/ */ const ok = true;\n"
    ),
    # frontend HANDOVER.md (AA-42: only documentation names it)
    "fe/HANDOVER.md": "POST /api/v1/verifytoken/ checks a token\n",
    # agent src/main/connection/Enroller.ts:136
    "agent/src/Enroller.ts": "const url = `${scheme}://${baseUrl}/agent/v1/enroll`;\n",
    # agent deploy/install.sh:193 (AA-58: the installer still called it)
    "agent/deploy/install.sh": '    -X POST "${API}/api/v1/auth/login" \\\n',
    # qrlib/QRQueue.py:48
    "qrlib/QRQueue.py": 'path = f"/bot/queue/"\n# a comment: "/bot/never-called/"\n',
}
ROUTES = [
    ("get", "/api/v1/robots/{pk}/"),
    ("patch", "/api/v1/robots/{pk}/robot-version/{version_pk}/"),
    ("get", "/api/v1/media/file-artifact/{workflow_id}/{file_id}/download"),
    ("patch", "/api/v1/users/change-password/"),
    ("post", "/api/v1/token-encrypted/"),
    ("post", "/api/v1/check_refresh_token/"),
    ("post", "/api/v1/verifytoken/"),
    ("post", "/api/v1/auth/login"),
    ("post", "/api/v1/bot/queue/"),
    ("get", "/api/v1/bot/never-called/"),
]


def schema(routes) -> dict:
    paths: dict = {}
    for method, path in routes:
        paths.setdefault(path, {})[method] = {"responses": {"200": {"description": "ok"}}}
    return {"openapi": "3.0.3", "info": {"title": "t", "version": "1"}, "paths": paths}


AGENT = [("post", "/agent/v1/enroll")]  # a second API, its own schema (as QuickRPA's)


def run(repo, routes=ROUTES, callers=CALLERS, *extra: str) -> int:
    repo.write("openapi.json", json.dumps(schema(routes)))
    for path, text in callers.items():
        repo.write(f"clients/{path}", text)
    schemas = ["--schema", "openapi.json"]
    if routes is ROUTES:  # the full fixture: the agent's API comes with it
        repo.write("agent-openapi.json", json.dumps(schema(AGENT)))
        schemas += ["--schema", "agent-openapi.json"]
    return cli.main(["routes", *schemas, "--callers", "clients", *extra])


def uncalled(out: str) -> list[str]:
    return sorted(line.split()[-1] for line in out.splitlines() if line.startswith("no caller:"))


def test_paths_are_found_however_clients_write_them(repo, capsys):
    code = run(repo)

    assert uncalled(capsys.readouterr().out) == [
        "/api/v1/bot/never-called/",  # only inside a Python comment
        "/api/v1/check_refresh_token/",  # only inside a JS block comment
        "/api/v1/token-encrypted/",  # AA-61: only inside a JS comment
        "/api/v1/verifytoken/",  # AA-42: only in documentation
    ]
    assert code == 1


def test_concatenated_and_formatted_paths_are_found(repo, capsys):
    callers = {
        "a.js": 'get("/robots/" + id + "/export/")\n',
        "b.py": "get('/robots/%s/run/' % pk)\nget(\"/robots/{}/logs/\".format(pk))\n",
    }
    routes = [
        ("get", "/api/v1/robots/{pk}/export/"),
        ("post", "/api/v1/robots/{pk}/run/"),
        ("get", "/api/v1/robots/{pk}/logs/"),
    ]

    assert run(repo, routes, callers) == 0
    assert uncalled(capsys.readouterr().out) == []


def test_a_shorter_path_does_not_make_a_longer_route_called(repo, capsys):
    routes = [("get", "/api/v1/robots/"), ("post", "/api/v1/robots/{pk}/run/")]

    run(repo, routes, {"a.js": "axiosInstance.get(`robots/`)\n"})

    assert uncalled(capsys.readouterr().out) == ["/api/v1/robots/{pk}/run/"]


def test_a_caller_names_one_route_below_the_api_base_not_every_route_ending_alike(repo, capsys):
    # AA-61 measurement: frontend src/lib/signOut.ts calls '/logout/' (= /api/v1/logout/);
    # matching by ending alone also credited it to the unused /api/v1/auth/logout.
    routes = [("post", "/api/v1/logout/"), ("post", "/api/v1/auth/logout"), ("get", "/api/v1/x/")]

    run(repo, routes, {"signOut.ts": "await axiosInstance.post('/logout/');\n"})

    assert uncalled(capsys.readouterr().out) == ["/api/v1/auth/logout", "/api/v1/x/"]


def test_shell_variables_command_lines_and_variable_prefixes_are_read(repo, capsys):
    # QuickRPA precision sample (slice 010): three real callers the first matcher missed.
    callers = {
        # agent deploy/install.ps1:126
        "install.ps1": (
            '  $dl = Invoke-RestMethod -Method Get -Uri "$Api/api/v1/agents/agent/download'
            '?platform=windows" `\n'
        ),
        # agent deploy/install.sh:183
        "install.sh": '       "curl -fsSL ${API}/api/v1/agents/install.sh | sudo -E bash"\n',
        # frontend src/components/CredentialModal.tsx:550
        "CredentialModal.tsx": "                `${vaultPath}/create_vault`,\n",
        # agent src/python/nodes/supabase_node/node.py: Supabase's own API, not ours. An
        # ending after a variable that fits two routes identifies neither.
        "supabase_node.py": 'url = f"{self._auth_base()}/logout"\n',
        # frontend src/components/NodeDetailsModal.tsx:396: its `${node.id}` is a parameter,
        # so it names /nodes/{node_id}, not /nodes/bulk-delete
        "NodeDetailsModal.tsx": (
            "`${getApiBase()}/api/v1/workflows/${workflowId}/nodes/${node.id}`,\n"
        ),
    }
    routes = [
        ("patch", "/api/v1/workflows/{workflow_id}/nodes/{node_id}"),
        ("delete", "/api/v1/workflows/{workflow_id}/nodes/bulk-delete"),
        ("get", "/api/v1/agents/agent/download"),
        ("get", "/api/v1/agents/install.sh"),
        ("post", "/api/v1/vault/{workflow_id}/create_vault"),
        ("post", "/api/v1/logout/"),
        ("post", "/api/v1/auth/logout"),
    ]

    run(repo, routes, callers)

    assert uncalled(capsys.readouterr().out) == [
        "/api/v1/auth/logout",
        "/api/v1/logout/",
        "/api/v1/workflows/{workflow_id}/nodes/bulk-delete",
    ]


def test_same_file_constants_slash_twins_and_single_files_are_read(repo, capsys):
    # QuickRPA held-out sample (slice 010): four real callers still missed.
    callers = {
        # frontend src/components/CredentialModal.tsx:196 and :208
        "CredentialModal.tsx": (
            "    const vaultPath = `/api/v1/vault/${workflowId}`;\n"
            "    const data = await vaultRequest(`${vaultPath}/vaults`, 'Failed');\n"
        ),
        # qrlib/QRStorageBucket.py:75 and :82
        "QRStorageBucket.py": (
            '        path = f"/bot/storagebuckets/"\n'
            '            path = f"{path}{bucket_id}/bucket_data/"\n'
        ),
        # frontend src/services/nodePackageApi.ts:160 (the schema has /{slug} and /{slug}/),
        # and the delete call, whose `${...}` holds spaces and quotes
        "nodePackageApi.ts": (
            "fetch(`${getApiBase()}/api/v1/node-packages/${slug}/`, {\n"
            "fetch(`${getApiBase()}/api/v1/node-packages/${slug}${force ? '?force=true' : ''}`, {\n"
        ),
    }
    routes = [
        ("get", "/api/v1/vault/{workflow_id}/vaults"),
        ("get", "/api/v1/robot/{r}/vaults"),  # another route ending in "vaults"
        ("post", "/api/v1/bot/storagebuckets/{pk}/bucket_data/"),
        ("post", "/api/v1/robot/{r}/storagebuckets/{b}/bucket_data/"),
        ("delete", "/api/v1/node-packages/{slug}"),
        ("get", "/api/v1/node-packages/{slug}/"),
        ("post", "/api/v1/runs/pause/"),
        ("get", "/api/v1/docs-only/"),
    ]
    # studio_workflow/services/bot_export.py:1909: the generated bot calls it from code kept
    # inside a ''' template; a caller can be one file (the template lives in the backend).
    # A docstring that names a route in prose is not a caller.
    repo.write(
        "bot_export.py",
        '"""Builds the bot. POST /api/v1/docs-only/ is described here."""\n'
        "RUNTIME = '''\n"
        "def pause():\n"
        '    url = f"{QREnv.BASE_URL}/runs/pause/"\n'
        "'''\n",
    )

    run(repo, routes, callers, "--callers", "bot_export.py")

    assert uncalled(capsys.readouterr().out) == [
        "/api/v1/docs-only/",
        "/api/v1/robot/{r}/storagebuckets/{b}/bucket_data/",
        "/api/v1/robot/{r}/vaults",
    ]


def test_a_placeholder_holding_spaces_does_not_break_the_path(repo, capsys):
    # frontend src/services/nodePackageApi.ts: the delete call, alone, is the only caller
    callers = {
        "nodePackageApi.ts": (
            "fetch(`${getApiBase()}/api/v1/node-packages/${slug}${force ? '?force=true' : ''}`, {\n"
        )
    }

    run(repo, [("delete", "/api/v1/node-packages/{slug}"), ("get", "/api/v1/x/")], callers)

    assert uncalled(capsys.readouterr().out) == ["/api/v1/x/"]


def test_tests_and_dependencies_are_not_callers(repo, capsys):
    callers = {
        # frontend src/components/Editor/EditorWrapper.test.tsx calls the real component,
        # whose URL is a template (a literal id would never match a parameter anyway)
        "src/EditorWrapper.test.tsx": "mock.patch(`robots/${id}/robot-version/${v}/`);\n",
        "src/__tests__/x.js": 'get("robots/1/robot-version/2/")\n',
        "node_modules/lib/index.js": 'get("robots/1/robot-version/2/")\n',
        "src/app.js": "const x = 1;\n",
    }

    run(repo, [("patch", "/api/v1/robots/{pk}/robot-version/{v}/")], callers)

    assert uncalled(capsys.readouterr().out) == ["/api/v1/robots/{pk}/robot-version/{v}/"]


def test_the_output_says_it_matches_paths_not_methods(repo, capsys):
    run(repo)

    out = capsys.readouterr().out
    assert "no caller: POST /api/v1/verifytoken/" in out
    assert "4 of 11 path(s) have no known caller" in out
    assert "per path" in out  # a GET caller does not prove the PATCH on that path is used


def test_routes_called_from_outside_are_allowed_with_a_reason(repo, capsys):
    repo.write(
        ".healthkit/config.toml",
        '[[allow]]\nrule = "route-no-caller"\npath = "/api/v1/verifytoken/"\n'
        'reason = "called by a partner system, outside these repos"\n',
    )

    run(repo)

    out = capsys.readouterr().out
    assert "/api/v1/verifytoken/" not in uncalled(out)
    assert "allowed: 1" in out


def test_several_schemas_are_one_route_list(repo, capsys):
    repo.write("agent.json", json.dumps(schema([("get", "/agent/v1/nodes/")])))

    run(repo, ROUTES, CALLERS, "--schema", "agent.json")

    assert "/agent/v1/nodes/" in uncalled(capsys.readouterr().out)


def test_a_missing_or_empty_callers_folder_is_never_a_result(repo, capsys):
    repo.write("openapi.json", json.dumps(schema(ROUTES)))
    (repo.root / "empty").mkdir()

    assert cli.main(["routes", "--schema", "openapi.json", "--callers", "nowhere"]) == 2
    assert cli.main(["routes", "--schema", "openapi.json", "--callers", "empty"]) == 2
    assert "no client files" in capsys.readouterr().err


def test_an_unreadable_schema_is_never_a_result(repo, capsys):
    repo.write("clients/a.js", 'get("/robots/")\n')
    repo.write("broken.json", "{not json")

    assert cli.main(["routes", "--schema", "broken.json", "--callers", "clients"]) == 2
    assert cli.main(["routes", "--schema", "missing.json", "--callers", "clients"]) == 2
    assert "schema" in capsys.readouterr().err
