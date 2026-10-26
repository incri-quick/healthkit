# Fixtures for raw-json-body.
# Real case: QuickRPA users/api/users.py at 220f7b3, line 230 (and 6 more routes)
# (code review AA-65): each route parsed the body itself; non-UTF-8 bytes and deep
# nesting were 500s, and the copies drifted apart.


def obtain_token(request, response):
    try:
        # ruleid: raw-json-body
        data = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        raise HttpError(400, "Invalid JSON body")


def refresh(request):
    # ruleid: raw-json-body
    payload = json.loads(request.body)


def good(request):
    # ok: raw-json-body
    data = read_json_object(request)


def unrelated(text):
    # ok: raw-json-body
    return json.loads(text)
