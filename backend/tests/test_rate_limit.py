from app.rate_limit import CREATE_SECRET_LIMIT, REVEAL_LIMIT, RequestRateLimiter


def test_rate_limit_bucket_hides_raw_scope_and_source() -> None:
    limiter = RequestRateLimiter(key=b"a" * 32)
    secret_id = "a" * 48
    source = "192.0.2.10"

    assert limiter.consume(scope=f"secret-code:{secret_id}", source=source, policy=CREATE_SECRET_LIMIT) is None

    serialized_keys = repr(limiter._events)
    assert secret_id not in serialized_keys
    assert source not in serialized_keys


def test_expired_buckets_are_cleaned_before_new_request() -> None:
    now = [0.0]
    limiter = RequestRateLimiter(key=b"b" * 32, clock=lambda: now[0])

    assert limiter.consume(scope="create", source="source-one", policy=CREATE_SECRET_LIMIT) is None
    assert len(limiter._events) == 1

    now[0] = 901.0
    assert limiter.consume(scope="reveal", source="source-two", policy=REVEAL_LIMIT) is None
    assert len(limiter._events) == 1
