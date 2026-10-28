"""A tiny two-user API for the API pack's tests (slice 016). Standard library only.

GET /notes             the caller's own notes
GET /notes/{note_id}   any note, to anyone: the cross-user read bug (no owner check)
GET /items/{item_id}   404 for every id except 7, which crashes (500): reachable only
                       with a real id, the way QuickRPA's routes 404 on guessed ids

python tenant_api.py <port>     tokens: "tok-a" (user a), "tok-b" (user b)
"""

import json
import sys
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
            }
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
    },
}


def app(environ, start_response):
    def reply(status, body):
        start_response(status, [("Content-Type", "application/json")])
        return [json.dumps(body).encode()]

    path = environ["PATH_INFO"]
    if path == "/openapi.json":
        return reply("200 OK", SCHEMA)
    user = TOKENS.get(environ.get("HTTP_AUTHORIZATION", ""))
    if not user:
        return reply("401 Unauthorized", {"detail": "auth"})
    last = path.rsplit("/", 1)[-1]
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
