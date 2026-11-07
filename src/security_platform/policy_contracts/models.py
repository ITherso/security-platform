"""Strict, deeply immutable offline packet-policy contracts."""
from datetime import time as LocalTime
import ipaddress
import re
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, PlainSerializer, field_validator, model_validator

from .errors import PolicyContractError
from .immutable import FrozenObject, freeze_object, immutable_tuple, thaw

BUNDLE_CONTRACT_VERSION = "sp-hbf-bundle/v1"
CANONICALIZATION_VERSION = "sp-json-canonical/v1"
NORMALIZATION_VERSION = "hbf-source-normalization/v1"
PREVIEW_CONTRACT_VERSION = "sp-hbf-preview/v1"
ADAPTER_CONTRACT_VERSION = "sp-hbf-adapter/v1"
MAX_SCENARIOS, MAX_TRACE_ENTRIES = 32, 64
JsonObject = Annotated[FrozenObject, BeforeValidator(freeze_object), PlainSerializer(thaw, return_type=dict)]
HexDigest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
BundleFingerprint = Annotated[str, Field(pattern=r"^sp-hbf-bundle-v1:sha256:[a-f0-9]{64}$")]
AdapterFingerprint = Annotated[str, Field(pattern=r"^sp-hbf-adapter-v1:sha256:[a-f0-9]{64}$")]
PreviewFingerprint = Annotated[str, Field(pattern=r"^sp-hbf-preview-v1:sha256:[a-f0-9]{64}$")]


class FrozenDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, arbitrary_types_allowed=True,
                              revalidate_instances="always")


class OrderedZone(FrozenDTO):
    name: str = Field(min_length=1, max_length=256)
    cidrs: Annotated[tuple[Annotated[str, Field(min_length=1, max_length=80)], ...],
                     BeforeValidator(immutable_tuple), Field(min_length=1, max_length=10000)]

    @field_validator("name")
    @classmethod
    def meaningful_name(cls, value):
        if not value.strip() or value == "ANY":
            raise PolicyContractError("invalid_policy_bundle")
        return value


class PolicyBundle(FrozenDTO):
    schema_version: Literal[1]
    contract_version: Literal["sp-hbf-bundle/v1"] = BUNDLE_CONTRACT_VERSION
    canonicalization_version: Literal["sp-json-canonical/v1"] = CANONICALIZATION_VERSION
    normalization_version: Literal["hbf-source-normalization/v1"] = NORMALIZATION_VERSION
    ordered_zones: Annotated[tuple[OrderedZone, ...], BeforeValidator(immutable_tuple), Field(max_length=10000)]
    objects: JsonObject
    policies: JsonObject

    @field_validator("schema_version", mode="before")
    @classmethod
    def strict_version(cls, value):
        if type(value) is not int:
            raise PolicyContractError("invalid_policy_bundle")
        return value

    @model_validator(mode="after")
    def source_shape(self):
        if len({zone.name for zone in self.ordered_zones}) != len(self.ordered_zones):
            raise PolicyContractError("invalid_policy_bundle")
        if set(self.objects) - {"address_objects", "user_objects", "services", "schedules",
                                "security_profiles", "nat_rules", "description"}:
            raise PolicyContractError("invalid_policy_bundle")
        if set(self.policies) - {"default_action", "policies", "description"}:
            raise PolicyContractError("invalid_policy_bundle")
        rules = self.policies.get("policies")
        if not isinstance(rules, tuple) or len(rules) > 500:
            raise PolicyContractError("input_limit_exceeded")
        # Enforce one aggregate budget, including ordered zone names and CIDRs.
        freeze_object({"objects": thaw(self.objects), "policies": thaw(self.policies),
                       "ordered_zones": [zone.model_dump(mode="json") for zone in self.ordered_zones]})
        return self


class PreviewScenario(FrozenDTO):
    scenario_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    src_ip: str = Field(max_length=45)
    dst_ip: str = Field(max_length=45)
    protocol: Literal["TCP", "UDP"]
    dst_port: int = Field(strict=True, ge=1, le=65535)
    network_profile: Literal["HOME", "WORK", "PUBLIC"] | None = None
    evaluation_local_time: str | None = Field(default=None, max_length=15)
    src_geo: str | None = Field(default=None, max_length=2)

    @field_validator("src_ip", "dst_ip")
    @classmethod
    def canonical_address(cls, value):
        if "%" in value:
            raise PolicyContractError("invalid_scenario")
        try:
            return str(ipaddress.ip_address(value))
        except ValueError as exc:
            raise PolicyContractError("invalid_scenario") from exc

    @field_validator("evaluation_local_time")
    @classmethod
    def explicit_local_time(cls, value):
        if value is None:
            return None
        if not re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](?:\.[0-9]{1,6})?", value):
            raise PolicyContractError("invalid_scenario")
        return LocalTime.fromisoformat(value).isoformat(timespec="microseconds")

    @field_validator("src_geo")
    @classmethod
    def explicit_country(cls, value):
        if value is not None and not re.fullmatch(r"[A-Za-z]{2}", value):
            raise PolicyContractError("invalid_scenario")
        return value.upper() if value is not None else None

    @model_validator(mode="after")
    def same_ip_family(self):
        if ipaddress.ip_address(self.src_ip).version != ipaddress.ip_address(self.dst_ip).version:
            raise PolicyContractError("invalid_scenario")
        return self


