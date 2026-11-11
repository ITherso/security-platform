"""Inspect one case ZIP locally without extracting it or opening source paths."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from commercial_case.bundle_reader import inspect_case_bundle, publish_inspection
from commercial_case.case_contracts import DEMO_LABEL, InputError


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "case_inspection: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Inspect a metadata-only demo case ZIP without extraction.",
                       allow_abbrev=False)
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        report = inspect_case_bundle(args.bundle)
        publish_inspection(args.output, report)
    except InputError as error:
        print("case_inspection: " + str(error), file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError):
        print("case_inspection: local_inspection_failed; no successful output is claimed", file=sys.stderr)
        return 1
    print("Created demo case inspection summary; internal_content_status=content_consistent")
    print(DEMO_LABEL)
    print("execution_binding=not_established; original_sources_read=false; source_relationships_rechecked=false")
    print("human_review_verified=false; producer_verified=false; release_authorized=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
