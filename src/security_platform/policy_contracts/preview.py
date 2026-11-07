"""Pure preview orchestration; every environmental input is supplied explicitly."""
from .errors import PolicyContractError
from .fingerprints import adapter_fingerprint, bundle_fingerprint, preview_fingerprint
from .models import (AdapterIdentity, MAX_SCENARIOS, MAX_TRACE_ENTRIES, PolicyBundle, PolicyDecision,
    PreviewOutcome, PreviewScenario, ScenarioComparison, ScenarioEvaluation, TraceEntry)
from .zone_safety import ensure_unambiguous_zones


def _needs_country(bundle):
    for policy in bundle.policies["policies"]:
        if policy["enabled"]:
            country = policy["if"].get("geo", policy.get("geo"))
            if country and country != "ANY":
                return True
    return False


def _evaluate(adapter, bundle, scenario):
    raw_decision, trace = adapter.evaluate(bundle, scenario)
    if not isinstance(trace, (list, tuple)) or len(trace) > 500:
        raise PolicyContractError("invalid_evaluator_result")
    decision = PolicyDecision.model_validate(raw_decision)
    # Validate every entry, even those excluded from the bounded public trace.
    validated = tuple(TraceEntry.model_validate(entry) for entry in trace)
    return ScenarioEvaluation(decision=decision, trace=validated[:MAX_TRACE_ENTRIES],
                              trace_total=len(validated), trace_complete=len(validated) <= MAX_TRACE_ENTRIES)


def preview_policy(base, candidate, scenarios, adapter=None):
    """Never authorize or execute a policy. Invalid work returns no partial result.

    Bundles and scenarios are immutable DTOs. Adapter selection/manifest reads
    happen outside this function; no module, path or command comes from a DTO.
    """
    if not isinstance(base, PolicyBundle) or not isinstance(candidate, PolicyBundle):
        return PreviewOutcome(status="blocked", blocker_codes=("invalid_policy_bundle",))
    try:
        # Pydantic model_copy/model_construct intentionally bypass validation.
        # Recheck actual instance values before normalization can erase an
        # invalid contract version or scalar type. Never serialize them first.
        base, candidate = PolicyBundle.model_validate(base), PolicyBundle.model_validate(candidate)
    except (ValueError, TypeError, AttributeError):
        return PreviewOutcome(status="blocked", blocker_codes=("invalid_policy_bundle",))
    binding = {"base_fingerprint": bundle_fingerprint(base), "candidate_fingerprint": bundle_fingerprint(candidate)}
    if adapter is None or not isinstance(getattr(adapter, "identity", None), AdapterIdentity):
        return PreviewOutcome(status="blocked", blocker_codes=("evaluator_unavailable",), **binding)
    try:
        identity = AdapterIdentity.model_validate(adapter.identity)
    except (ValueError, TypeError, AttributeError):
        return PreviewOutcome(status="blocked", blocker_codes=("evaluator_unavailable",), **binding)
    binding.update(adapter_fingerprint=adapter_fingerprint(identity), adapter_identity=identity)
    try:
        if not isinstance(scenarios, (list, tuple)) or not 1 <= len(scenarios) <= MAX_SCENARIOS:
            raise PolicyContractError("input_limit_exceeded")
        if (any(not isinstance(scenario, PreviewScenario) for scenario in scenarios)
                or len({scenario.scenario_id for scenario in scenarios}) != len(scenarios)):
            raise PolicyContractError("invalid_scenario")
        try:
            scenarios = tuple(PreviewScenario.model_validate(scenario) for scenario in scenarios)
        except (ValueError, TypeError, AttributeError) as exc:
            raise PolicyContractError("invalid_scenario") from exc
        ensure_unambiguous_zones(base)
        ensure_unambiguous_zones(candidate)
        base, candidate = adapter.normalize(base), adapter.normalize(candidate)
        if not isinstance(base, PolicyBundle) or not isinstance(candidate, PolicyBundle):
            raise PolicyContractError("invalid_evaluator_result")
        ensure_unambiguous_zones(base)
        ensure_unambiguous_zones(candidate)
        binding.update(base_fingerprint=bundle_fingerprint(base), candidate_fingerprint=bundle_fingerprint(candidate),
                       legacy_base_version=adapter.legacy_version(base))
        needs_country = _needs_country(base) or _needs_country(candidate)
        if any(scenario.network_profile is None or scenario.evaluation_local_time is None
                or needs_country and scenario.src_geo is None for scenario in scenarios):
            raise PolicyContractError("insufficient_context")
        results = []
        for scenario in scenarios:
            old, new = _evaluate(adapter, base, scenario), _evaluate(adapter, candidate, scenario)
            fields = ("action", "temp_block_sec", "nat", "log")
            results.append(ScenarioComparison(scenario=scenario, base=old, candidate=new,
                decision_changed=any(getattr(old.decision, key) != getattr(new.decision, key) for key in fields),
                matched_policy_changed=(old.decision.policy_id, old.decision.policy_name)
                                       != (new.decision.policy_id, new.decision.policy_name)))
        identity = preview_fingerprint({"contract_version": "sp-hbf-preview/v1",
            "base_fingerprint": binding["base_fingerprint"], "candidate_fingerprint": binding["candidate_fingerprint"],
            "adapter_fingerprint": binding["adapter_fingerprint"],
            "results": [result.model_dump(mode="json") for result in results],
            "authorization": "not_evaluated", "execution_authorized": False, "verification": "not_performed",
            "scope": "packet_policy_preview_only"})
        return PreviewOutcome(status="ok", preview_fingerprint=identity, results=tuple(results), **binding)
    except PolicyContractError as exc:
        return PreviewOutcome(status="blocked", blocker_codes=(exc.code,), **binding)
    except Exception:
        return PreviewOutcome(status="blocked", blocker_codes=("evaluator_failed",), **binding)
