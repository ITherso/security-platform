"""SP_MAX_OPEN_ALERTS_PER_DEVICE is a bounded setting wired into the service limits; SP_SILENCE_ALERT_SECONDS
is the bounded setting of `security-platform sweep`."""
from dataclasses import replace
import json

from cryptography.hazmat.primitives.asymmetric import rsa
import jwt
import pytest

from security_platform.app import create_app
from security_platform.services.common import DEFAULT_LIMITS, ServiceLimits
from security_platform.settings import (DEFAULT_SILENCE_ALERT_SECONDS, SILENCE_ALERT_SECONDS_RANGE, Settings,
    max_open_alerts_from_environment, silence_alert_seconds_from_environment)


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


# The HTTP server's operator settings: the sweep needs none of them.
OPERATOR_SETTINGS = ("SP_DATABASE_URL", "SP_OPERATOR_ISSUER", "SP_OPERATOR_AUDIENCE", "SP_JWKS_FILE", "SP_ALLOWED_HOSTS",
                     "SP_ALLOW_LOOPBACK_HTTP")


def required_environment(settings, monkeypatch):
    for name, value in (("SP_DATABASE_URL", settings.database_url), ("SP_OPERATOR_ISSUER", settings.operator_issuer),
                        ("SP_OPERATOR_AUDIENCE", settings.operator_audience), ("SP_JWKS_FILE", str(settings.jwks_file))):
        monkeypatch.setenv(name, value)


def test_silence_setting_default_and_bounds(settings):
    assert (DEFAULT_SILENCE_ALERT_SECONDS, SILENCE_ALERT_SECONDS_RANGE) == (900, (300, 86400))
    assert settings.silence_alert_seconds == 900
    for value in (300, 86400):
        assert replace(settings, silence_alert_seconds=value).silence_alert_seconds == value
    for value in (299, 86401, 0, -1, True, "900", 900.0, None):
        with pytest.raises(ValueError, match="Invalid bounded platform setting"):
            replace(settings, silence_alert_seconds=value)


def test_silence_setting_is_parsed_strictly_from_the_environment(settings, monkeypatch):
    required_environment(settings, monkeypatch)
    monkeypatch.delenv("SP_SILENCE_ALERT_SECONDS", raising=False)
    assert Settings.from_environment().silence_alert_seconds == 900
    monkeypatch.setenv("SP_SILENCE_ALERT_SECONDS", "1800")
    assert Settings.from_environment().silence_alert_seconds == 1800
    for value in ("many", "900.0", "1e3"):
        monkeypatch.setenv("SP_SILENCE_ALERT_SECONDS", value)
        with pytest.raises(ValueError, match="Invalid integer setting: SP_SILENCE_ALERT_SECONDS"):
            Settings.from_environment()
    for value in ("299", "86401"):
        monkeypatch.setenv("SP_SILENCE_ALERT_SECONDS", value)
        with pytest.raises(ValueError, match="Invalid bounded platform setting"):
            Settings.from_environment()


def test_the_sweep_reads_its_two_settings_without_the_servers_operator_settings(monkeypatch):
    for name in OPERATOR_SETTINGS + ("SP_SILENCE_ALERT_SECONDS", "SP_MAX_OPEN_ALERTS_PER_DEVICE"):
        monkeypatch.delenv(name, raising=False)
    assert (silence_alert_seconds_from_environment(), max_open_alerts_from_environment()) == (900, 500)
    for value in ("300", "86400"):
        monkeypatch.setenv("SP_SILENCE_ALERT_SECONDS", value)
        assert silence_alert_seconds_from_environment() == int(value)
    for value in ("299", "86401", "0", "-1"):
        monkeypatch.setenv("SP_SILENCE_ALERT_SECONDS", value)
        with pytest.raises(ValueError, match="Invalid bounded platform setting"):
            silence_alert_seconds_from_environment()
    for value in ("many", "900.0", "1e3"):
        monkeypatch.setenv("SP_SILENCE_ALERT_SECONDS", value)
        with pytest.raises(ValueError, match="Invalid integer setting: SP_SILENCE_ALERT_SECONDS"):
            silence_alert_seconds_from_environment()
    monkeypatch.setenv("SP_MAX_OPEN_ALERTS_PER_DEVICE", "10")
    assert max_open_alerts_from_environment() == 10
    monkeypatch.setenv("SP_MAX_OPEN_ALERTS_PER_DEVICE", "9")
    with pytest.raises(ValueError, match="Invalid bounded platform setting"):
        max_open_alerts_from_environment()
    monkeypatch.setenv("SP_MAX_OPEN_ALERTS_PER_DEVICE", "many")
    with pytest.raises(ValueError, match="Invalid integer setting: SP_MAX_OPEN_ALERTS_PER_DEVICE"):
        max_open_alerts_from_environment()


def test_the_sweep_helpers_read_what_the_server_settings_read(settings, monkeypatch):
    required_environment(settings, monkeypatch)
    for value in ("300", "901", "86400"):
        monkeypatch.setenv("SP_SILENCE_ALERT_SECONDS", value)
        assert Settings.from_environment().silence_alert_seconds == silence_alert_seconds_from_environment() == int(value)
    for value in ("10", "77", "100000"):
        monkeypatch.setenv("SP_MAX_OPEN_ALERTS_PER_DEVICE", value)
        assert (Settings.from_environment().max_open_alerts_per_device == max_open_alerts_from_environment()
                == int(value))
