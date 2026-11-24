"""SP_MAX_OPEN_ALERTS_PER_DEVICE is a bounded setting wired into the service limits."""
from dataclasses import replace
import json

from cryptography.hazmat.primitives.asymmetric import rsa
import jwt
import pytest

from security_platform.app import create_app
from security_platform.services.common import DEFAULT_LIMITS, ServiceLimits
from security_platform.settings import Settings


@pytest.fixture
def settings(tmp_path):
    public = jwt.algorithms.RSAAlgorithm.to_jwk(rsa.generate_private_key(public_exponent=65537, key_size=2048)
                                                .public_key(), as_dict=True)
    public.update(kid="alert-settings", alg="RS256", use="sig")
    jwks = tmp_path / "public-jwks.json"
    jwks.write_text(json.dumps({"keys": [public]}), encoding="utf-8")
    return Settings(database_url="postgresql+psycopg://unused:unused@127.0.0.1:1/test",
                    operator_issuer="https://issuer.example.test", operator_audience="platform", jwks_file=jwks)


def test_default_and_bounds(settings):
    assert settings.max_open_alerts_per_device == 500 == DEFAULT_LIMITS.max_open_alerts_per_device
    for value in (10, 100000):
        assert replace(settings, max_open_alerts_per_device=value).max_open_alerts_per_device == value
    for value in (9, 100001, 0, -1, True, "500", 500.0, None):
        with pytest.raises(ValueError, match="Invalid bounded platform setting"):
            replace(settings, max_open_alerts_per_device=value)
    with pytest.raises(ValueError, match="Invalid service limits"):
        ServiceLimits(max_open_alerts_per_device=0)


def test_environment_value_is_parsed_strictly(settings, monkeypatch):
    for name, value in (("SP_DATABASE_URL", settings.database_url), ("SP_OPERATOR_ISSUER", settings.operator_issuer),
                        ("SP_OPERATOR_AUDIENCE", settings.operator_audience), ("SP_JWKS_FILE", str(settings.jwks_file))):
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("SP_MAX_OPEN_ALERTS_PER_DEVICE", raising=False)
    assert Settings.from_environment().max_open_alerts_per_device == 500
    monkeypatch.setenv("SP_MAX_OPEN_ALERTS_PER_DEVICE", "25")
    assert Settings.from_environment().max_open_alerts_per_device == 25
    monkeypatch.setenv("SP_MAX_OPEN_ALERTS_PER_DEVICE", "many")
    with pytest.raises(ValueError, match="Invalid integer setting: SP_MAX_OPEN_ALERTS_PER_DEVICE"):
        Settings.from_environment()
    monkeypatch.setenv("SP_MAX_OPEN_ALERTS_PER_DEVICE", "9")
    with pytest.raises(ValueError, match="Invalid bounded platform setting"):
        Settings.from_environment()


def test_setting_reaches_the_application_service_limits(settings):
    app = create_app(replace(settings, max_open_alerts_per_device=42))
    try:
        assert app.state.limits.max_open_alerts_per_device == 42
        # The event cap stays its own setting.
        assert app.state.limits.max_events_per_device == settings.max_events_per_device
    finally:
        app.state.database.close()
