"""Create an offline portfolio from explicitly selected existing case ZIPs."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from commercial_handoff.input_loader import output_location
from commercial_portfolio.case_bundle_adapter import load_case_bundles
from commercial_portfolio.portfolio_contracts import DEMO_LABEL, InputError, read_portfolio_map
from commercial_portfolio.portfolio_index import build_portfolio
from commercial_portfolio.portfolio_manifest import publish_portfolio


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "portfolio: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Offline demo portfolio; no source revalidation or execution authority.",
                       allow_abbrev=False)
    parser.add_argument("--portfolio-map", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    try:
        output = output_location(args.output_dir)
        selected = read_portfolio_map(args.portfolio_map)
        cases = load_case_bundles(selected)
        index = build_portfolio(selected, cases)
        publish_portfolio(output, index)
    except InputError as error:
        print("portfolio: " + str(error), file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError):
        print("portfolio: local_preparation_failed; no successful portfolio is claimed", file=sys.stderr)
        return 1
    print("Created offline demo portfolio JSON, Markdown, static HTML and manifest")
    print(DEMO_LABEL)
    print("execution_binding=not_established; human_review_verified=false; release_authorized=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
