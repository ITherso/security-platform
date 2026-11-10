"""Generate demo-only documents. Never execute Termivar or contact a target."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

# Direct-file invocation also works with Python -I, without importing production src.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from commercial_handoff.input_loader import load_input, output_location
from commercial_handoff.manifest import manifest_bytes, publish
from commercial_handoff.renderer import render_documents
from commercial_handoff.review_rules import build_models
from commercial_handoff.schema import InputError


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "handoff_builder: invalid_arguments\n")


def main(argv=None) -> int:
    parser = Arguments(description="Create demo-only internal/client document drafts.", allow_abbrev=False)
    parser.add_argument("--input", required=True, help="One explicit cwd-relative JSON file.")
    parser.add_argument("--output-dir", required=True, help="New cwd-relative directory; parent must exist.")
    args = parser.parse_args(argv)
    try:
        loaded = load_input(args.input)
        output = output_location(args.output_dir)
        internal, client = build_models(loaded.document)
        documents = render_documents(internal, client)
        metadata = manifest_bytes(loaded, documents, internal.delivery_blockers)
        publish(output, documents, metadata)
    except InputError as error:
        print("handoff_builder: " + str(error), file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError):
        print("handoff_builder: local_generation_failed; no successful delivery is claimed", file=sys.stderr)
        return 1
    print("Created demo-only drafts: internal-review-summary.md, client-handoff-draft.md, client-handoff-draft.html, manifest.json")
    print("release_authorized=false; human_review_verified=false; client delivery is not authorized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
