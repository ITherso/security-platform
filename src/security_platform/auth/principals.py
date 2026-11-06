from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class OperatorPrincipal:
    issuer: str
    subject: str


@dataclass(frozen=True)
class EnrollmentPrincipal:
    tenant_id: UUID
    grant_id: UUID


@dataclass(frozen=True)
class DevicePrincipal:
    tenant_id: UUID
    device_id: UUID
    credential_id: UUID
