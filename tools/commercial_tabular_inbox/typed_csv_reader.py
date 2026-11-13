"""Pure canonical typed CSV import using the protected Phase35 cell codec."""
from __future__ import annotations

from copy import deepcopy
import csv
import io

from csv_renderer import decode_cell, render_csvs
from tabular_contracts import (
    MAX_CSV_BYTES, MAX_ROW_BYTES, PROJECTION_HEADERS, REF_HEADERS,
    InputError, json_bytes, validate_dataset, validate_projection,
    validate_reference_record,
)


def _parse_table(raw: bytes, headers: tuple, maximum_records: int,
                 *, projections: bool) -> list[dict]:
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_CSV_BYTES:
        raise InputError("typed_inbox_CSV_byte_limit")
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeError:
        raise InputError("typed_inbox_CSV_UTF8_required") from None
    if (text.startswith("\ufeff") or not text.endswith("\n")
            or any(ord(char) > 127 or ord(char) == 127
                   or (ord(char) < 32 and char != "\n") for char in text)):
        raise InputError("typed_inbox_CSV_physical_encoding_rejected")
    physical_rows = raw.splitlines(keepends=True)
    if (not 1 <= len(physical_rows) <= maximum_records + 1
            or any(len(row) > MAX_ROW_BYTES for row in physical_rows)):
        raise InputError("typed_inbox_CSV_physical_row_limit")

    records, identities = [], set()
    try:
        reader = csv.reader(io.StringIO(text, newline=""), delimiter=",", quotechar='"',
                            doublequote=True, escapechar=None, quoting=csv.QUOTE_ALL,
                            strict=True)
        header = next(reader)
        if len(set(header)) != len(header) or header != list(headers):
            raise InputError("typed_inbox_CSV_header_rejected")
        for cells in reader:
            if len(records) >= maximum_records or len(cells) != len(headers):
                raise InputError("typed_inbox_CSV_column_or_record_limit")
            # Values originate in actual CSV cells, never a dataset record.
            # The owning decoder strictly parses tagged JSON, rejects bool as
            # int, and requires the exact canonical Phase35 cell spelling.
            record = {key: decode_cell(cell) for key, cell in zip(headers, cells)}
            if projections:
                record = validate_projection(record, record["reference_id"])
                identity = record["candidate_id"]
            else:
                record = validate_reference_record(record)
                identity = record["reference_id"]
            if identity in identities:
                raise InputError("typed_inbox_duplicate_CSV_record")
            identities.add(identity)
            records.append(record)
    except (csv.Error, StopIteration):
        raise InputError("typed_inbox_CSV_syntax_rejected") from None
    if len(physical_rows) != len(records) + 1:
        raise InputError("typed_inbox_CSV_physical_logical_rows_differ")
    return records


def parse_typed_csvs(dataset: dict, refs_raw: bytes,
                     projs_raw: bytes) -> tuple[list[dict], list[dict]]:
    """Decode real CSV rows, reconcile typed values, then require exact bytes."""
    dataset = validate_dataset(dataset)
    references = _parse_table(refs_raw, REF_HEADERS, 8, projections=False)
    projections = _parse_table(projs_raw, PROJECTION_HEADERS, 64, projections=True)
    if (json_bytes(references) != json_bytes(dataset["reference_records"])
            or json_bytes(projections) != json_bytes(dataset["projection_records"])):
        raise InputError("typed_inbox_CSV_dataset_typed_values_mismatch")

    # Metadata is used only to reconcile the owning dataset contract. Both
    # record collections are replaced with the independently decoded CSV rows.
    reconstructed = deepcopy(dataset)
    reconstructed["reference_records"] = references
    reconstructed["projection_records"] = projections
    reconstructed = validate_dataset(reconstructed)
    expected_references, expected_projections = render_csvs(reconstructed)
    if refs_raw != expected_references or projs_raw != expected_projections:
        raise InputError("typed_inbox_noncanonical_CSV_bytes")
    return deepcopy(references), deepcopy(projections)


__all__ = ("parse_typed_csvs",)
