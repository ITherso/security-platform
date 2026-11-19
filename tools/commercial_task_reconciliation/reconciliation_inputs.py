"""Explicit CLI inputs shared by the import command and the inspector.

Only the paths named on the command line are opened, through the existing
bounded owner readers (phase42_adapter.InputBudget). No directory is scanned.
"""
from __future__ import annotations

from dataclasses import dataclass

from exchange_contracts import MAX_CAPSULE_BYTES, MAX_TOTAL_INPUT_BYTES, parse_json
from reconciliation_contracts import MAX_REQUEST_BYTES, fail, validate_request

PHASE42_OPTIONS = ("local-register", "local-classification", "local-intake-receipt",
                   "local-intake-summary", "local-intake-manifest")
PHASE43_OPTIONS = ("disclosed-capsule", "disclosed-index", "disclosed-receipt",
                   "disclosed-summary", "disclosed-manifest")


@dataclass(frozen=True, slots=True)
class LoadedInputs:
    capsule: bytes
    request_raw: bytes
    request: dict
    local: object
    budget: object


def add_input_arguments(parser) -> None:
    parser.add_argument("--capsule", required=True)
    parser.add_argument("--request", required=True)
    for name in (*PHASE42_OPTIONS, *PHASE43_OPTIONS):
        parser.add_argument("--" + name)


def _group(args, options: tuple) -> tuple | None:
    values = [getattr(args, name.replace("-", "_")) for name in options]
    if all(value is None for value in values):
        return None
    if any(value is None for value in values):
        fail("partial_local_record_group")
    return tuple(values)


def load_inputs(args) -> LoadedInputs:
    from phase42_adapter import InputBudget
    from local_task_records import load_local_reference

    budget = InputBudget(maximum=MAX_TOTAL_INPUT_BYTES)
    request_raw = budget.read_text(args.request, MAX_REQUEST_BYTES)
    request = validate_request(parse_json(request_raw, maximum=MAX_REQUEST_BYTES))
    capsule = budget.read_binary(args.capsule, MAX_CAPSULE_BYTES)
    local = load_local_reference(request, budget, _group(args, PHASE42_OPTIONS), _group(args, PHASE43_OPTIONS))
    return LoadedInputs(capsule, request_raw, request, local, budget)


__all__ = ("LoadedInputs", "PHASE42_OPTIONS", "PHASE43_OPTIONS", "add_input_arguments", "load_inputs")
