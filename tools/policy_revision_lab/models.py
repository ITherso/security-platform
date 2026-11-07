"""Shared immutable lab protocol. No persistence, clock, network or authority."""
from datetime import datetime, timezone
import hashlib
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BeforeValidator, Field, field_validator, model_validator

from security_platform.policy_contracts.fingerprints import adapter_fingerprint, bundle_fingerprint, canonical_bytes
from security_platform.policy_contracts.models import AdapterFingerprint, AdapterIdentity, BundleFingerprint, FrozenDTO, PolicyBundle
from security_platform.policy_contracts.zone_safety import ensure_unambiguous_zones

MAX_REVISION = 9223372036854775807
MAX_ENTRIES = 128
MAX_STORE_BYTES = 16 * 1024 * 1024
MAX_JSON_BYTES = 3 * 1024 * 1024
SCHEMA_VERSION = 1


class LabError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _uuid(value):
    if type(value) is not str:
        raise ValueError("invalid_lab_uuid")
    try:
        if str(UUID(value)) != value:
            raise ValueError("invalid_lab_uuid")
    except (ValueError, AttributeError) as exc:
        raise ValueError("invalid_lab_uuid") from exc
    return value


UUIDText = Annotated[str, BeforeValidator(_uuid)]
Revision = Annotated[int, Field(strict=True, ge=0, le=MAX_REVISION)]
RequestDigest = Annotated[str, Field(pattern=r"^sp-hbf-lab-request-v1:sha256:[a-f0-9]{64}$")]


class LabBinding(FrozenDTO):
    kind: Literal["controller_draft", "endpoint_staged"]
    tenant_id: UUIDText
    subject_id: UUIDText
    product_id: Literal["hostbasedfirewall"] = "hostbasedfirewall"
    enforcement_scope: Literal["packet_policy"] = "packet_policy"


class LabGuards(FrozenDTO):
    schema_version: Literal[1] = 1
    authority: Literal["unbound"] = "unbound"
    operational_binding: Literal["absent"] = "absent"
    identity_source: Literal["fixture"] = "fixture"
    rollback_protection: Literal["not_established"] = "not_established"
    controller_desired_revision: None = None
    device_policy_revision: None = None
    authorization: Literal["not_evaluated"] = "not_evaluated"
    execution_authorized: Literal[False] = False
    verification: Literal["not_performed"] = "not_performed"
    scope: Literal["packet_policy_preview_only"] = "packet_policy_preview_only"

    @field_validator("schema_version", mode="before")
    @classmethod
    def strict_schema(cls, value):
        if type(value) is not int:
            raise ValueError("invalid_lab_version")
        return value

    @field_validator("execution_authorized", mode="before")
    @classmethod
    def never_authorized(cls, value):
        if value is not False:
            raise ValueError("invalid_lab_guard")
        return value


class AppendRequest(FrozenDTO):
    binding: LabBinding
    operation_id: UUIDText
    expected_lineage: UUIDText
    expected_revision: Revision
    base_fingerprint: BundleFingerprint | None
    bundle: PolicyBundle

    @model_validator(mode="after")
    def base_matches_empty_head(self):
        if (self.expected_revision == 0) != (self.base_fingerprint is None):
            raise ValueError("invalid_lab_precondition")
        return self


class LabCommit(LabGuards):
    record_kind: Literal["controller_draft", "endpoint_staged"]
    binding: LabBinding
    lineage: UUIDText
    operation_id: UUIDText
    draft_revision: Revision | None
    staged_revision: Revision | None
    bundle_fingerprint: BundleFingerprint
    request_digest: RequestDigest
    committed_at: str = Field(max_length=27)

    @field_validator("committed_at")
    @classmethod
    def utc_metadata(cls, value):
        try:
            parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
        except ValueError as exc:
            raise ValueError("invalid_lab_timestamp") from exc
        if parsed.isoformat(timespec="microseconds").replace("+00:00", "Z") != value:
            raise ValueError("invalid_lab_timestamp")
        return value

    @model_validator(mode="after")
    def kind_revision(self):
        active = self.draft_revision if self.record_kind == "controller_draft" else self.staged_revision
        other = self.staged_revision if self.record_kind == "controller_draft" else self.draft_revision
        if self.binding.kind != self.record_kind or active is None or active < 1 or other is not None:
            raise ValueError("invalid_lab_result")
        return self


