"""Recorded five-artifact import receipt, without producer or import proof."""
from __future__ import annotations

from inbox_contracts import (
    CSV_HEADERS, LIMITATIONS, RECEIPT_SCHEMA, RECEIPT_SCOPE,
    SOURCE_MANIFEST_SCHEMA, common, validate_receipt,
)
from inbox_snapshot import ValidatedInbox, read_typed_inbox


def build_import_receipt(validated_inbox: ValidatedInbox) -> dict:
    """Summarize closed inbox provenance metadata and whole imported counts.

    This pure function reads no Phase35 file and parses no CSV. Normal import
    builds the inbox only after reconciliation; reconstructing this receipt
    from stored new-inbox bytes is internal correspondence, not independent
    evidence that an earlier CSV import happened or that its producer is known.
    """
    inbox = read_typed_inbox(validated_inbox)
    receipt = {
        **common(RECEIPT_SCHEMA),
        "source_artifacts": [
            {"name": item["name"], "bytes": item["bytes"], "sha256": item["sha256"]}
            for item in inbox["source_artifacts"]
        ],
        "source_dataset_schema": inbox["source_dataset_schema"],
        "source_manifest_schema": SOURCE_MANIFEST_SCHEMA,
        "csv_headers": {
            "reference": list(CSV_HEADERS["reference"]),
            "projection": list(CSV_HEADERS["projection"]),
        },
        "csv_rows": {
            "reference_data_rows": len(inbox["reference_records"]),
            "projection_data_rows": len(inbox["projection_records"]),
        },
        "counts": dict(inbox["counts"]),
        "canonical_CSV_reconciliation": "matched_during_import",
        "dataset_CSV_relation": "typed_values_equal_during_import",
        "receipt_scope": RECEIPT_SCOPE,
        "limitations": list(LIMITATIONS),
    }
    return validate_receipt(receipt)


__all__ = ("build_import_receipt",)
