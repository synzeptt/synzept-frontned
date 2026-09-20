from types import SimpleNamespace

import pytest
from starlette.requests import Request

from app.api import middleware


class _FakeRedis:
    shared_counts = {}

    def __init__(self):
        self.counts = self.shared_counts

    async def eval(self, _script, _key_count, key, window):
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]


class _FailingRedis:
    async def eval(self, *_args):
        raise ConnectionError("redis unavailable")


def _request(path="/api/test", client="198.51.100.10", authorization=None):
    headers = []
    if authorization:
        headers.append((b"authorization", authorization.encode()))
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": headers,
        "client": (client, 1234),
        "server": ("testserver", 80),
        "scheme": "http",
    }
    return Request(scope)


async def _ok(_request):
    return SimpleNamespace(status_code=200)


@pytest.mark.asyncio
async def test_redis_limit_rejects_after_existing_limit(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(middleware.settings, "rate_limit_per_minute", 2)
    limiter = middleware.RateLimitMiddleware(None, redis_client=fake)

    assert (await limiter._allow("key", 0)) is True
    assert (await limiter._allow("key", 1)) is True
    assert (await limiter._allow("key", 2)) is False


@pytest.mark.asyncio
async def test_requests_within_limit_succeed_and_excess_returns_429(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(middleware.settings, "rate_limit_per_minute", 2)
    limiter = middleware.RateLimitMiddleware(None, redis_client=fake)
    request = _request()

    assert (await limiter.dispatch(request, _ok)).status_code == 200
    assert (await limiter.dispatch(request, _ok)).status_code == 200
    assert (await limiter.dispatch(request, _ok)).status_code == 429


@pytest.mark.asyncio
async def test_redis_keys_are_shared_across_process_instances():
    fake = _FakeRedis()
    first = middleware.RateLimitMiddleware(None, redis_client=fake)
    second = middleware.RateLimitMiddleware(None, redis_client=fake)
    original_limit = middleware.settings.rate_limit_per_minute
    middleware.settings.rate_limit_per_minute = 2
    try:
        assert await first._allow("shared", 0)
        assert await second._allow("shared", 1)
        assert not await first._allow("shared", 2)
    finally:
        middleware.settings.rate_limit_per_minute = original_limit


@pytest.mark.asyncio
async def test_different_users_use_isolated_keys(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(middleware.settings, "rate_limit_per_minute", 1)
    limiter = middleware.RateLimitMiddleware(None, redis_client=fake)
    user_a = _request(authorization="Bearer user-a")
    user_b = _request(authorization="Bearer user-b")
    monkeypatch.setattr(middleware, "decode_token", lambda token, _type: {"sub": token})

    key_a = limiter._key(limiter._identity(user_a, "198.51.100.10"))
    key_b = limiter._key(limiter._identity(user_b, "198.51.100.10"))
    assert key_a != key_b
    assert await limiter._allow(key_a, 0)
    assert await limiter._allow(key_b, 0)


@pytest.mark.asyncio
async def test_redis_failure_fails_closed_when_configured(monkeypatch):
    limiter = middleware.RateLimitMiddleware(None, redis_client=_FailingRedis())
    request = _request()
    monkeypatch.setattr(middleware, "settings", SimpleNamespace(
        rate_limit_per_minute=120,
        rate_limit_window_seconds=60,
        redis_url="redis://test",
    ))

    response = await limiter.dispatch(request, _ok)

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_production_without_redis_fails_closed(monkeypatch):
    monkeypatch.setattr(middleware, "settings", SimpleNamespace(
        environment="production",
        redis_url="",
        rate_limit_per_minute=120,
        rate_limit_window_seconds=60,
    ))
    limiter = middleware.RateLimitMiddleware(None)

    response = await limiter.dispatch(_request(), _ok)

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_health_and_documentation_paths_remain_exempt(monkeypatch):
    monkeypatch.setattr(middleware.settings, "rate_limit_per_minute", 0)
    limiter = middleware.RateLimitMiddleware(None, redis_client=_FailingRedis())

    for path in ("/health", "/health/ready", "/docs", "/openapi.json", "/redoc"):
        response = await limiter.dispatch(_request(path=path), _ok)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_local_fallback_window_resets(monkeypatch):
    monkeypatch.setattr(middleware.settings, "rate_limit_per_minute", 1)
    monkeypatch.setattr(middleware.settings, "rate_limit_window_seconds", 60)
    limiter = middleware.RateLimitMiddleware(None)
    key = "local"

    assert await limiter._allow(key, 0)
    assert not await limiter._allow(key, 59)
    assert await limiter._allow(key, 60)