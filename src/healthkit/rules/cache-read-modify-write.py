# Fixtures for cache-read-modify-write.
# Real case: QuickRPA users/services/password_reset.py at 4cf0801^, line 49 (code review
# AA-03): get, compare, set. On the local stack with real Redis, 20 simultaneous requests
# from one address let 10-20 through instead of 5; the shared helper had already been made
# atomic, and this copy kept the old shape.


def check_password_reset_rate_limit(request, limit=5, window=3600):
    ip = client_ip(request)
    cache_key = f"rl:pw_reset:{ip}"
    count = cache.get(cache_key, 0)
    if count >= limit:
        raise PasswordResetError(429, "Too many requests. Please try again later.")
    # ruleid: cache-read-modify-write
    cache.set(cache_key, count + 1, timeout=window)


def failures_or_zero(key):
    failures = cache.get(key) or 0
    # ruleid: cache-read-modify-write
    cache.set(key, failures + 1, 300)


def counted_in_place(key):
    hits = cache.get(key, 0)
    hits += 1
    # ruleid: cache-read-modify-write
    cache.set(key, hits)


# Real fix: QuickRPA commons/cache_guard.py:113 cache_incr_window at 4cf0801^ (atomic).
def cache_incr_window(key, window, scope):
    try:
        # ok: cache-read-modify-write
        return cache.incr(key)
    except ValueError:
        pass
    cache.add(key, 1, timeout=window)
    return 1


def another_key(a, b):
    value = cache.get(a, 0)
    # ok: cache-read-modify-write
    cache.set(b, value + 1)


def not_a_counter(key, payload):
    previous = cache.get(key)
    # ok: cache-read-modify-write
    cache.set(key, payload)
    return previous
