"""Read explicit portfolio payloads without reopening any source case ZIP."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from commercial_case.bundle_reader import publish_inspection
from commercial_portfolio.portfolio_contracts import (
    DEMO_LABEL, FALSE_FLAGS, PORTFOLIO_CONTRACT, InputError, parse_json_bytes,
    portfolio_to_dict, validate_portfolio,
)
from commercial_portfolio.portfolio_manifest import read_selected_bytes, validate_manifest
from commercial_portfolio.portfolio_renderer import render_html, render_markdown


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "portfolio_inspection: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Inspect explicit offline portfolio JSON, Markdown, HTML and manifest bytes.",
                       allow_abbrev=False)
    for name in ("portfolio", "manifest", "summary", "overview", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        portfolio_raw = read_selected_bytes(args.portfolio, 512 * 1024, ".json")
        manifest_raw = read_selected_bytes(args.manifest, 64 * 1024, ".json")
        summary_raw = read_selected_bytes(args.summary, 128 * 1024, ".md")
        overview_raw = read_selected_bytes(args.overview, 512 * 1024, ".html")
        index = validate_portfolio(parse_json_bytes(portfolio_raw, maximum=512 * 1024))
        payloads = {"portfolio-index.json": portfolio_raw,
                    "portfolio-summary.md": summary_raw,
                    "portfolio-overview.html": overview_raw}
        validate_manifest(parse_json_bytes(manifest_raw, maximum=64 * 1024), index, payloads)
        if summary_raw != render_markdown(index) or overview_raw != render_html(index):
            raise InputError("portfolio_rendered_projection_mismatch")
        data = portfolio_to_dict(index)
        report = {
            "schema_version": "termivar-offline-portfolio-inspection/v1",
            "portfolio_contract": PORTFOLIO_CONTRACT,
            "portfolio_reference": index.portfolio_reference,
            "demo_label": DEMO_LABEL,
            "internal_content_status": "content_consistent",
            "input_files": [{"role": role, "bytes": len(raw),
                             "sha256": hashlib.sha256(raw).hexdigest()}
                            for role, raw in (("portfolio", portfolio_raw),
                                              ("manifest", manifest_raw),
                                              ("summary", summary_raw),
                                              ("overview", overview_raw))],
            "payload_bindings": [{"name": name, "bytes": len(raw),
                                  "sha256": hashlib.sha256(raw).hexdigest(),
                                  "status": "content_consistent"}
                                 for name, raw in payloads.items()],
            "totals": data["totals"],
            "blocker_summary": data["blocker_summary"],
            "stage_summary": data["stage_summary"],
            "case_bundles": [{"case_reference": case.case_reference,
                              "sha256": case.bundle_sha256,
                              "byte_length": case.bundle_byte_length}
                             for case in index.cases],
            "source_map_read": False,
            "source_case_bundles_read": False,
            "original_sources_read": False,
            "source_relationships_rechecked": False,
            "browser_visual_acceptance_performed": False,
            "inspection_scope": "four_explicit_portfolio_files_and_rederived_metadata_only",
            "integrity_limit": "The portfolio and three payload bytes are internally consistent. Source case ZIPs, original artifacts, producer, human decisions, authorization and execution are not revalidated.",
            "demo_only": True, "execution_binding": "not_established",
            **{flag: False for flag in FALSE_FLAGS},
        }
        publish_inspection(args.output, report)
    except InputError as error:
        print("portfolio_inspection: " + str(error), file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError):
        print("portfolio_inspection: local_inspection_failed; no successful inspection is claimed", file=sys.stderr)
        return 1
    print("Created demo portfolio inspection; internal_content_status=content_consistent")
    print(DEMO_LABEL)
    print("source_case_bundles_read=false; execution_binding=not_established; release_authorized=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
