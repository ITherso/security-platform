"""Regenerate the offline Termivar analyst demo chain (phases 16-44) in a new workspace and compare bytes.

The runner builds the fixed layout the tools expect (W/security-platform as a real copy of the git-tracked
repository files, W/outputs), runs the documented demo commands of each phase in order with `python -I -B`
and workspace-relative paths, and compares the SHA256 of every produced file with
examples/offline-chain/expected-sha256.json. Phases whose external inputs were not supplied are NOT_RUN.

This is a byte-identical regeneration check of recorded demo outputs only. It does not review, verify,
approve or release any finding, source, delivery or decision, and it never runs a scanner or uses the network.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[1]
EXAMPLES = REPO / "examples" / "offline-chain"
EXPECTED_FILE = EXAMPLES / "expected-sha256.json"
DRAFT_FILE = EXAMPLES / "termivar-decision-draft.json"
DRAFT_TARGET = ("outputs", "phase19-exported", "termivar-decision-draft.json")
ZIP_TARGET = ("outputs", "Termivar-Offline-Module-Candidates-phase30-2026-11-12.zip")
SCHEMA = "security-platform-offline-chain-expected/v1"
INPUT_KEYS = ("termivar_commit", "phase19_decision_draft_sha256", "phase30_delivery_zip_sha256")
MAX_EXPECTED_BYTES = 256 * 1024
MAX_DRAFT_BYTES = 64 * 1024
MAX_ZIP_BYTES = 2 * 1024 * 1024
COMMAND_TIMEOUT = 900
TERMIVAR = "<TERMIVAR_ROOT>"
HEX64 = re.compile(r"[0-9a-f]{64}")
HEX40 = re.compile(r"[0-9a-f]{40}")
SAFE_TOOL_LINE = re.compile(r"[A-Za-z0-9_ .,:;=()-]{1,200}")
T = "security-platform/tools/"
P17, P18, P19 = "outputs/phase17-intake/", "outputs/phase18-review-packet/", "outputs/phase19-finalized-overlay/"
P24, P25, P26 = "outputs/phase24-composition/", "outputs/phase25-license-evidence/", "outputs/phase26-pilot-variants/"
P42, P43, P44 = "outputs/phase42-deferred-intake/", "outputs/phase43-task-exchange/", "outputs/phase44-task-reconciliation/"
PHASE44_INPUTS = (
    "--capsule " + P43 + "task-exchange-capsule.zip"
    " --request " + T + "commercial_task_reconciliation/examples/demo_reconciliation_request.json"
    " --local-register " + P42 + "deferred-intake-register.json --local-classification " + P42 +
    "intake-classification.json --local-intake-receipt " + P42 + "intake-source-receipt.json"
    " --local-intake-summary " + P42 + "intake-summary.md --local-intake-manifest " + P42 + "manifest.json"
    " --disclosed-capsule " + P43 + "task-exchange-capsule.zip --disclosed-index " + P43 + "task-exchange-index.json"
    " --disclosed-receipt " + P43 + "task-exchange-source-receipt.json --disclosed-summary " + P43 +
    "task-exchange-summary.md --disclosed-manifest " + P43 + "manifest.json")

# (phase, required external input, output directories under W/outputs, documented commands in order).
# Commands are the README / DEMO_DELIVERY demo commands with the security-platform/ prefix.
PHASES = (
    ("16", None, ("phase16-demo",), (
        T + "commercial_handoff/assemble.py --input " + T + "commercial_handoff/examples/demo_input.json"
        " --output-dir outputs/phase16-demo",)),
    ("17", None, ("phase17-intake", "phase17-handoff"), (
        T + "commercial_intake/assemble_intake.py --assessment security-platform/docs/commercial/examples/assessment.json"
        " --manifest security-platform/docs/commercial/examples/manifest.json --output-dir outputs/phase17-intake",
        T + "commercial_handoff/assemble.py --input " + P17 + "handoff-input.json --output-dir outputs/phase17-handoff")),
    ("18", None, ("phase18-review-packet", "phase18-reconciled", "phase18-handoff"), (
        T + "commercial_review/prepare_review.py --handoff-input " + P17 + "handoff-input.json --source-mapping " + P17 +
        "source-mapping.json --intake-manifest " + P17 + "intake-manifest.json --output-dir outputs/phase18-review-packet",
        T + "commercial_review/reconcile_review.py --review-packet " + P18 + "review-packet.json --packet-manifest " + P18 +
        "review-packet-manifest.json --handoff-input " + P17 + "handoff-input.json --overlay " + P18 +
        "decision-overlay.template.json --output-dir outputs/phase18-reconciled",
        T + "commercial_handoff/assemble.py --input outputs/phase18-reconciled/handoff-input.json"
        " --output-dir outputs/phase18-handoff")),
    ("19", None, ("phase19-review-desk", "phase19-finalized-overlay", "phase19-reconciled"), (
        T + "commercial_review_desk/prepare_desk.py --review-packet " + P18 + "review-packet.json --packet-manifest " + P18 +
        "review-packet-manifest.json --overlay-template " + P18 + "decision-overlay.template.json"
        " --output-dir outputs/phase19-review-desk",
        T + "commercial_review_desk/finalize_desk.py --review-packet " + P18 + "review-packet.json --packet-manifest " +
        P18 + "review-packet-manifest.json --handoff-input " + P17 + "handoff-input.json --decision-draft"
        " outputs/phase19-exported/termivar-decision-draft.json --output-dir outputs/phase19-finalized-overlay",
        T + "commercial_review/reconcile_review.py --review-packet " + P18 + "review-packet.json --packet-manifest " + P18 +
        "review-packet-manifest.json --handoff-input " + P17 + "handoff-input.json --overlay " + P19 +
        "decision-overlay.json --output-dir outputs/phase19-reconciled")),
    ("20", "termivar", ("phase20-scope",), (
        T + "commercial_scope/assemble_scope.py --proposal " + T + "commercial_scope/examples/demo_scope.json"
        " --termivar-source " + TERMIVAR + " --output-dir outputs/phase20-scope",)),
    ("21", "termivar", ("phase21-traceability",), (
        T + "commercial_traceability/assemble_traceability.py --plan outputs/phase20-scope/assessment-plan-proposal.json"
        " --preflight outputs/phase20-scope/scope-preflight.json --catalog outputs/phase20-scope/capability-catalog.json"
        " --plan-manifest outputs/phase20-scope/manifest.json --assessment"
        " security-platform/docs/commercial/examples/assessment.json --assessment-manifest"
        " security-platform/docs/commercial/examples/manifest.json --source-mapping " + P17 + "source-mapping.json"
        " --handoff-input " + P17 + "handoff-input.json --intake-manifest " + P17 + "intake-manifest.json"
        " --output-dir outputs/phase21-traceability",)),
    ("22", "termivar", ("phase22-case",), (
        T + "commercial_case/assemble_case.py --workspace-root . --case-map " + T +
        "commercial_case/examples/demo_case_map.json --output-dir outputs/phase22-case",
        T + "commercial_case/inspect_case.py --bundle outputs/phase22-case/termivar-demo-case.zip"
        " --output outputs/phase22-case/inspection-summary.json")),
    ("23", "termivar", ("phase23-portfolio",), (
        T + "commercial_portfolio/assemble_portfolio.py --portfolio-map " + T +
        "commercial_portfolio/examples/demo_portfolio_map.json --output-dir outputs/phase23-portfolio",
        T + "commercial_portfolio/inspect_portfolio.py --portfolio outputs/phase23-portfolio/portfolio-index.json"
        " --manifest outputs/phase23-portfolio/portfolio-manifest.json --summary outputs/phase23-portfolio/portfolio-summary.md"
        " --overview outputs/phase23-portfolio/portfolio-overview.html"
        " --output outputs/phase23-portfolio/portfolio-inspection.json")),
    ("24", "termivar", ("phase24-composition",), (
        T + "commercial_composition/assemble_composition.py --scope " + T +
        "commercial_composition/examples/demo_composition_scope.json --termivar-root " + TERMIVAR +
        " --platform-root security-platform --output-dir outputs/phase24-composition",
        T + "commercial_composition/inspect_composition.py --inventory " + P24 + "composition-inventory.json"
        " --dependencies " + P24 + "dependency-license-ledger.json --constraints " + P24 + "release-constraints.json"
        " --summary " + P24 + "composition-summary.md --manifest " + P24 + "manifest.json"
        " --output " + P24 + "inspection-summary.json")),
    ("25", "termivar", ("phase25-license-evidence",), (
        T + "commercial_license_review/assemble_evidence.py --scope " + T +
        "commercial_license_review/examples/demo_evidence_scope.json --termivar-root " + TERMIVAR +
        " --platform-root security-platform --output-dir outputs/phase25-license-evidence",
        T + "commercial_license_review/inspect_evidence.py --ledger " + P25 + "license-evidence-ledger.json"
        " --queue " + P25 + "review-queue.json --conflicts " + P25 + "binding-conflicts.json"
        " --summary " + P25 + "evidence-summary.md --manifest " + P25 + "manifest.json"
        " --output " + P25 + "inspection-summary.json")),
    ("26", "termivar", ("phase26-pilot-variants",), (
        T + "commercial_pilot_variants/assemble_variants.py --scope " + T +
        "commercial_pilot_variants/examples/demo_variant_scope.json --composition-inventory " + P24 +
        "composition-inventory.json --composition-dependencies " + P24 + "dependency-license-ledger.json"
        " --composition-constraints " + P24 + "release-constraints.json --composition-summary " + P24 +
        "composition-summary.md --composition-manifest " + P24 + "manifest.json --evidence-ledger " + P25 +
        "license-evidence-ledger.json --evidence-queue " + P25 + "review-queue.json --evidence-conflicts " + P25 +
        "binding-conflicts.json --evidence-summary " + P25 + "evidence-summary.md --evidence-manifest " + P25 +
        "manifest.json --output-dir outputs/phase26-pilot-variants",
        T + "commercial_pilot_variants/inspect_variants.py --analysis " + P26 + "variant-analysis.json"
        " --dependencies " + P26 + "dependency-exposure.json --licenses " + P26 + "license-readiness.json"
        " --summary " + P26 + "variant-comparison.md --manifest " + P26 + "manifest.json"
        " --output " + P26 + "inspection-summary.json")),
    ("27", "termivar", ("phase27-dependency-evidence",), (
        T + "commercial_dependency_evidence/assemble_evidence_graph.py --scope " + T +
        "commercial_dependency_evidence/examples/demo_dependency_scope.json --termivar-root " + TERMIVAR +
        " --composition-inventory " + P24 + "composition-inventory.json --composition-dependencies " + P24 +
        "dependency-license-ledger.json --composition-constraints " + P24 + "release-constraints.json"
        " --composition-summary " + P24 + "composition-summary.md --composition-manifest " + P24 + "manifest.json"
        " --variant-analysis " + P26 + "variant-analysis.json --variant-dependencies " + P26 + "dependency-exposure.json"
        " --variant-licenses " + P26 + "license-readiness.json --variant-summary " + P26 + "variant-comparison.md"
        " --variant-manifest " + P26 + "manifest.json --output-dir outputs/phase27-dependency-evidence",
        T + "commercial_dependency_evidence/inspect_evidence_graph.py"
        " --evidence outputs/phase27-dependency-evidence/direct-dependency-evidence.json"
        " --graph outputs/phase27-dependency-evidence/source-evidence-graph.json"
        " --variants outputs/phase27-dependency-evidence/variant-dependency-evidence.json"
        " --summary outputs/phase27-dependency-evidence/dependency-evidence-summary.md"
        " --manifest outputs/phase27-dependency-evidence/manifest.json"
        " --output outputs/phase27-dependency-evidence/inspection-summary.json")),
    ("28", "termivar", ("phase28-entrypoint-coverage",), (
        T + "commercial_entrypoint_coverage/assemble_coverage.py --scope " + T +
        "commercial_entrypoint_coverage/examples/demo_coverage_scope.json --termivar-root " + TERMIVAR +
        " --output-dir outputs/phase28-entrypoint-coverage",
        T + "commercial_entrypoint_coverage/inspect_coverage.py"
        " --coverage outputs/phase28-entrypoint-coverage/entrypoint-coverage.json"
        " --delta outputs/phase28-entrypoint-coverage/source-scope-delta.json"
        " --variants outputs/phase28-entrypoint-coverage/variant-entrypoint-projection.json"
        " --summary outputs/phase28-entrypoint-coverage/entrypoint-summary.md"
        " --manifest outputs/phase28-entrypoint-coverage/manifest.json"
        " --output outputs/phase28-entrypoint-coverage/inspection-summary.json")),
    ("29", "termivar", ("phase29-rust-source-graph-corrected",), (
        T + "commercial_rust_source_graph/assemble_source_graph.py --scope " + T +
        "commercial_rust_source_graph/examples/demo_source_graph_scope.json --termivar-root " + TERMIVAR +
        " --output-dir outputs/phase29-rust-source-graph-corrected",
        T + "commercial_rust_source_graph/inspect_source_graph.py"
        " --ledger outputs/phase29-rust-source-graph-corrected/source-reference-ledger.json"
        " --graph outputs/phase29-rust-source-graph-corrected/source-evidence-graph.json"
        " --coverage outputs/phase29-rust-source-graph-corrected/module-coverage-projection.json"
        " --summary outputs/phase29-rust-source-graph-corrected/source-graph-summary.md"
        " --manifest outputs/phase29-rust-source-graph-corrected/manifest.json"
        " --output outputs/phase29-rust-source-graph-corrected/inspection-summary.json")),
    ("30", "termivar", ("phase30-module-candidates",), (
        T + "commercial_module_candidates/assemble_candidates.py --scope " + T +
        "commercial_module_candidates/examples/demo_candidate_scope.json --termivar-root " + TERMIVAR +
        " --output-dir outputs/phase30-module-candidates",
        T + "commercial_module_candidates/inspect_candidates.py"
        " --evidence outputs/phase30-module-candidates/module-candidate-evidence.json"
        " --triage outputs/phase30-module-candidates/candidate-triage.json"
        " --coverage outputs/phase30-module-candidates/candidate-coverage.json"
        " --summary outputs/phase30-module-candidates/candidate-summary.md"
        " --manifest outputs/phase30-module-candidates/manifest.json"
        " --output outputs/phase30-module-candidates/inspection-summary.json")),
    ("31", "zip", ("phase31-candidate-revalidation",), (
        T + "commercial_candidate_revalidation/assemble_revalidation.py --scope " + T +
        "commercial_candidate_revalidation/examples/demo_revalidation_scope.json --termivar-root " + TERMIVAR +
        " --output-dir outputs/phase31-candidate-revalidation",
        T + "commercial_candidate_revalidation/inspect_revalidation.py"
        " --ledger outputs/phase31-candidate-revalidation/revalidation-ledger.json"
        " --reuse outputs/phase31-candidate-revalidation/evidence-reuse.json"
        " --summary outputs/phase31-candidate-revalidation/revalidation-summary.md"
        " --manifest outputs/phase31-candidate-revalidation/manifest.json"
        " --output outputs/phase31-candidate-revalidation/inspection-summary.json")),
    ("32", "zip", ("phase32-reference-metadata",), (
        T + "commercial_reference_metadata/assemble_metadata.py"
        " --ledger outputs/phase31-candidate-revalidation/revalidation-ledger.json"
        " --reuse outputs/phase31-candidate-revalidation/evidence-reuse.json"
        " --source-summary outputs/phase31-candidate-revalidation/revalidation-summary.md"
        " --source-manifest outputs/phase31-candidate-revalidation/manifest.json --request " + T +
        "commercial_reference_metadata/examples/demo_metadata_request.json --output-dir outputs/phase32-reference-metadata",
        T + "commercial_reference_metadata/inspect_metadata.py"
        " --response outputs/phase32-reference-metadata/reference-metadata-response.json"
        " --selection outputs/phase32-reference-metadata/metadata-selection-ledger.json"
        " --summary outputs/phase32-reference-metadata/metadata-summary.md"
        " --manifest outputs/phase32-reference-metadata/manifest.json"
        " --output outputs/phase32-reference-metadata/inspection-summary.json")),
    ("33", "zip", ("phase33-reference-capsule",), (
        T + "commercial_reference_capsule/assemble_capsule.py"
        " --response outputs/phase32-reference-metadata/reference-metadata-response.json"
        " --selection outputs/phase32-reference-metadata/metadata-selection-ledger.json"
        " --source-summary outputs/phase32-reference-metadata/metadata-summary.md"
        " --source-manifest outputs/phase32-reference-metadata/manifest.json --request " + T +
        "commercial_reference_capsule/examples/demo_capsule_request.json --output-dir outputs/phase33-reference-capsule",
        T + "commercial_reference_capsule/inspect_capsule.py"
        " --bundle outputs/phase33-reference-capsule/guarded-reference-capsule.zip"
        " --lookup-reference rust-ref-dfd6b59f25de8346b72d86fedce91afe4e9ace4f55fac7986019ede3b1ecef81"
        " --lookup-reference rust-ref-555f207606bbd8a43d836efed36f64587866e090fa212c2cadefb898c8c4ce1a"
        " --lookup-reference rust-ref-6bc3209001edb569d2477705369c3609f5befa7a0963dc53883935c1452d6c4a"
        " --inspection-output outputs/phase33-reference-capsule/capsule-inspection.json"
        " --lookup-output outputs/phase33-reference-capsule/lookup-results.json")),
    ("34", "zip", ("phase34-capsule-derivation",), (
        T + "commercial_capsule_derivation/derive_capsule.py"
        " --source-bundle outputs/phase33-reference-capsule/guarded-reference-capsule.zip --request " + T +
        "commercial_capsule_derivation/examples/demo_derivation_request.json --output-dir outputs/phase34-capsule-derivation",
        T + "commercial_capsule_derivation/inspect_derivation.py"
        " --source-bundle outputs/phase33-reference-capsule/guarded-reference-capsule.zip"
        " --derived-bundle outputs/phase34-capsule-derivation/derived-reference-capsule.zip"
        " --ledger outputs/phase34-capsule-derivation/derivation-ledger.json"
        " --summary outputs/phase34-capsule-derivation/derivation-summary.md"
        " --manifest outputs/phase34-capsule-derivation/manifest.json"
        " --output outputs/phase34-capsule-derivation/derivation-inspection.json")),
    ("35", "zip", ("phase35-capsule-tabular",), (
        T + "commercial_capsule_tabular/assemble_tabular.py"
        " --source-bundle outputs/phase34-capsule-derivation/derived-reference-capsule.zip --scope " + T +
        "commercial_capsule_tabular/examples/demo_tabular_scope.json --output-dir outputs/phase35-capsule-tabular",
        T + "commercial_capsule_tabular/inspect_tabular.py"
        " --source-bundle outputs/phase34-capsule-derivation/derived-reference-capsule.zip"
        " --dataset outputs/phase35-capsule-tabular/tabular-dataset.json"
        " --references outputs/phase35-capsule-tabular/reference-register.csv"
        " --projections outputs/phase35-capsule-tabular/projection-register.csv"
        " --summary outputs/phase35-capsule-tabular/tabular-summary.md"
        " --manifest outputs/phase35-capsule-tabular/manifest.json"
        " --output outputs/phase35-capsule-tabular/inspection-summary.json")),
    ("36", "zip", ("phase36-tabular-inbox",), (
        T + "commercial_tabular_inbox/assemble_inbox.py --dataset outputs/phase35-capsule-tabular/tabular-dataset.json"
        " --references outputs/phase35-capsule-tabular/reference-register.csv"
        " --projections outputs/phase35-capsule-tabular/projection-register.csv"
        " --source-summary outputs/phase35-capsule-tabular/tabular-summary.md"
        " --source-manifest outputs/phase35-capsule-tabular/manifest.json --request " + T +
        "commercial_tabular_inbox/examples/demo_import_request.json --output-dir outputs/phase36-tabular-inbox",
        T + "commercial_tabular_inbox/inspect_inbox.py --inbox outputs/phase36-tabular-inbox/typed-inbox.json"
        " --query outputs/phase36-tabular-inbox/reference-query.json"
        " --receipt outputs/phase36-tabular-inbox/import-receipt.json"
        " --summary outputs/phase36-tabular-inbox/inbox-summary.md --manifest outputs/phase36-tabular-inbox/manifest.json"
        " --output outputs/phase36-tabular-inbox/inspection-summary.json")),
    ("37", "zip", ("phase37-file-reference-index",), (
        T + "commercial_file_reference_index/assemble_file_index.py --inbox outputs/phase36-tabular-inbox/typed-inbox.json"
        " --source-query outputs/phase36-tabular-inbox/reference-query.json"
        " --receipt outputs/phase36-tabular-inbox/import-receipt.json"
        " --source-summary outputs/phase36-tabular-inbox/inbox-summary.md"
        " --source-manifest outputs/phase36-tabular-inbox/manifest.json --request " + T +
        "commercial_file_reference_index/examples/demo_file_lookup_request.json"
        " --output-dir outputs/phase37-file-reference-index",
        T + "commercial_file_reference_index/inspect_file_index.py"
        " --index outputs/phase37-file-reference-index/file-reference-index.json"
        " --lookup outputs/phase37-file-reference-index/file-reference-lookup.json"
        " --receipt outputs/phase37-file-reference-index/index-source-receipt.json"
        " --summary outputs/phase37-file-reference-index/file-index-summary.md"
        " --manifest outputs/phase37-file-reference-index/manifest.json"
        " --output outputs/phase37-file-reference-index/inspection-summary.json")),
    ("38", "zip", ("phase38-co-reference",), (
        T + "commercial_co_reference/assemble_co_reference.py"
        " --index outputs/phase37-file-reference-index/file-reference-index.json"
        " --source-lookup outputs/phase37-file-reference-index/file-reference-lookup.json"
        " --receipt outputs/phase37-file-reference-index/index-source-receipt.json"
        " --source-summary outputs/phase37-file-reference-index/file-index-summary.md"
        " --source-manifest outputs/phase37-file-reference-index/manifest.json --request " + T +
        "commercial_co_reference/examples/demo_co_reference_request.json --output-dir outputs/phase38-co-reference",
        T + "commercial_co_reference/inspect_co_reference.py --join outputs/phase38-co-reference/co-reference-join.json"
        " --lookup outputs/phase38-co-reference/co-reference-lookup.json"
        " --receipt outputs/phase38-co-reference/co-reference-source-receipt.json"
        " --summary outputs/phase38-co-reference/co-reference-summary.md"
        " --manifest outputs/phase38-co-reference/manifest.json"
        " --output outputs/phase38-co-reference/inspection-summary.json")),
    ("39", "zip", ("phase39-cohort-query",), (
        T + "commercial_cohort_query/assemble_cohort_query.py --join outputs/phase38-co-reference/co-reference-join.json"
        " --source-lookup outputs/phase38-co-reference/co-reference-lookup.json"
        " --receipt outputs/phase38-co-reference/co-reference-source-receipt.json"
        " --source-summary outputs/phase38-co-reference/co-reference-summary.md"
        " --source-manifest outputs/phase38-co-reference/manifest.json --request " + T +
        "commercial_cohort_query/examples/demo_cohort_request.json --output-dir outputs/phase39-cohort-query",
        T + "commercial_cohort_query/inspect_cohort_query.py --query outputs/phase39-cohort-query/cohort-query.json"
        " --witnesses outputs/phase39-cohort-query/cohort-witnesses.json"
        " --receipt outputs/phase39-cohort-query/cohort-source-receipt.json"
        " --summary outputs/phase39-cohort-query/cohort-summary.md --manifest outputs/phase39-cohort-query/manifest.json"
        " --output outputs/phase39-cohort-query/inspection-summary.json")),
    ("40", "zip", ("phase40-evidence-followup",), (
        T + "commercial_evidence_followup/assemble_evidence_followup.py"
        " --query outputs/phase39-cohort-query/cohort-query.json"
        " --witnesses outputs/phase39-cohort-query/cohort-witnesses.json"
        " --receipt outputs/phase39-cohort-query/cohort-source-receipt.json"
        " --source-summary outputs/phase39-cohort-query/cohort-summary.md"
        " --source-manifest outputs/phase39-cohort-query/manifest.json --request " + T +
        "commercial_evidence_followup/examples/demo_followup_request.json --output-dir outputs/phase40-evidence-followup",
        T + "commercial_evidence_followup/inspect_evidence_followup.py"
        " --queue outputs/phase40-evidence-followup/evidence-followup-queue.json"
        " --handoff outputs/phase40-evidence-followup/analyst-handoff.json"
        " --receipt outputs/phase40-evidence-followup/followup-source-receipt.json"
        " --summary outputs/phase40-evidence-followup/followup-summary.md"
        " --manifest outputs/phase40-evidence-followup/manifest.json"
        " --output outputs/phase40-evidence-followup/inspection-summary.json")),
    ("41", "zip", ("phase41-response-slots",), (
        T + "commercial_response_slots/assemble_response_slots.py"
        " --queue outputs/phase40-evidence-followup/evidence-followup-queue.json"
        " --handoff outputs/phase40-evidence-followup/analyst-handoff.json"
        " --receipt outputs/phase40-evidence-followup/followup-source-receipt.json"
        " --source-summary outputs/phase40-evidence-followup/followup-summary.md"
        " --source-manifest outputs/phase40-evidence-followup/manifest.json --request " + T +
        "commercial_response_slots/examples/demo_slot_request.json --output-dir outputs/phase41-response-slots",
        T + "commercial_response_slots/inspect_response_slots.py"
        " --slots outputs/phase41-response-slots/task-response-slots.json"
        " --template outputs/phase41-response-slots/response-template.json"
        " --receipt outputs/phase41-response-slots/response-slot-source-receipt.json"
        " --summary outputs/phase41-response-slots/response-slot-summary.md"
        " --manifest outputs/phase41-response-slots/manifest.json"
        " --output outputs/phase41-response-slots/inspection-summary.json")),
    ("42", "zip", ("phase42-deferred-intake",), (
        T + "commercial_deferred_intake/assemble_deferred_intake.py"
        " --slots outputs/phase41-response-slots/task-response-slots.json"
        " --template outputs/phase41-response-slots/response-template.json"
        " --receipt outputs/phase41-response-slots/response-slot-source-receipt.json"
        " --source-summary outputs/phase41-response-slots/response-slot-summary.md"
        " --source-manifest outputs/phase41-response-slots/manifest.json --request " + T +
        "commercial_deferred_intake/examples/demo_intake_request.json --output-dir outputs/phase42-deferred-intake",
        T + "commercial_deferred_intake/inspect_deferred_intake.py --intake " + P42 + "deferred-intake-register.json"
        " --classification " + P42 + "intake-classification.json --receipt " + P42 + "intake-source-receipt.json"
        " --summary " + P42 + "intake-summary.md --manifest " + P42 + "manifest.json"
        " --output " + P42 + "inspection-summary.json")),
    ("43", "zip", ("phase43-task-exchange",), (
        T + "commercial_task_exchange/assemble_task_exchange.py --register " + P42 + "deferred-intake-register.json"
        " --classification " + P42 + "intake-classification.json --receipt " + P42 + "intake-source-receipt.json"
        " --source-summary " + P42 + "intake-summary.md --source-manifest " + P42 + "manifest.json --request " + T +
        "commercial_task_exchange/examples/demo_task_exchange_request.json --output-dir outputs/phase43-task-exchange",
        T + "commercial_task_exchange/inspect_task_exchange.py --capsule " + P43 + "task-exchange-capsule.zip"
        " --index " + P43 + "task-exchange-index.json --receipt " + P43 + "task-exchange-source-receipt.json"
        " --summary " + P43 + "task-exchange-summary.md --manifest " + P43 + "manifest.json"
        " --output " + P43 + "inspection-summary.json")),
    ("44", "zip", ("phase44-task-reconciliation",), (
        T + "commercial_task_reconciliation/import_task_capsule.py " + PHASE44_INPUTS +
        " --output-dir outputs/phase44-task-reconciliation",
        T + "commercial_task_reconciliation/inspect_task_reconciliation.py " + PHASE44_INPUTS +
        " --inbox " + P44 + "task-inbox-record.json --report " + P44 + "capsule-reconciliation-report.json"
        " --summary " + P44 + "capsule-reconciliation-summary.md --manifest " + P44 + "manifest.json"
        " --output " + P44 + "inspection-summary.json")),
)


class SetupError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "offline_chain: invalid_arguments\n")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _extended(path: Path) -> str:
    """Windows extended-length form so the repository copy is not limited by MAX_PATH."""
    text = str(path)
    return "\\\\?\\" + text if os.name == "nt" and not text.startswith("\\\\") else text


def _inside(path: Path, root: Path) -> bool:
    child, parent = os.path.normcase(str(path)), os.path.normcase(os.path.realpath(root))
    try:
        return os.path.commonpath([child, parent]) == parent
    except ValueError:
        return False


def _no_duplicates(pairs):
    data = {}
    for key, value in pairs:
        if key in data:
            raise ValueError("duplicate key")
        data[key] = value
    return data


def load_expected() -> dict:
    try:
        raw = EXPECTED_FILE.read_bytes()
        if len(raw) > MAX_EXPECTED_BYTES:
            raise ValueError("oversize")
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicates)
        if set(data) != {"schema_version", "mode", "derived_from", "inputs", "phases"}:
            raise ValueError("fields")
        if data["schema_version"] != SCHEMA or data["mode"] != "demo" or not isinstance(data["derived_from"], str):
            raise ValueError("header")
        inputs = data["inputs"]
        if set(inputs) != set(INPUT_KEYS) or not HEX40.fullmatch(inputs["termivar_commit"]):
            raise ValueError("inputs")
        if not all(HEX64.fullmatch(inputs[key]) for key in INPUT_KEYS[1:]):
            raise ValueError("inputs")
        if list(data["phases"]) != [phase for phase, _need, _dirs, _commands in PHASES]:
            raise ValueError("phases")
        for phase, _need, directories, _commands in PHASES:
            files = data["phases"][phase]
            if not isinstance(files, dict) or not files:
                raise ValueError("phase")
            for name, digest in files.items():
                parts = name.split("/")
                if (len(parts) != 3 or parts[0] != "outputs" or parts[1] not in directories
                        or not parts[2] or parts[2] in (".", "..") or not HEX64.fullmatch(digest)):
                    raise ValueError("entry")
        return data
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, AttributeError, RecursionError):
        raise SetupError("expected_hashes_invalid") from None


def check_workspace(raw: str) -> Path:
    path = Path(os.path.realpath(os.path.abspath(raw)))
    if _inside(path, REPO):
        raise SetupError("workspace_inside_repository")
    if os.path.lexists(path):
        if not path.is_dir():
            raise SetupError("workspace_not_directory")
        try:
            if any(path.iterdir()):
                raise SetupError("workspace_not_empty")
        except OSError:
            raise SetupError("workspace_unreadable") from None
    elif not path.parent.is_dir():
        raise SetupError("workspace_parent_missing")
    return path


def check_termivar(raw: str, expected: dict, workspace: Path) -> str:
    path = Path(os.path.realpath(os.path.abspath(raw)))
    if not path.is_dir():
        raise SetupError("termivar_root_missing")
    if _inside(workspace, path) or _inside(path, workspace):
        raise SetupError("workspace_overlaps_termivar_root")
    try:
        result = subprocess.run(["git", "--no-optional-locks", "-C", str(path), "rev-parse", "HEAD"],
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                timeout=60, check=False)
    except (OSError, subprocess.SubprocessError):
        raise SetupError("termivar_root_commit_unreadable") from None
    if result.returncode or result.stdout.decode("ascii", "replace").strip() != expected["inputs"]["termivar_commit"]:
        raise SetupError("termivar_root_commit_mismatch")
    return str(path)


def read_delivery_zip(raw: str, expected: dict) -> bytes:
    path = Path(os.path.abspath(raw))
    try:
        if not path.is_file() or path.stat().st_size > MAX_ZIP_BYTES:
            raise SetupError("phase30_delivery_zip_identity_mismatch")
        data = path.read_bytes()
    except OSError:
        raise SetupError("phase30_delivery_zip_unreadable") from None
    if len(data) > MAX_ZIP_BYTES or _sha256(data) != expected["inputs"]["phase30_delivery_zip_sha256"]:
        raise SetupError("phase30_delivery_zip_identity_mismatch")
    return data


def tracked_files() -> list:
    try:
        result = subprocess.run(["git", "--no-optional-locks", "-C", str(REPO), "ls-files", "-z", "--cached"],
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                timeout=120, check=False)
        names = [name for name in result.stdout.decode("utf-8").split("\0") if name]
    except (OSError, subprocess.SubprocessError, UnicodeError):
        raise SetupError("repository_file_list_unavailable") from None
    if result.returncode or not names:
        raise SetupError("repository_file_list_unavailable")
    for name in names:
        parts = name.split("/")
        if (name.startswith("/") or "\\" in name or ":" in name
                or any(part in ("", ".", "..") for part in parts)):
            raise SetupError("repository_file_list_unsafe")
    return names


def prepare_workspace(workspace: Path, expected: dict, zip_bytes) -> int:
    names = tracked_files()
    try:
        draft = DRAFT_FILE.read_bytes()
    except OSError:
        raise SetupError("decision_draft_unreadable") from None
    if len(draft) > MAX_DRAFT_BYTES or _sha256(draft) != expected["inputs"]["phase19_decision_draft_sha256"]:
        raise SetupError("decision_draft_identity_mismatch")
    copied = 0
    try:
        workspace.mkdir(exist_ok=True)
        if any(workspace.iterdir()):
            raise SetupError("workspace_not_empty")
        root = workspace / "security-platform"
        root.mkdir()
        for name in names:
            source = _extended(REPO.joinpath(*name.split("/")))
            if os.path.islink(source) or not os.path.isfile(source):
                continue
            target = root.joinpath(*name.split("/"))
            os.makedirs(_extended(target.parent), exist_ok=True)
            shutil.copyfile(source, _extended(target))
            copied += 1
        (workspace / "outputs" / "phase19-exported").mkdir(parents=True)
        workspace.joinpath(*DRAFT_TARGET).write_bytes(draft)
        if zip_bytes is not None:
            workspace.joinpath(*ZIP_TARGET).write_bytes(zip_bytes)
        (workspace / "run-logs").mkdir()
    except OSError:
        raise SetupError("workspace_setup_failed") from None
    return copied


def run_command(workspace: Path, termivar, command: str, log: Path) -> tuple:
    argv = [sys.executable, "-I", "-B", *[termivar if part == TERMIVAR else part for part in command.split()]]
    try:
        result = subprocess.run(argv, cwd=workspace, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=COMMAND_TIMEOUT, check=False)
        code, out, err = result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        code, out, err = -1, b"", b"offline_chain: command_timeout\n"
    except OSError:
        code, out, err = -2, b"", b"offline_chain: command_start_failed\n"
    with open(log, "ab") as handle:
        handle.write(("$ python -I -B " + " ".join(argv[3:]) + "\nexit=" + str(code) + "\n").encode("utf-8"))
        handle.write(b"--- stdout\n" + out + b"\n--- stderr\n" + err + b"\n")
    lines = [line.strip() for line in err.decode("utf-8", "replace").splitlines() if line.strip()]
    message = lines[-1] if lines and SAFE_TOOL_LINE.fullmatch(lines[-1]) else "tool_message_withheld"
    return code, message


def compare_phase(workspace: Path, directories: tuple, files: dict, log: Path) -> tuple:
    matched, problems = 0, []
    for name, digest in files.items():
        path = workspace.joinpath(*name.split("/"))
        if path.is_symlink() or not path.is_file():
            problems.append("missing " + name)
        elif _file_sha256(path) != digest:
            problems.append("sha256_differs " + name)
        else:
            matched += 1
    for directory in directories:
        folder = workspace / "outputs" / directory
        if folder.is_dir():
            for item in sorted(folder.iterdir(), key=lambda entry: entry.name):
                name = "outputs/" + directory + "/" + item.name
                if name not in files:
                    problems.append("unexpected " + name)
    if problems:
        with open(log, "ab") as handle:
            handle.write(("--- comparison\n" + "\n".join(problems) + "\n").encode("utf-8"))
    return matched, len(problems)


def run_chain(workspace: Path, expected: dict, termivar, have_zip: bool) -> tuple:
    rows, blocked = [], None
    print("phase  status          exits        files    seconds  note", flush=True)
    for phase, need, directories, commands in PHASES:
        files = expected["phases"][phase]
        reason = blocked
        if reason is None and need is not None and termivar is None:
            reason = "termivar_root_not_supplied"
        elif reason is None and need == "zip" and not have_zip:
            reason = "phase30_delivery_zip_not_supplied"
        if reason is not None:
            row = (phase, "NOT_RUN", "-", 0, len(files), "-", reason)
        else:
            started, exits, note = time.perf_counter(), [], ""
            log = workspace / "run-logs" / ("phase" + phase + ".log")
            for command in commands:
                code, message = run_command(workspace, termivar, command, log)
                exits.append(str(code))
                if code != 0:
                    note = message
                    break
            matched, problems = compare_phase(workspace, directories, files, log)
            if note:
                status = "COMMAND_FAILED"
            elif problems:
                status, note = "MISMATCH", "differing_or_missing_or_unexpected=" + str(problems)
            else:
                status = "MATCHED"
            row = (phase, status, ",".join(exits), matched, len(files),
                   "%.1f" % (time.perf_counter() - started), note)
            if status != "MATCHED":
                blocked = "upstream_failed"
        rows.append(row)
        print(("%-6s %-15s %-12s %-8s %-8s %s" % (row[0], row[1], row[2], "%d/%d" % (row[3], row[4]), row[5],
                                                  row[6])).rstrip(), flush=True)
    return rows


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Regenerate the offline Termivar demo chain (phases 16-44) in a new workspace "
                                   "and compare every output with the recorded SHA256 values.", allow_abbrev=False)
    parser.add_argument("--workspace", required=True,
                        help="new or empty directory; everything is written inside it")
    parser.add_argument("--termivar-root",
                        help="Termivar checkout at the pinned commit; enables phases 20-30")
    parser.add_argument("--phase30-delivery-zip",
                        help="Termivar-Offline-Module-Candidates-phase30-2026-11-12.zip; with --termivar-root "
                             "enables phases 31-44")
    args = parser.parse_args(argv)
    if sys.version_info < (3, 11):
        print("offline_chain: python_3_11_or_newer_required", file=sys.stderr)
        return 2
    started = time.perf_counter()
    try:
        expected = load_expected()
        workspace = check_workspace(args.workspace)
        termivar = check_termivar(args.termivar_root, expected, workspace) if args.termivar_root else None
        zip_bytes = read_delivery_zip(args.phase30_delivery_zip, expected) if args.phase30_delivery_zip else None
        copied = prepare_workspace(workspace, expected, zip_bytes)
    except SetupError as error:
        print("offline_chain: " + error.code + "; nothing was run", file=sys.stderr)
        return 2
    print("offline_chain: workspace prepared; repository_files_copied=%d termivar_root=%s phase30_delivery_zip=%s"
          % (copied, "supplied" if termivar else "not_supplied",
             "supplied" if zip_bytes is not None else "not_supplied"), flush=True)
    try:
        rows = run_chain(workspace, expected, termivar, zip_bytes is not None)
    except OSError:
        print("offline_chain: result=FAILED workspace_read_or_write_failed", file=sys.stderr)
        return 1
    matched_phases = sum(1 for row in rows if row[1] == "MATCHED")
    failed = sum(1 for row in rows if row[1] in ("COMMAND_FAILED", "MISMATCH"))
    not_run = sum(1 for row in rows if row[1] == "NOT_RUN")
    result = "FAILED" if failed else "ALL_MATCHED" if not not_run else "PARTIAL_MATCHED"
    print("offline_chain: result=%s phases_matched=%d phases_failed=%d phases_not_run=%d files_matched=%d/%d "
          "seconds=%.1f" % (result, matched_phases, failed, not_run, sum(row[3] for row in rows),
                            sum(row[4] for row in rows), time.perf_counter() - started))
    print("offline_chain: per-phase command logs are in the workspace run-logs directory")
    print("offline_chain: byte comparison with recorded demo outputs only; no finding, source, decision or "
          "delivery is reviewed, verified or approved")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
