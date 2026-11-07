"""Bounded, immutable rollout proposals and pure non-executable simulation."""
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .errors import PolicyContractError
from .preconditions import (AdapterFingerprint, BundleFingerprint, FrozenContract, GuardedContract,
    Identity, PolicyBinding, PolicyReceipt, PreconditionCheck, PreconditionExpectation, PreconditionObservation,
    ReceiptBlocker, ReceiptExpectation, RevisionEvidence, RevisionText, ScopeText, UTCText, check_preconditions,
    coerce, unique_codes, utc_value, validate_receipt)

MAX_TARGETS = 128
MAX_PILOT_TARGETS = 16
MAX_BATCHES = 16
MAX_BATCH_TARGETS = 32
MAX_VALIDITY_SECONDS = 86400
FIXED_BLOCKERS = ("execution_not_implemented", "windows_acceptance_missing",
                  "authorization_not_evaluated", "verification_not_performed")
RolloutBlocker = Literal[ReceiptBlocker, "execution_not_implemented", "windows_acceptance_missing",
    "authorization_not_evaluated", "verification_not_performed", "rollout_observation_binding_conflict",
    "rollout_receipt_binding_conflict", "rollout_expired", "rollout_not_started", "receipt_missing"]


def immutable_array(value):
    if type(value) not in (list, tuple):
        raise ValueError("ordered_array_required")
    return tuple(value)


class StopConditions(FrozenContract):
    on_failure: Literal[True] = True
    on_missing_receipt: Literal[True] = True
    on_stale_receipt: Literal[True] = True
    on_conflict: Literal[True] = True

    @field_validator("on_failure", "on_missing_receipt", "on_stale_receipt", "on_conflict", mode="before")
    @classmethod
    def fixed_stop(cls, value):
        if type(value) is not bool or value is not True:
            raise ValueError("stop_condition_required")
        return value


class PreviousArtifactReference(FrozenContract):
    artifact_fingerprint: BundleFingerprint
    endpoint_revision: RevisionEvidence | None = None
    purpose: Literal["rollback_proposal_only"] = "rollback_proposal_only"


class RolloutTarget(FrozenContract):
    device_id: Identity
    preconditions: PreconditionExpectation
    rollback_reference: PreviousArtifactReference

    @model_validator(mode="after")
    def bound_reference(self):
        if (self.device_id != self.preconditions.binding.device_id
                or self.rollback_reference.artifact_fingerprint != self.preconditions.base_fingerprint
                or self.rollback_reference.endpoint_revision != self.preconditions.endpoint_revision):
            raise ValueError("rollout_rollback_reference_conflict")
        return self


class ProposedRollout(GuardedContract):
    plan_id: Identity
    plan_revision: RevisionText
    tenant_id: Identity
    product_id: ScopeText
    enforcement_scope: ScopeText
    candidate_fingerprint: BundleFingerprint
    adapter_fingerprint: AdapterFingerprint
    targets: tuple[RolloutTarget, ...] = Field(min_length=1, max_length=MAX_TARGETS)
    pilot_devices: tuple[Identity, ...] = Field(min_length=1, max_length=MAX_PILOT_TARGETS)
    batches: tuple[tuple[Identity, ...], ...] = Field(default=(), max_length=MAX_BATCHES)
    valid_from: UTCText
    expires_at: UTCText
    stop_conditions: StopConditions = Field(default_factory=StopConditions)
    unresolved_gates: tuple[str, ...] = FIXED_BLOCKERS

    @field_validator("targets", "pilot_devices", mode="before")
    @classmethod
    def freeze_arrays(cls, value):
        return immutable_array(value)

    @field_validator("batches", mode="before")
    @classmethod
    def freeze_batches(cls, value):
        return tuple(immutable_array(batch) for batch in immutable_array(value))

    @field_validator("unresolved_gates", mode="before")
    @classmethod
    def fixed_gates(cls, value):
        value = immutable_array(value)
        if value != FIXED_BLOCKERS:
            raise ValueError("rollout_acceptance_gates_cannot_be_cleared")
        return value

    @model_validator(mode="after")
    def bind_targets_and_window(self):
        devices = tuple(target.device_id for target in self.targets)
        groups = (self.pilot_devices, *self.batches)
        ordered = tuple(device for batch in groups for device in batch)
        if (len(set(devices)) != len(devices) or len(set(ordered)) != len(ordered)
                or set(ordered) != set(devices) or any(not 1 <= len(batch) <= MAX_BATCH_TARGETS for batch in self.batches)):
            raise ValueError("rollout_target_partition_invalid")
        if self.product_id != "hostbasedfirewall" or self.enforcement_scope != "packet_policy":
            raise ValueError("rollout_scope_unsupported")
        for target in self.targets:
            expected = target.preconditions
            if (expected.binding.tenant_id != self.tenant_id or expected.binding.product_id != self.product_id
                    or expected.binding.enforcement_scope != self.enforcement_scope
                    or expected.candidate_fingerprint != self.candidate_fingerprint
                    or expected.adapter_fingerprint != self.adapter_fingerprint):
                raise ValueError("rollout_target_binding_conflict")
        seconds = (utc_value(self.expires_at) - utc_value(self.valid_from)).total_seconds()
        if not 0 < seconds <= MAX_VALIDITY_SECONDS:
            raise ValueError("rollout_validity_window_invalid")
        return self


