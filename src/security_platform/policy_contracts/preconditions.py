"""Pure fixture CAS and reported-receipt consistency, never authorization.

No revision is derived from an inventory sequence, timestamp or content hash.
The caller must supply distinct controller and endpoint policy evidence.
"""
from datetime import datetime
import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from .errors import PolicyContractError

BundleFingerprint = Annotated[str, Field(strict=True, pattern=r"^sp-hbf-bundle-v1:sha256:[a-f0-9]{64}$")]
AdapterFingerprint = Annotated[str, Field(strict=True, pattern=r"^sp-hbf-adapter-v1:sha256:[a-f0-9]{64}$")]
PreviewFingerprint = Annotated[str, Field(strict=True, pattern=r"^sp-hbf-preview-v1:sha256:[a-f0-9]{64}$")]
Identity = Annotated[str, Field(strict=True, pattern=r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$")]
RevisionText = Annotated[str, Field(strict=True, min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:\-]*$")]
ScopeText = Annotated[str, Field(strict=True, min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_\-]*$")]
UTCText = Annotated[str, Field(strict=True, min_length=20, max_length=32)]
PreconditionBlocker = Literal["precondition_evidence_missing", "tenant_mismatch", "device_mismatch",
    "product_mismatch", "enforcement_scope_mismatch", "unsupported_product", "unsupported_enforcement_scope",
    "controller_revision_conflict", "controller_lineage_conflict", "endpoint_revision_conflict",
    "endpoint_lineage_conflict", "base_fingerprint_conflict", "candidate_fingerprint_conflict",
    "adapter_fingerprint_conflict", "preview_fingerprint_conflict"]
ReceiptBlocker = Literal[PreconditionBlocker, "receipt_plan_conflict", "receipt_plan_revision_conflict",
    "receipt_evidence_missing", "receipt_time_invalid", "receipt_outside_plan_window", "receipt_from_future",
    "receipt_stale", "receipt_reported_failure", "receipt_claim_inconsistent"]


class FrozenContract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True,
                              revalidate_instances="always", validate_default=True)


class GuardedContract(FrozenContract):
    schema_version: Literal[1] = 1
    authorization: Literal["not_evaluated"] = "not_evaluated"
    execution_authorized: Literal[False] = False
    verification: Literal["not_performed"] = "not_performed"
    scope: Literal["packet_policy_preview_only"] = "packet_policy_preview_only"

    @field_validator("schema_version", mode="before")
    @classmethod
    def strict_version(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError("invalid_contract_version")
        return value

    @field_validator("execution_authorized", mode="before")
    @classmethod
    def never_execute(cls, value):
        if type(value) is not bool or value is not False:
            raise ValueError("execution_not_authorized")
        return value


class RevisionEvidence(FrozenContract):
    revision: RevisionText
    lineage: RevisionText


class PolicyBinding(FrozenContract):
    tenant_id: Identity
    device_id: Identity
    product_id: ScopeText
    enforcement_scope: ScopeText


class PreconditionExpectation(GuardedContract):
    binding: PolicyBinding
    controller_revision: RevisionEvidence | None = None
    endpoint_revision: RevisionEvidence | None = None
    base_fingerprint: BundleFingerprint
    candidate_fingerprint: BundleFingerprint
    adapter_fingerprint: AdapterFingerprint
    preview_fingerprint: PreviewFingerprint


class PreconditionObservation(GuardedContract):
    binding: PolicyBinding
    controller_revision: RevisionEvidence | None = None
    endpoint_revision: RevisionEvidence | None = None
    base_fingerprint: BundleFingerprint | None = None
    candidate_fingerprint: BundleFingerprint | None = None
    adapter_fingerprint: AdapterFingerprint | None = None
    preview_fingerprint: PreviewFingerprint | None = None


class PreconditionCheck(GuardedContract):
    expected: PreconditionExpectation
    observed: PreconditionObservation


class PreconditionResult(GuardedContract):
    status: Literal["consistent_fixture_only", "precondition_evidence_missing", "precondition_conflict"]
    format_consistent: bool
    blocker_codes: tuple[PreconditionBlocker, ...]
    missing_evidence: tuple[Literal["controller_revision", "endpoint_revision", "base_fingerprint",
        "candidate_fingerprint", "adapter_fingerprint", "preview_fingerprint"], ...] = ()
    evidence_basis: Literal["explicit_inputs_only"] = "explicit_inputs_only"


def coerce(model, value, code):
    try:
        if isinstance(value, BaseModel):
            value = value.model_dump(mode="python")
        return model.model_validate(value)
    except (ValidationError, TypeError, ValueError):
        raise PolicyContractError(code) from None


def utc_value(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z", value):
        raise PolicyContractError("evaluation_time_invalid")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise PolicyContractError("evaluation_time_invalid") from None


def unique_codes(values):
    return tuple(dict.fromkeys(values))


def binding_conflicts(expected, observed):
    codes = []
    for field, code in (("tenant_id", "tenant_mismatch"), ("device_id", "device_mismatch"),
                        ("product_id", "product_mismatch"), ("enforcement_scope", "enforcement_scope_mismatch")):
        if getattr(expected, field) != getattr(observed, field):
            codes.append(code)
    if expected.product_id != "hostbasedfirewall" or observed.product_id != "hostbasedfirewall":
        codes.append("unsupported_product")
    if expected.enforcement_scope != "packet_policy" or observed.enforcement_scope != "packet_policy":
        codes.append("unsupported_enforcement_scope")
    return codes


def check_preconditions(value: PreconditionCheck | dict) -> PreconditionResult:
    check = coerce(PreconditionCheck, value, "precondition_input_invalid")
    expected, observed = check.expected, check.observed
    conflicts = binding_conflicts(expected.binding, observed.binding)
    missing = []
    for field, prefix in (("controller_revision", "controller"), ("endpoint_revision", "endpoint")):
        wanted, actual = getattr(expected, field), getattr(observed, field)
        if wanted is None or actual is None:
            missing.append(field)
        else:
            if wanted.revision != actual.revision:
                conflicts.append(prefix + "_revision_conflict")
            if wanted.lineage != actual.lineage:
                conflicts.append(prefix + "_lineage_conflict")
    for field in ("base_fingerprint", "candidate_fingerprint", "adapter_fingerprint", "preview_fingerprint"):
        actual = getattr(observed, field)
        if actual is None:
            missing.append(field)
        elif actual != getattr(expected, field):
            conflicts.append(field + "_conflict")
    blockers = (["precondition_evidence_missing"] if missing else []) + conflicts
    status = ("precondition_conflict" if conflicts else "precondition_evidence_missing" if missing
              else "consistent_fixture_only")
    return PreconditionResult(status=status, format_consistent=not blockers,
                              blocker_codes=unique_codes(blockers), missing_evidence=tuple(missing))


class PolicyReceipt(GuardedContract):
    binding: PolicyBinding
    plan_id: Identity
    plan_revision: RevisionText
    base_fingerprint: BundleFingerprint
    candidate_fingerprint: BundleFingerprint
    adapter_fingerprint: AdapterFingerprint
    preview_fingerprint: PreviewFingerprint
    controller_revision: RevisionEvidence | None = None
    source_revision: RevisionEvidence | None = None
    resulting_revision: RevisionEvidence | None = None
    claim_type: Literal["received_reported", "applied_reported"]
    report_status: Literal["reported_success", "reported_failure"]
    reported_at: UTCText
    expires_at: UTCText


class ReceiptExpectation(GuardedContract):
    plan_id: Identity
    plan_revision: RevisionText
    preconditions: PreconditionExpectation
    valid_from: UTCText
    expires_at: UTCText


class ReceiptValidation(GuardedContract):
    status: Literal["receipt_consistent_fixture_only", "receipt_evidence_missing", "receipt_conflict"]
    format_consistent: bool
    blocker_codes: tuple[ReceiptBlocker, ...]
    claim_type: Literal["received_reported", "applied_reported"]
    reported_status: Literal["reported_success", "reported_failure"]
    evidence_basis: Literal["reported_claim_only"] = "reported_claim_only"


def validate_receipt(receipt: PolicyReceipt | dict, expectation: ReceiptExpectation | dict, *, now: str) -> ReceiptValidation:
    receipt = coerce(PolicyReceipt, receipt, "receipt_input_invalid")
    wanted = coerce(ReceiptExpectation, expectation, "receipt_expectation_invalid")
    instant = utc_value(now)
    start, end = utc_value(wanted.valid_from), utc_value(wanted.expires_at)
    reported, expires = utc_value(receipt.reported_at), utc_value(receipt.expires_at)
    codes = binding_conflicts(wanted.preconditions.binding, receipt.binding)
    if receipt.plan_id != wanted.plan_id:
        codes.append("receipt_plan_conflict")
    if receipt.plan_revision != wanted.plan_revision:
        codes.append("receipt_plan_revision_conflict")
    for field in ("base_fingerprint", "candidate_fingerprint", "adapter_fingerprint", "preview_fingerprint"):
        if getattr(receipt, field) != getattr(wanted.preconditions, field):
            codes.append(field + "_conflict")
    evidence = PreconditionObservation(binding=receipt.binding, controller_revision=receipt.controller_revision,
        endpoint_revision=receipt.source_revision, base_fingerprint=receipt.base_fingerprint,
        candidate_fingerprint=receipt.candidate_fingerprint, adapter_fingerprint=receipt.adapter_fingerprint,
        preview_fingerprint=receipt.preview_fingerprint)
    cas = check_preconditions(PreconditionCheck(expected=wanted.preconditions, observed=evidence))
    codes.extend(cas.blocker_codes)
    if receipt.claim_type == "applied_reported" and receipt.resulting_revision is None:
        codes.append("receipt_evidence_missing")
    if receipt.claim_type == "received_reported" and receipt.resulting_revision is not None:
        codes.append("receipt_claim_inconsistent")
    if end <= start or expires <= reported:
        codes.append("receipt_time_invalid")
    if reported < start or reported >= end or expires > end:
        codes.append("receipt_outside_plan_window")
    if reported > instant:
        codes.append("receipt_from_future")
    if instant >= expires or instant >= end:
        codes.append("receipt_stale")
    if receipt.report_status == "reported_failure":
        codes.append("receipt_reported_failure")
    codes = unique_codes(codes)
    only_missing = bool(codes) and all(code in {"precondition_evidence_missing", "receipt_evidence_missing"} for code in codes)
    return ReceiptValidation(status="receipt_evidence_missing" if only_missing else "receipt_conflict" if codes
        else "receipt_consistent_fixture_only", format_consistent=not codes, blocker_codes=codes,
        claim_type=receipt.claim_type, reported_status=receipt.report_status)