class SourceManifestEntry(FrozenDTO):
    component: Literal["hbf", "platform"]
    name: str = Field(min_length=1, max_length=64, pattern=r"^[a-z_]+\.py$")
    sha256: HexDigest


class AdapterIdentity(FrozenDTO):
    contract_version: Literal["sp-hbf-adapter/v1"] = ADAPTER_CONTRACT_VERSION
    evaluator_contract: Literal["hbf-explicit-time-profile/v1"] = "hbf-explicit-time-profile/v1"
    normalization_version: Literal["hbf-source-normalization/v1"] = NORMALIZATION_VERSION
    python_implementation: str = Field(min_length=1, max_length=32)
    python_version: str = Field(min_length=1, max_length=32)
    pydantic_version: str = Field(min_length=1, max_length=32)
    source_manifest: Annotated[tuple[SourceManifestEntry, ...], BeforeValidator(immutable_tuple), Field(min_length=1, max_length=16)]

    @model_validator(mode="after")
    def unique_manifest(self):
        if len({(row.component, row.name) for row in self.source_manifest}) != len(self.source_manifest):
            raise PolicyContractError("invalid_adapter_identity")
        return self


class PolicyDecision(FrozenDTO):
    action: Literal["ALLOW", "DENY", "DENY_TEMP"]
    policy_id: int | None = Field(default=None, strict=True, ge=1, le=9007199254740991)
    policy_name: str | None = Field(default=None, max_length=256)
    reason: str = Field(max_length=1024)
    temp_block_sec: int | None = Field(default=None, strict=True, ge=1)
    nat: bool
    log: bool

    @model_validator(mode="after")
    def coherent_decision(self):
        if ((self.action == "DENY_TEMP") != (self.temp_block_sec is not None)
                or self.nat and self.action != "ALLOW"
                or (self.policy_id is None) != (self.policy_name is None)):
            raise PolicyContractError("invalid_evaluator_result")
        return self


class TraceEntry(FrozenDTO):
    policy_id: int = Field(strict=True, ge=1, le=9007199254740991)
    policy_name: str = Field(max_length=256)
    matched: bool
    selected: bool
    reasons: Annotated[tuple[Annotated[str, Field(max_length=1024)], ...], BeforeValidator(immutable_tuple), Field(max_length=4)]


class ScenarioEvaluation(FrozenDTO):
    decision: PolicyDecision
    trace: Annotated[tuple[TraceEntry, ...], BeforeValidator(immutable_tuple), Field(max_length=MAX_TRACE_ENTRIES)]
    trace_total: int = Field(strict=True, ge=0, le=500)
    trace_complete: bool


class ScenarioComparison(FrozenDTO):
    scenario: PreviewScenario
    base: ScenarioEvaluation
    candidate: ScenarioEvaluation
    decision_changed: bool
    matched_policy_changed: bool


class PreviewOutcome(FrozenDTO):
    contract_version: Literal["sp-hbf-preview/v1"] = PREVIEW_CONTRACT_VERSION
    status: Literal["ok", "blocked"]
    blocker_codes: Annotated[tuple[Literal["evaluator_unavailable", "invalid_policy_bundle", "ambiguous_equal_prefix_zones",
        "insufficient_context", "input_limit_exceeded", "invalid_scenario", "invalid_evaluator_result", "evaluator_failed"], ...],
        BeforeValidator(immutable_tuple), Field(max_length=16)] = ()
    legacy_base_version: HexDigest | None = None
    base_fingerprint: BundleFingerprint | None = None
    candidate_fingerprint: BundleFingerprint | None = None
    adapter_fingerprint: AdapterFingerprint | None = None
    preview_fingerprint: PreviewFingerprint | None = None
    adapter_identity: AdapterIdentity | None = None
    results: Annotated[tuple[ScenarioComparison, ...], BeforeValidator(immutable_tuple), Field(max_length=MAX_SCENARIOS)] = ()
    authorization: Literal["not_evaluated"] = "not_evaluated"
    execution_authorized: Literal[False] = False
    verification: Literal["not_performed"] = "not_performed"
    scope: Literal["packet_policy_preview_only"] = "packet_policy_preview_only"

    @field_validator("execution_authorized", mode="before")
    @classmethod
    def no_execution_authority(cls, value):
        if value is not False:
            raise PolicyContractError("execution_not_authorized")
        return value

    @model_validator(mode="after")
    def outcome_consistency(self):
        if self.status == "ok":
            if self.blocker_codes or not self.results or not all((self.base_fingerprint, self.candidate_fingerprint,
                    self.adapter_fingerprint, self.preview_fingerprint, self.adapter_identity, self.legacy_base_version)):
                raise PolicyContractError("invalid_preview_outcome")
        elif self.preview_fingerprint is not None or self.results or not self.blocker_codes:
            raise PolicyContractError("invalid_preview_outcome")
        return self
