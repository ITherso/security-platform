"""Explicit offline policy tooling; this module never starts a server or sender."""
import argparse
import json
from pathlib import Path
import sys
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import PolicyBundle, PreviewScenario
from .offline_io import OfflineInputError, read_input, write_output


class OfflineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    schema_version: Literal[1] = 1

    @field_validator("schema_version", mode="before")
    @classmethod
    def version_is_integer(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError("policy_input_invalid")
        return value


class PreviewRequest(OfflineRequest):
    base: PolicyBundle
    candidate: PolicyBundle
    scenarios: tuple[PreviewScenario, ...] = Field(min_length=1, max_length=32)


def _parse(model, value):
    # JSON mode permits JSON arrays for immutable tuples while strict scalar
    # types, unknown-field rejection and each DTO's validators remain enabled.
    return model.model_validate_json(json.dumps(value, allow_nan=False))


# Blockers that only mean the selected input is invalid: exit 1, no output is
# written or replaced. insufficient_context, evaluator results/failures and the
# documented no --hbf-root evaluator_unavailable stay written blocked outcomes.
# The bundle, scenario and zone checks need the evaluator: without --hbf-root
# preview_policy stops at evaluator_unavailable, so a schema-valid request is
# written as blocked whether or not those later checks would have failed.
INPUT_BLOCKERS = ("invalid_policy_bundle", "invalid_scenario", "input_limit_exceeded", "ambiguous_equal_prefix_zones")


def _preview(value, root):
    from .hbf_bridge import load_hbf_adapter
    from .preview import preview_policy
    request = _parse(PreviewRequest, value)
    adapter = None
    if root is not None:
        # An explicitly selected source that cannot be loaded is an operator
        # input error; it never becomes a written evaluator_unavailable result.
        adapter = load_hbf_adapter(root)
        if adapter is None:
            raise OfflineInputError("evaluator_unavailable")
    result = preview_policy(request.base, request.candidate, request.scenarios, adapter=adapter)
    rejected = INPUT_BLOCKERS + (("evaluator_unavailable",) if root is not None else ())
    code = next((code for code in result.blocker_codes if code in rejected), None)
    if code is not None:
        raise OfflineInputError(code)
    return result


def _preconditions(value):
    from .preconditions import PreconditionCheck, check_preconditions
    return check_preconditions(_parse(PreconditionCheck, value))


def _rollout(value, evaluation_time):
    from .preconditions import PolicyReceipt, PreconditionObservation
    from .rollout import ProposedRollout, simulate_rollout

    class RolloutRequest(OfflineRequest):
        plan: ProposedRollout
        observations: tuple[PreconditionObservation, ...] = Field(default=(), max_length=128)
        receipts: tuple[PolicyReceipt, ...] = Field(default=(), max_length=256)

    request = _parse(RolloutRequest, value)
    return simulate_rollout(request.plan, observations=request.observations,
                            receipts=request.receipts, now=evaluation_time)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline preview and non-executable policy contracts")
    commands = parser.add_subparsers(dest="command", required=True)
    preview = commands.add_parser("preview", help="Evaluate explicit scenarios by running the HBF evaluator source "
                                  "the operator selects with --hbf-root as trusted local code")
    preview.add_argument("--hbf-root", type=Path, help="Explicit local HostBasedFirewall source directory chosen by the "
                         "operator; its Python evaluator files run as trusted local code without sandbox or producer "
                         "verification. A root that cannot be loaded exits 1 with evaluator_unavailable; without "
                         "--hbf-root the written result is blocked with evaluator_unavailable")
    check = commands.add_parser("check-preconditions", help="Check fixture CAS evidence without authorizing execution")
    rollout = commands.add_parser("validate-rollout", help="Simulate a non-executable fixture rollout")
    rollout.add_argument("--evaluation-time", required=True, help="Explicit UTC timestamp ending in Z")
    for command in (preview, check, rollout):
        command.add_argument("--input", required=True, type=Path)
        command.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        value = read_input(args.input)
        if args.command == "preview":
            result = _preview(value, args.hbf_root)
        elif args.command == "check-preconditions":
            result = _preconditions(value)
        else:
            result = _rollout(value, args.evaluation_time)
        write_output(args.output, result.model_dump(mode="json"), input_path=args.input)
        # Policy IPs, source documents, trace, identifiers and paths go only to
        # the explicitly selected output file, never normal console logs.
        print('{"status":"output_written","execution_authorized":false}')
        return 0
    except OfflineInputError as error:
        print(str(error), file=sys.stderr)
        return 1
    except (ValueError, TypeError, KeyError, OSError):
        print("policy_input_invalid", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
