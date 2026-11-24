"""Explicit fail-closed configuration; no authentication-free development mode."""
from dataclasses import dataclass, field
import os
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Settings:
    database_url: str = field(repr=False)
    operator_issuer: str
    operator_audience: str
    jwks_file: Path
    allowed_hosts: tuple[str, ...] = ("localhost", "127.0.0.1", "[::1]")
    allow_loopback_http: bool = False
    stale_after_seconds: int = 90
    enrollment_ttl_seconds: int = 600
    max_enrollment_ttl_seconds: int = 3600
    credential_ttl_seconds: int = 86400
    max_devices_per_tenant: int = 1000
    max_active_grants_per_tenant: int = 1000
    max_audit_events_per_tenant: int = 10000
    max_events_per_device: int = 250000
    max_open_alerts_per_device: int = 500
    requests_per_minute: int = 120
    body_timeout_seconds: int = 5

    def __post_init__(self):
        if not isinstance(self.database_url, str) or not self.database_url.startswith("postgresql+psycopg://"):
            raise ValueError("A PostgreSQL psycopg database URL is required")
        issuer = urlsplit(self.operator_issuer)
        if (issuer.scheme != "https" or not issuer.hostname or issuer.query or issuer.fragment
                or issuer.username or issuer.password or len(self.operator_issuer) > 512):
            raise ValueError("A fixed HTTPS operator issuer is required")
        if not isinstance(self.operator_audience, str) or not 1 <= len(self.operator_audience) <= 256:
            raise ValueError("A fixed API audience is required")
        if not self.allowed_hosts or any(not host or host == "*" or "*" in host or "/" in host for host in self.allowed_hosts):
            raise ValueError("Explicit allowed hosts are required")
        for value, minimum, maximum in (
            (self.stale_after_seconds, 1, 86400), (self.enrollment_ttl_seconds, 1, 3600),
            (self.max_enrollment_ttl_seconds, 1, 3600), (self.credential_ttl_seconds, 60, 2592000),
            (self.max_devices_per_tenant, 1, 100000), (self.max_active_grants_per_tenant, 1, 100000),
            (self.max_audit_events_per_tenant, 10, 1000000), (self.max_events_per_device, 1000, 10000000),
            (self.max_open_alerts_per_device, 10, 100000),
            (self.requests_per_minute, 1, 10000), (self.body_timeout_seconds, 1, 30),
        ):
            if type(value) is not int or not minimum <= value <= maximum:
                raise ValueError("Invalid bounded platform setting")
        if self.enrollment_ttl_seconds > self.max_enrollment_ttl_seconds or type(self.allow_loopback_http) is not bool:
            raise ValueError("Invalid platform setting")
        object.__setattr__(self, "jwks_file", Path(self.jwks_file))

    @classmethod
    def from_environment(cls):
        required = {"database_url": "SP_DATABASE_URL", "operator_issuer": "SP_OPERATOR_ISSUER",
                    "operator_audience": "SP_OPERATOR_AUDIENCE", "jwks_file": "SP_JWKS_FILE"}
        values = {}
        for field, name in required.items():
            if not os.environ.get(name):
                raise ValueError(f"Missing required setting: {name}")
            values[field] = os.environ[name]
        values["allowed_hosts"] = tuple(host.strip() for host in os.environ.get("SP_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]").split(","))
        flag = os.environ.get("SP_ALLOW_LOOPBACK_HTTP", "false")
        if flag not in {"true", "false"}:
            raise ValueError("SP_ALLOW_LOOPBACK_HTTP must be true or false")
        values["allow_loopback_http"] = flag == "true"
        for field in ("stale_after_seconds", "enrollment_ttl_seconds", "max_enrollment_ttl_seconds",
                      "credential_ttl_seconds", "max_devices_per_tenant", "max_active_grants_per_tenant",
                      "max_audit_events_per_tenant", "max_events_per_device", "max_open_alerts_per_device",
                      "requests_per_minute", "body_timeout_seconds"):
            key = "SP_" + field.upper()
            if key in os.environ:
                try:
                    values[field] = int(os.environ[key])
                except ValueError:
                    raise ValueError(f"Invalid integer setting: {key}") from None
        return cls(**values)
