"""Attach selected local evidence to immutable Phase24 record identities."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from commercial_handoff.input_loader import explicit_relative_path, output_location
from commercial_composition.source_inventory import read_explicit_text
from commercial_license_review.composition_adapter import load_composition
from commercial_license_review.component_identity import build_subjects
from commercial_license_review.conflict_analysis import build_conflicts
from commercial_license_review.evidence_binding import build_ledger
from commercial_license_review.evidence_contracts import DEMO_LABEL, InputError, parse_json, validate_scope
from commercial_license_review.evidence_manifest import publish_evidence
from commercial_license_review.evidence_reader import read_evidence_sources
from commercial_license_review.review_queue import build_queue


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "license_evidence: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Offline license evidence metadata; no approval path.", allow_abbrev=False)
    for name in ("scope", "termivar-root", "platform-root", "output-dir"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        output = output_location(args.output_dir)
        raw, _ = read_explicit_text(explicit_relative_path(args.scope), 128 * 1024)
        scope = validate_scope(parse_json(raw, maximum=128 * 1024))
        base = load_composition(scope)
        subjects = build_subjects(base)
        evidence = read_evidence_sources(scope, base,
                                         {"termivar": args.termivar_root, "platform": args.platform_root})
        ledger = build_ledger(base, subjects, evidence, scope["binding_requests"])
        conflicts = build_conflicts(ledger)
        queue = build_queue(ledger, conflicts)
        base.check_stability()
        publish_evidence(output, ledger, queue, conflicts)
    except InputError as error:
        print("license_evidence: " + str(error), file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError):
        print("license_evidence: local_evidence_preparation_failed; no successful delivery is claimed", file=sys.stderr)
        return 1
    print("Created demo license evidence ledger, review queue, binding analysis, Markdown and manifest")
    print(DEMO_LABEL)
    print("license_review_completed=false; redistribution_authorized=false; release_authorized=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