class LabHead(LabGuards):
    record_kind: Literal["controller_draft", "endpoint_staged"]
    binding: LabBinding
    lineage: UUIDText
    revision: Revision
    draft_revision: Revision | None
    staged_revision: Revision | None
    adapter_fingerprint: AdapterFingerprint
    bundle_fingerprint: BundleFingerprint | None
    bundle: PolicyBundle | None
    last_commit: LabCommit | None

    @model_validator(mode="after")
    def consistent_head(self):
        active = self.draft_revision if self.record_kind == "controller_draft" else self.staged_revision
        other = self.staged_revision if self.record_kind == "controller_draft" else self.draft_revision
        if self.record_kind != self.binding.kind or active != self.revision or other is not None:
            raise ValueError("invalid_lab_head")
        if self.revision == 0:
            if self.bundle is not None or self.bundle_fingerprint is not None or self.last_commit is not None:
                raise ValueError("invalid_lab_head")
        else:
            if self.bundle is None or self.last_commit is None or self.bundle_fingerprint != bundle_fingerprint(self.bundle):
                raise ValueError("invalid_lab_head")
            commit = self.last_commit
            if (commit.binding != self.binding or commit.lineage != self.lineage
                    or commit.bundle_fingerprint != self.bundle_fingerprint or commit_revision(commit) != self.revision):
                raise ValueError("invalid_lab_head")
        return self


class LabCheck(LabGuards):
    status: Literal["consistent"] = "consistent"
    checked_entries: int = Field(strict=True, ge=0, le=MAX_ENTRIES)
    head: LabHead

    @model_validator(mode="after")
    def matches_full_history(self):
        if self.checked_entries != self.head.revision:
            raise ValueError("invalid_lab_check")
        return self


def normalize_bundle(value, adapter):
    """Revalidate typed copies before actual fixed source normalization."""
    try:
        if adapter is None:
            raise ValueError("adapter unavailable")
        AdapterIdentity.model_validate(adapter.identity)
        bundle = PolicyBundle.model_validate(value)
        ensure_unambiguous_zones(bundle)
        bundle = PolicyBundle.model_validate(adapter.normalize(bundle))
        ensure_unambiguous_zones(bundle)
        return bundle
    except (ValueError, TypeError, AttributeError, KeyError, OverflowError, RecursionError) as exc:
        raise LabError("invalid_lab_bundle") from exc


def normalize_request(value, adapter):
    try:
        request = AppendRequest.model_validate(value)
        bundle = normalize_bundle(request.bundle, adapter)
        return AppendRequest.model_validate({**request.model_dump(mode="python"), "bundle": bundle})
    except LabError:
        raise
    except (ValueError, TypeError, AttributeError) as exc:
        raise LabError("invalid_lab_request") from exc


def request_digest(request):
    try:
        request = AppendRequest.model_validate(request)
        return "sp-hbf-lab-request-v1:sha256:" + hashlib.sha256(canonical_bytes(request.model_dump(mode="json"))).hexdigest()
    except (ValueError, TypeError) as exc:
        raise LabError("invalid_lab_request") from exc


def commit_revision(commit):
    return commit.draft_revision if commit.record_kind == "controller_draft" else commit.staged_revision


def make_commit(request, lineage, revision, committed_at):
    try:
        request = AppendRequest.model_validate(request)
        if type(revision) is not int or not 1 <= revision <= MAX_REVISION or revision != request.expected_revision + 1:
            raise ValueError("invalid revision")
        if lineage != request.expected_lineage:
            raise ValueError("invalid lineage")
        return LabCommit(record_kind=request.binding.kind, binding=request.binding, lineage=lineage,
            operation_id=request.operation_id,
            draft_revision=revision if request.binding.kind == "controller_draft" else None,
            staged_revision=revision if request.binding.kind == "endpoint_staged" else None,
            bundle_fingerprint=bundle_fingerprint(request.bundle), request_digest=request_digest(request), committed_at=committed_at)
    except (ValueError, TypeError) as exc:
        raise LabError("invalid_lab_result") from exc


def validate_committed(request, result, adapter):
    try:
        normalized = normalize_request(request, adapter)
        result = LabCommit.model_validate(result)
        expected = make_commit(normalized, result.lineage, commit_revision(result), result.committed_at)
        if result != expected:
            raise ValueError("result mismatch")
        return result
    except (ValueError, TypeError) as exc:
        raise LabError("lab_store_corrupt") from exc


def make_head(binding, lineage, revision, adapter, bundle=None, last_commit=None):
    try:
        binding = LabBinding.model_validate(binding)
        if bundle is not None:
            bundle = normalize_bundle(bundle, adapter)
        return LabHead(record_kind=binding.kind, binding=binding, lineage=lineage, revision=revision,
            draft_revision=revision if binding.kind == "controller_draft" else None,
            staged_revision=revision if binding.kind == "endpoint_staged" else None,
            adapter_fingerprint=adapter_fingerprint(AdapterIdentity.model_validate(adapter.identity)),
            bundle_fingerprint=bundle_fingerprint(bundle) if bundle is not None else None,
            bundle=bundle, last_commit=last_commit)
    except (ValueError, TypeError) as exc:
        raise LabError("lab_store_corrupt") from exc
