"""Pure validation of reported Windows evidence format, never live acceptance.

References and hashes are caller supplied strings. This module never opens them,
queries Windows, checks a signature, authenticates a reviewer, or performs a test.
"""
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field, field_validator, model_validator

from security_platform.policy_contracts.immutable import immutable_tuple
from security_platform.policy_contracts.preconditions import FrozenContract

CaseStatus = Literal["NOT_RUN", "PASS", "FAIL", "SKIP", "BLOCKED"]
Sha256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Commit = Annotated[str, Field(pattern=r"^[a-f0-9]{40}$")]
ShortText = Annotated[str, Field(min_length=1, max_length=256)]
Description = Annotated[str, Field(min_length=1, max_length=2048)]


class EvidenceReference(FrozenContract):
    reference: Annotated[str, Field(min_length=1, max_length=256,
                                    pattern=r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")]
    sha256: Sha256
    kind: Literal["log", "screenshot", "artifact", "signature_report", "operator_note", "self_report"]

    @field_validator("reference")
    @classmethod
    def lexical_relative_reference(cls, value):
        if any(part in ("", ".", "..") for part in value.split("/")):
            raise ValueError("invalid_evidence_reference")
        return value


class WindowsAccountContext(FrozenContract):
    account_name: ShortText
    sid: Annotated[str, Field(max_length=184, pattern=r"^S-1-(?:[0-9]+-){1,15}[0-9]+$")]
    context: Literal["standard_user", "administrator", "SYSTEM"]

    @model_validator(mode="after")
    def sid_context_format(self):
        parts = self.sid.split("-")
        numbers = parts[2:]
        if (len(numbers) > 16 or any(str(int(part)) != part for part in numbers)
                or int(numbers[0]) >= 2 ** 48 or any(int(part) >= 2 ** 32 for part in numbers[1:])):
            raise ValueError("invalid_reported_sid_format")
        if (self.context == "SYSTEM") != (self.sid == "S-1-5-18"):
            raise ValueError("reported_system_sid_context_inconsistent")
        return self


class WindowsCase(FrozenContract):
    case_id: Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")]
    source_commit: Commit | None = None
    artifact_sha256: Sha256 | None = None
    windows_build: ShortText | None = None
    architecture: Literal["x64", "arm64", "x86"] | None = None
    environment: Literal["vm", "physical"] | None = None
    accounts: Annotated[tuple[WindowsAccountContext, ...], BeforeValidator(immutable_tuple),
                        Field(max_length=8)] = ()
    preconditions: Annotated[tuple[Description, ...], BeforeValidator(immutable_tuple),
                             Field(min_length=1, max_length=16)]
    action: Description
    expected: Description
    observed: Description | None = None
    evidence_refs: Annotated[tuple[EvidenceReference, ...], BeforeValidator(immutable_tuple),
                             Field(max_length=32)] = ()
    status: CaseStatus = "NOT_RUN"
    reviewer: ShortText | None = None
    review_status: Literal["not_reviewed", "reported_reviewed"] = "not_reviewed"

    @model_validator(mode="after")
    def reported_consistency(self):
        if self.status == "NOT_RUN":
            if self.observed is not None or self.evidence_refs or self.reviewer is not None or self.review_status != "not_reviewed":
                raise ValueError("not_run_must_not_claim_observation_or_review")
        else:
            if any(value is None for value in (self.source_commit, self.artifact_sha256,
                    self.windows_build, self.architecture, self.environment, self.observed)) or not self.accounts:
                raise ValueError("reported_case_context_missing")
            if not self.evidence_refs:
                raise ValueError("reported_case_evidence_missing")
        if (self.review_status == "reported_reviewed") != (self.reviewer is not None):
            raise ValueError("reported_review_inconsistent")
        if len({account.sid for account in self.accounts}) != len(self.accounts):
            raise ValueError("duplicate_account_sid")
        if any(ref.kind == "artifact" and ref.sha256 != self.artifact_sha256 for ref in self.evidence_refs):
            raise ValueError("reported_artifact_hash_inconsistent")
        return self


class WindowsEvidenceReport(FrozenContract):
    schema_version: Literal[1] = 1
    evidence_origin: Literal["real", "synthetic"]
    cases: Annotated[tuple[WindowsCase, ...], BeforeValidator(immutable_tuple),
                     Field(min_length=1, max_length=64)]

    @field_validator("schema_version", mode="before")
    @classmethod
    def exact_version(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError("windows_evidence_version_invalid")
        return value

    @model_validator(mode="after")
    def unique_consistent_references(self):
        if len({case.case_id for case in self.cases}) != len(self.cases):
            raise ValueError("duplicate_windows_case_id")
        references = {}
        for case in self.cases:
            for ref in case.evidence_refs:
                if ref.reference in references and references[ref.reference] != ref.sha256:
                    raise ValueError("conflicting_reported_evidence_hash")
                references[ref.reference] = ref.sha256
        return self


class ReportedStatusCounts(FrozenContract):
    NOT_RUN: Annotated[int, Field(ge=0, le=64)] = 0
    PASS: Annotated[int, Field(ge=0, le=64)] = 0
    FAIL: Annotated[int, Field(ge=0, le=64)] = 0
    SKIP: Annotated[int, Field(ge=0, le=64)] = 0
    BLOCKED: Annotated[int, Field(ge=0, le=64)] = 0


class WindowsEvidenceValidation(FrozenContract):
    status: Literal["format_consistent"] = "format_consistent"
    validation_scope: Literal["format_consistency_only"] = "format_consistency_only"
    evidence_origin: Literal["real", "synthetic"]
    case_count: Annotated[int, Field(ge=1, le=64)]
    reported_status_counts: ReportedStatusCounts
    windows_acceptance: Literal["not_evaluated"] = "not_evaluated"
    independent_verification: Literal["not_performed"] = "not_performed"
    reviewer_identity: Literal["not_authenticated"] = "not_authenticated"
    authorization: Literal["not_evaluated"] = "not_evaluated"
    execution_authorized: Literal[False] = False
    real_acceptance_established: Literal[False] = False

    @field_validator("execution_authorized", "real_acceptance_established", mode="before")
    @classmethod
    def exact_false(cls, value):
        if type(value) is not bool or value is not False:
            raise ValueError("windows_acceptance_not_established")
        return value


def validate_windows_evidence(value: WindowsEvidenceReport | dict) -> WindowsEvidenceValidation:
    """Validate supplied format without promoting any reported result.

    Revalidate instances too: Pydantic model_copy/model_construct do not validate
    their input. No evidence reference or hash is independently checked here.
    """
    if not isinstance(value, (WindowsEvidenceReport, dict)):
        raise ValueError("windows_evidence_invalid")
    report = WindowsEvidenceReport.model_validate(value)
    counts = {status: 0 for status in ("NOT_RUN", "PASS", "FAIL", "SKIP", "BLOCKED")}
    for case in report.cases:
        counts[case.status] += 1
    return WindowsEvidenceValidation(evidence_origin=report.evidence_origin,
        case_count=len(report.cases), reported_status_counts=ReportedStatusCounts(**counts))
