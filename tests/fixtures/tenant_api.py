"""A tiny two-user API for the API pack's tests (slices 016, 019). Standard library only.

GET /notes             the caller's own notes
GET /notes/{note_id}   any note, to anyone: the cross-user read bug (no owner check)
POST /notes            a write: never sent unless --allow-writes (slice 019)
GET /items/{item_id}   404 for every id except 7, which crashes (500): reachable only
                       with a real id, the way QuickRPA's routes 404 on guessed ids
GET /report            admin-only: user b crashes it (500), user a is refused (403)

python tenant_api.py <port> [log]    tokens: "tok-a" (user a), "tok-b" (user b);
                                     log: a file each request's method is added to
"""

import json
import sys
from pathlib import Path
from wsgiref.simple_server import WSGIRequestHandler, make_server

TOKENS = {"Bearer tok-a": "a", "Bearer tok-b": "b"}
NOTES = {1: {"id": 1, "owner": "a", "text": "a's note"}, 2: {"id": 2, "owner": "b", "text": "b's"}}
NOTE = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "owner": {"type": "string"},
        "text": {"type": "string"},
    },
}
SECURE = [{"bearer": []}]
ID = {"in": "path", "required": True, "schema": {"type": "integer"}}
SCHEMA = {
    "openapi": "3.0.3",
    "info": {"title": "tenants", "version": "1"},
    "components": {"securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}}},
    "paths": {
        "/notes": {
            "get": {
                "security": SECURE,
                "responses": {
                    "200": {
                        "description": "own notes",
                        "content": {
                            "application/json": {"schema": {"type": "array", "items": NOTE}}
                        },
                    }
                },
            },
            "post": {
                "security": SECURE,
                "requestBody": {"content": {"application/json": {"schema": NOTE}}},
                "responses": {"201": {"description": "created"}},
            },
        },
        "/notes/{note_id}": {
            "get": {
                "security": SECURE,
                "parameters": [{"name": "note_id", **ID}],
                "responses": {
                    "200": {
                        "description": "a note",
                        "content": {"application/json": {"schema": NOTE}},
                    },
                    "404": {"description": "no such note"},
                },
            }
        },
        "/items/{item_id}": {
            "get": {
                "security": SECURE,
                "parameters": [{"name": "item_id", **ID}],
                "responses": {"200": {"description": "ok"}, "404": {"description": "no"}},
            }
        },
        "/report": {
            "get": {
                "security": SECURE,
                "responses": {"200": {"description": "ok"}, "403": {"description": "admins"}},
            }
        },
    },
}
LOG = Path(sys.argv[2]) if len(sys.argv) > 2 else None  # the optional log file


def app(environ, start_response):  # noqa: C901, PLR0911 - one branch per route
    def reply(status, body):
        start_response(status, [("Content-Type", "application/json")])
        return [json.dumps(body).encode()]

    path, method = environ["PATH_INFO"], environ["REQUEST_METHOD"]
    if path == "/openapi.json":
        return reply("200 OK", SCHEMA)
    if LOG:
        with LOG.open("a", encoding="utf-8") as log:
            log.write(method + "\n")
    user = TOKENS.get(environ.get("HTTP_AUTHORIZATION", ""))
    if not user:
        return reply("401 Unauthorized", {"detail": "auth"})
    last = path.rsplit("/", 1)[-1]
    if path == "/report":
        if user == "a":
            return reply("403 Forbidden", {"detail": "admins only"})
        msg = "the admin report crashes"
        raise RuntimeError(msg)
    if path == "/notes" and method == "POST":
        return reply("201 Created", {"id": 3})
    if path == "/notes":
        return reply("200 OK", [n for n in NOTES.values() if n["owner"] == user])
    if path.startswith("/notes/") and last.isdigit() and int(last) in NOTES:
        return reply("200 OK", NOTES[int(last)])  # the bug: nobody checks the owner
    if path.startswith("/items/") and last == "7":
        msg = "only a real id reaches this"
        raise RuntimeError(msg)
    return reply("404 Not Found", {"detail": "no"})


class _Quiet(WSGIRequestHandler):
    def log_message(self, *args):  # keep test output clean
        pass


if __name__ == "__main__":
    make_server("127.0.0.1", int(sys.argv[1]), app, handler_class=_Quiet).serve_forever()
