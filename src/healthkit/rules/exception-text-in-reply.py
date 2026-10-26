# Fixtures for exception-text-in-reply.
# Real case: QuickRPA users/services/password_reset.py at 220f7b3, lines 218-224
# (code review AA-15): a database error's text, including host and port, was sent
# to the person resetting their password.


def validate_password_match(password, password_confirm, user=None):
    try:
        checkpassword(password=password, password_confirm=password_confirm, user=user)
    except HttpError as exc:
        # ok: exception-text-in-reply
        raise PasswordResetError(400, exc.message)
    except Exception as exc:
        # ruleid: exception-text-in-reply
        raise PasswordResetError(400, str(exc))


def handler(request):
    try:
        do_work()
    except Exception as e:
        # ruleid: exception-text-in-reply
        raise HttpError(500, str(e))


def view(request):
    try:
        do_work()
    except ValueError as err:
        # ruleid: exception-text-in-reply
        return {"error": str(err)}


def domain_error(org):
    # Real case: QuickRPA organization/utils.py:30 (dev 7fadfe3). Our own exception,
    # written to be shown to the user: not a leak.
    try:
        check_seat_limit(org)
    except SeatLimitExceeded as exc:
        # ok: exception-text-in-reply
        raise HttpError(402, str(exc))


def storage_error(bucket):
    # Real case: QuickRPA storage_buckets/services.py:164 (dev 7fadfe3). Anything the
    # storage client raises, endpoint details included, goes back to the caller.
    try:
        create_bucket(bucket)
    except Exception as exc:
        # ruleid: exception-text-in-reply
        raise HttpError(400, str(exc))


def safe(request):
    try:
        do_work()
    except Exception as exc:
        # ok: exception-text-in-reply
        logger.warning("work failed: %s", type(exc).__name__)
        raise HttpError(500, "Something went wrong")
