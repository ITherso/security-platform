from dataclasses import replace

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from security_platform.boundary import RequestBoundary
from security_platform.settings import Settings


@pytest.fixture
def settings(tmp_path):
    return Settings(database_url="postgresql+psycopg://unused:unused@127.0.0.1/test",
                    operator_issuer="https://issuer.example.test", operator_audience="platform",
                    jwks_file=tmp_path / "public.json")


def application(settings):
    app = FastAPI()
    calls = []
    @app.put("/api/v1/device/snapshot")
    def receive(payload: dict):
        calls.append(True)
        return {"accepted": True}
    @app.get("/api/v1/tenants")
    def tenants():
        calls.append(True)
        return []
    app.add_middleware(RequestBoundary, settings=settings)
    return app, calls


@pytest.mark.parametrize("body,status", [(b'{"x":1,"x":2}', 400), (b'{"x":NaN}', 400),
    (b'{"x":Infinity}', 400), (b"[" * 20 + b"0" + b"]" * 20, 400), (b"x" * 16385, 413)],
    ids=["duplicate", "nan", "infinity", "depth", "oversize"])
def test_json_rejected_before_route_without_echoing_input(settings, body, status):
    app, calls = application(settings)
    with TestClient(app, base_url="https://platform.example.test") as client:
        result = client.put("/api/v1/device/snapshot", content=body, headers={"Content-Type": "application/json"})
    assert result.status_code == status and calls == []
    assert body not in result.content
    assert result.headers["cache-control"] == "no-store"


def test_actual_stream_bytes_are_bounded_without_content_length(settings):
    app, calls = application(settings)
    def chunks():
        yield b" " * 10000
        yield b" " * 10000
    with TestClient(app, base_url="https://platform.example.test") as client:
        response = client.put("/api/v1/device/snapshot", content=chunks(), headers={"Content-Type": "application/json"})
    assert response.status_code == 413 and calls == []


def test_tls_has_no_unconfigured_plain_http_fallback(settings):
    app, calls = application(settings)
    with TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 50000)) as client:
        assert client.get("/api/v1/tenants", headers={"X-Forwarded-Proto": "https"}).status_code == 400
    assert calls == []


def test_explicit_test_http_only_allows_loopback_client_and_host(settings):
    app, calls = application(replace(settings, allow_loopback_http=True))
    with TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 50000)) as client:
        assert client.get("/api/v1/tenants").status_code == 200
        assert client.get("/api/v1/tenants", headers={"Host": "public.example.test"}).status_code == 400
    with TestClient(app, base_url="http://127.0.0.1", client=("192.0.2.1", 50000)) as client:
        assert client.get("/api/v1/tenants").status_code == 400
    assert len(calls) == 1


def test_duplicate_authorization_and_foreign_origin_are_rejected(settings):
    app, calls = application(settings)
    with TestClient(app, base_url="https://platform.example.test") as client:
        assert client.get("/api/v1/tenants", headers=[("Authorization", "Bearer a"), ("Authorization", "Bearer b")]).status_code == 400
        assert client.get("/api/v1/tenants", headers={"Origin": "https://foreign.example.test"}).status_code == 403
    assert calls == []


def test_request_budget_is_bounded_and_configured(settings):
    app, calls = application(replace(settings, requests_per_minute=1))
    with TestClient(app, base_url="https://platform.example.test") as client:
        assert client.get("/api/v1/tenants").status_code == 200
        assert client.get("/api/v1/tenants").status_code == 429
    assert len(calls) == 1


def test_false_content_length_and_compression_are_rejected(settings):
    app, calls = application(settings)
    with TestClient(app, base_url="https://platform.example.test") as client:
        assert client.put("/api/v1/device/snapshot", content=b"{}", headers={"Content-Length": "1", "Content-Type": "application/json"}).status_code == 400
        assert client.put("/api/v1/device/snapshot", content=b"{}", headers={"Content-Encoding": "gzip"}).status_code == 415
    assert calls == []


def test_missing_auth_settings_fail_closed(monkeypatch):
    monkeypatch.delenv("SP_OPERATOR_ISSUER", raising=False)
    monkeypatch.delenv("SP_DATABASE_URL", raising=False)
    with pytest.raises(ValueError, match="Missing required setting"):
        Settings.from_environment()
