"""Import one explicit capsule into an untrusted local inbox record and reconcile it.

Exit codes: 0 = outputs published and the capsule is
STRUCTURALLY_VALID_REQUIRES_MANUAL_REVIEW; 3 = outputs published with a
non-eligible status (rejection, mismatch or unavailable reconciliation);
2 = arguments, inputs or local records rejected, nothing published;
1 = unexpected failure, nothing claimed. No task is sent, assigned,
approved, executed, completed or submitted.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reconciliation_paths  # noqa: E402

reconciliation_paths.install()

from exchange_contracts import InputError  # noqa: E402
from reconciliation_contracts import Eligibility  # noqa: E402
from reconciliation_engine import reconcile_capsule  # noqa: E402
from reconciliation_inputs import add_input_arguments, load_inputs  # noqa: E402
from reconciliation_manifest import input_identities, output_documents, publish_outputs  # noqa: E402


def import_task_capsule(args) -> dict:
    inputs = load_inputs(args)
    report, inbox = reconcile_capsule(inputs.capsule, inputs.request, inputs.local)
    documents = output_documents(report, inbox, input_identities(inputs.capsule, inputs.request_raw, inputs.local))
    inputs.budget.check_stability()
    publish_outputs(args.output_dir, documents)
    return report


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "task_reconciliation: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Offline untrusted capsule import and reconciliation; no dispatch or submission.",
                       allow_abbrev=False)
    add_input_arguments(parser)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    try:
        report = import_task_capsule(args)
    except FileNotFoundError:
        print("task_reconciliation: missing_explicit_input", file=sys.stderr)
        return 2
    except InputError:
        print("task_reconciliation: input_or_local_record_rejected; nothing published", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError,
            IndexError, RecursionError, StopIteration, EOFError, OverflowError):
        print("task_reconciliation: rejected; no reconciliation is claimed", file=sys.stderr)
        return 1
    status = report["eligibility"]["status"]
    print("Created untrusted task inbox record, reconciliation report, summary and manifest")
    print(report["demo_label"])
    print("eligibility_status=" + status + "; manual_review_requirement=REQUIRED")
    print("task_dispatched=false; task_assigned=false; producer_authenticated=false; response_submitted=false")
    return 0 if status == Eligibility.STRUCTURALLY_VALID_REQUIRES_MANUAL_REVIEW else 3


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ("import_task_capsule", "main")
