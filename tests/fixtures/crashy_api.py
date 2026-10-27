"""A tiny local API reproducing real QuickRPA crashes, for the API pack's tests (slice 007).

Standard library only. Routes:
  POST /profile  crashes (500) when first_name is not text or is very long  (AA-75)
  POST /token    crashes (500) on a body that is not JSON, e.g. a form upload (AA-73)
  POST /ok       validates and answers 422 on bad input: must never be a finding
  GET  /openapi.json

    python crashy_api.py <port> [--require-token TOKEN]
"""

import json
import sys
from wsgiref.simple_server import WSGIRequestHandler, make_server

NAME = {"type": "string", "maxLength": 150}
SCHEMA = {
    "openapi": "3.0.3",
    "info": {"title": "crashy", "version": "1"},
    "paths": {
        path: {
            "post": {
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {"first_name": NAME},
                                "required": ["first_name"],
                            }
                        }
                    },
                },
                "responses": {"200": {"description": "ok"}, "422": {"description": "bad"}},
            }
        }
        for path in ("/profile", "/token", "/ok", "/agent-only")
    },
}


def app(environ, start_response):  # noqa: PLR0911, C901 - one small test app
    def reply(status, body):
        start_response(status, [("Content-Type", "application/json")])
        return [json.dumps(body).encode()]

    path, method = environ["PATH_INFO"], environ["REQUEST_METHOD"]
    # Like QuickRPA's development settings (API_DOCS="public"): the schema is open,
    # the API routes need a login.
    if path == "/openapi.json" and method == "GET":
        return reply("200 OK", SCHEMA)
    # A route with its own login scheme, like QuickRPA's agent/bot routes: a bearer
    # token never opens it (measured: 18 such operations in the QuickRPA sweep).
    if path == "/agent-only":
        return reply("401 Unauthorized", {"detail": "agent token required"})
    token = environ.get("CRASHY_TOKEN")
    if token and environ.get("HTTP_AUTHORIZATION") != f"Bearer {token}":
        return reply("401 Unauthorized", {"detail": "auth"})
    length = int(environ.get("CONTENT_LENGTH") or 0)
    raw = environ["wsgi.input"].read(length) if length else b""
    if path == "/token":
        data = json.loads(raw)  # AA-73: anything that is not JSON crashes here
        return reply("200 OK", {"ok": bool(data)})
    try:
        data = json.loads(raw or b"{}")
    except ValueError:
        return reply("400 Bad Request", {"detail": "json"})
    if path == "/profile":
        name = data["first_name"] if isinstance(data, dict) else None
        if len(name.strip()) > 150:  # AA-75: a number has no .strip(); long text "fails"
            msg = "too long for the column"
            raise ValueError(msg)
        return reply("200 OK", {"first_name": name})
    if path == "/ok":
        name = data.get("first_name") if isinstance(data, dict) else None
        if not isinstance(name, str) or len(name) > 150:
            return reply("422 Unprocessable Entity", {"detail": "first_name"})
        return reply("200 OK", {"first_name": name})
    return reply("404 Not Found", {"detail": "no route"})


class _Quiet(WSGIRequestHandler):
    def log_message(self, *args):  # keep test output clean
        pass


if __name__ == "__main__":
    import os

    if "--require-token" in sys.argv:
        os.environ["CRASHY_TOKEN"] = sys.argv[sys.argv.index("--require-token") + 1]

    def with_env(environ, start_response):
        environ.setdefault("CRASHY_TOKEN", os.environ.get("CRASHY_TOKEN", ""))
        return app(environ, start_response)

    make_server("127.0.0.1", int(sys.argv[1]), with_env, handler_class=_Quiet).serve_forever()
