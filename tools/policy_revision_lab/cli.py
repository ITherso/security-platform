"""Explicit laboratory commands. No production entrypoint or execution mode."""
import argparse
from pathlib import Path
import re
import sys
from typing import Literal

from pydantic import field_validator

from security_platform.policy_contracts.hbf_bridge import load_hbf_adapter
from security_platform.policy_contracts.offline_io import OfflineInputError, read_input, write_output
from .models import AppendRequest, LabBinding, LabError, LabGuards, LabHead

REPORT_BLOCKERS = ("precondition_evidence_missing", "execution_not_implemented",
                   "windows_acceptance_missing", "authorization_not_evaluated", "verification_not_performed")


class LabReport(LabGuards):
    status: Literal["unbound_lab_state_only"] = "unbound_lab_state_only"
    head: LabHead
    precondition_status: Literal["precondition_evidence_missing"] = "precondition_evidence_missing"
    rollout_status: Literal["would_pause"] = "would_pause"
    blockers: tuple[str, ...] = REPORT_BLOCKERS
    revision_meaning: Literal["draft_or_staged_lab_revision_only"] = "draft_or_staged_lab_revision_only"

    @field_validator("blockers", mode="before")
    @classmethod
    def fixed_blockers(cls, value):
        if not isinstance(value, (tuple, list)) or tuple(value) != REPORT_BLOCKERS:
            raise ValueError("lab_blockers_cannot_be_cleared")
        return tuple(value)


def lab_report(head):
    """Never convert a lab revision into operational policy CAS evidence."""
    return LabReport(head=LabHead.model_validate(head))


def _output_boundary(args):
    target = args.output.resolve()
    inputs = [args.input] if getattr(args, "input", None) is not None else []
    if getattr(args, "binding_file", None) is not None:
        inputs.append(args.binding_file)
    if getattr(args, "location", None) is not None:
        inputs.append(args.location)
        if args.backend == "endpoint" and target.is_relative_to(args.location.resolve()):
            raise LabError("lab_output_inside_store")
    if any(target == source.resolve() for source in inputs):
        raise LabError("lab_output_is_input")
    if getattr(args, "hbf_root", None) is not None and target.is_relative_to(args.hbf_root.resolve()):
        raise LabError("lab_output_inside_hbf_source")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Isolated draft/staged revision laboratory; never apply policies")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "append", "read", "check", "report"):
        command = commands.add_parser(name)
        command.add_argument("--backend", required=True, choices=("endpoint", "controller"))
        command.add_argument("--location", required=True, type=Path,
                             help="New private endpoint directory or explicit protected controller config file")
        command.add_argument("--binding-file", required=True, type=Path)
        command.add_argument("--hbf-root", required=True, type=Path)
        command.add_argument("--output", required=True, type=Path)
        if name == "append":
            command.add_argument("--input", required=True, type=Path)
    windows = commands.add_parser("windows-report", help="Validate supplied evidence format without running Windows checks")
    windows.add_argument("--input", required=True, type=Path)
    windows.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        _output_boundary(args)
        if args.command == "windows-report":
            from .windows_evidence import validate_windows_evidence
            result = validate_windows_evidence(read_input(args.input))
            input_path = args.input
        else:
            binding = LabBinding.model_validate(read_input(args.binding_file))
            if binding.kind != {"endpoint": "endpoint_staged", "controller": "controller_draft"}[args.backend]:
                raise LabError("lab_binding_mismatch")
            adapter = load_hbf_adapter(args.hbf_root)
            if adapter is None:
                raise LabError("lab_evaluator_unavailable")
            if args.backend == "endpoint":
                from .endpoint_store import EndpointStore as Store
            else:
                from .controller_store import ControllerStore as Store
            request = AppendRequest.model_validate(read_input(args.input)) if args.command == "append" else None
            factory = Store.init if args.command == "init" else Store.open
            with factory(args.location, binding, adapter=adapter) as store:
                if args.command == "append":
                    result = store.append(request)
                elif args.command == "check":
                    result = store.check()
                elif args.command == "report":
                    result = lab_report(store.read())
                else:
                    result = store.read()
            input_path = args.input if args.command == "append" else args.binding_file
        write_output(args.output, result.model_dump(mode="json"), input_path=input_path)
        print('{"status":"lab_output_written","execution_authorized":false}')
        return 0
    except (LabError, OfflineInputError) as error:
        code = getattr(error, "code", str(error))
        print(code if isinstance(code, str) and re.fullmatch(r"[a-z][a-z0-9_]{0,79}", code)
              else "lab_operation_failed", file=sys.stderr)
        return 1
    except (ValueError, TypeError, KeyError, OSError):
        print("lab_input_invalid", file=sys.stderr)
        return 1
    except Exception:
        # Database/driver failures can contain connection strings or payloads.
        # The explicit CLI reports failure without dumping exceptions or locals.
        print("lab_operation_failed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