class TargetEvaluation(GuardedContract):
    device_id: Identity
    status: Literal["would_wait", "would_pause"]
    blocker_codes: tuple[RolloutBlocker, ...]
    receipt_claims: tuple[Literal["received_reported", "applied_reported"], ...] = ()
    rollback_reference: PreviousArtifactReference


class RolloutEvaluation(GuardedContract):
    plan_id: Identity
    plan_revision: RevisionText
    status: Literal["would_wait", "would_pause"]
    blocker_codes: tuple[RolloutBlocker, ...]
    targets: tuple[TargetEvaluation, ...]
    next_batch: None = None
    execution_plan: Literal["not_created"] = "not_created"
    rollback: Literal["references_only"] = "references_only"


def simulate_rollout(plan: ProposedRollout | dict, observations=(), receipts=(), *, now: str) -> RolloutEvaluation:
    plan = coerce(ProposedRollout, plan, "rollout_input_invalid")
    if type(observations) not in (tuple, list) or len(observations) > MAX_TARGETS:
        raise PolicyContractError("rollout_observations_invalid")
    if type(receipts) not in (tuple, list) or len(receipts) > MAX_TARGETS * 2:
        raise PolicyContractError("rollout_receipts_invalid")
    observations = tuple(coerce(PreconditionObservation, row, "rollout_observations_invalid") for row in observations)
    receipts = tuple(coerce(PolicyReceipt, row, "rollout_receipts_invalid") for row in receipts)
    instant = utc_value(now)
    start, end = utc_value(plan.valid_from), utc_value(plan.expires_at)
    devices = {target.device_id for target in plan.targets}
    seen_observations = set()
    global_faults = []
    for row in observations:
        identity = row.binding.device_id
        if identity not in devices or identity in seen_observations:
            global_faults.append("rollout_observation_binding_conflict")
        seen_observations.add(identity)
    seen_receipts = set()
    for row in receipts:
        identity = (row.binding.device_id, row.claim_type)
        if row.binding.device_id not in devices or identity in seen_receipts:
            global_faults.append("rollout_receipt_binding_conflict")
        seen_receipts.add(identity)
    if instant >= end:
        global_faults.append("rollout_expired")
    elif instant < start:
        global_faults.append("rollout_not_started")
    evaluations = []
    for target in plan.targets:
        faults = list(global_faults)
        matching = tuple(row for row in observations if row.binding.device_id == target.device_id)
        if len(matching) != 1:
            faults.append("precondition_evidence_missing")
        else:
            check = check_preconditions(PreconditionCheck(expected=target.preconditions, observed=matching[0]))
            faults.extend(check.blocker_codes)
        target_receipts = tuple(row for row in receipts if row.binding.device_id == target.device_id)
        claims = []
        for receipt in target_receipts:
            validation = validate_receipt(receipt, ReceiptExpectation(plan_id=plan.plan_id,
                plan_revision=plan.plan_revision, preconditions=target.preconditions,
                valid_from=plan.valid_from, expires_at=plan.expires_at), now=now)
            faults.extend(validation.blocker_codes)
            if validation.format_consistent:
                claims.append(receipt.claim_type)
        if not target_receipts:
            faults.append("receipt_missing")
        # A received/applied report never grants trusted verification or opens
        # the next batch. All targets remain constrained by the fixed gates.
        pause = any(code not in {"receipt_missing", "rollout_not_started"} for code in faults)
        evaluations.append(TargetEvaluation(device_id=target.device_id,
            status="would_pause" if pause else "would_wait", blocker_codes=unique_codes((*FIXED_BLOCKERS, *faults)),
            receipt_claims=tuple(claims), rollback_reference=target.rollback_reference))
    return RolloutEvaluation(plan_id=plan.plan_id, plan_revision=plan.plan_revision,
        status="would_pause" if any(row.status == "would_pause" for row in evaluations) else "would_wait",
        blocker_codes=unique_codes(code for row in evaluations for code in row.blocker_codes), targets=tuple(evaluations))
