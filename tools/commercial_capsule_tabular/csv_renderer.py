"""Two fixed CSV tables with reversible, formula-inert typed data cells.

The authoritative values are the closed dataset JSON values. Every data cell
is an ASCII ``j:`` tag followed by canonical compact JSON, never a replacement
or normalization of the source value. Headers are fixed plain column names.
"""
from __future__ import annotations

import csv
import io
import json

from tabular_contracts import (
    MAX_CELL_BYTES, MAX_CSV_BYTES, MAX_ROW_BYTES, PROJECTION_HEADERS, REF_HEADERS,
    InputError, json_bytes, parse_json, validate_dataset,
)


def _cell_value(value: object) -> None:
    if value is not None and type(value) not in (str, int, list):
        raise InputError("tabular_CSV_cell_type_rejected")
    if type(value) is list and any(type(item) is not str for item in value):
        raise InputError("tabular_CSV_collection_type_rejected")
    # Reuse the owning JSON tree, string, safe-integer and Unicode boundaries.
    # This also rejects negative integers, floats and non-JSON Python objects.
    json_bytes(value)


def encode_cell(value: object) -> str:
    """Encode a bounded source value without stripping or modifying it."""
    _cell_value(value)
    try:
        payload = json.dumps(value, ensure_ascii=True, separators=(",", ":"),
                             sort_keys=True, allow_nan=False)
        cell = "j:" + payload
        raw = cell.encode("ascii", "strict")
    except (UnicodeError, ValueError, TypeError, OverflowError):
        raise InputError("tabular_CSV_cell_encoding_rejected") from None
    if not 2 < len(raw) <= MAX_CELL_BYTES:
        raise InputError("tabular_CSV_cell_byte_limit")
    return cell


def decode_cell(cell: str) -> object:
    """Recover a typed value only from the exact canonical tagged encoding."""
    if type(cell) is not str or not cell.startswith("j:"):
        raise InputError("tabular_CSV_cell_tag_rejected")
    try:
        raw = cell.encode("ascii", "strict")
    except UnicodeError:
        raise InputError("tabular_CSV_cell_ASCII_required") from None
    if (not 2 < len(raw) <= MAX_CELL_BYTES
            or any(byte < 32 or byte == 127 for byte in raw)):
        raise InputError("tabular_CSV_cell_size_or_control_rejected")
    value = parse_json(raw[2:], maximum=MAX_CELL_BYTES - 2)
    _cell_value(value)
    if encode_cell(value) != cell:
        raise InputError("tabular_CSV_noncanonical_cell_rejected")
    return value


def _row_bytes(cells: list[str] | tuple[str, ...]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, delimiter=",", quotechar='"', doublequote=True,
                        escapechar=None, quoting=csv.QUOTE_ALL, lineterminator="\n")
    writer.writerow(cells)
    raw = stream.getvalue().encode("utf-8", "strict")
    if len(raw) > MAX_ROW_BYTES:
        raise InputError("tabular_CSV_row_byte_limit")
    return raw


def _render_table(headers: tuple, records: list[dict]) -> bytes:
    output = bytearray(_row_bytes(headers))
    for record in records:
        raw_row = _row_bytes([encode_cell(record[key]) for key in headers])
        if len(output) + len(raw_row) > MAX_CSV_BYTES:
            raise InputError("tabular_CSV_file_byte_limit")
        output.extend(raw_row)
    if not 0 < len(output) <= MAX_CSV_BYTES:
        raise InputError("tabular_CSV_file_byte_limit")
    return bytes(output)


def render_csvs(dataset: dict) -> tuple[bytes, bytes]:
    """Render the fixed reference and projection tables from validated JSON."""
    dataset = validate_dataset(dataset)
    return (_render_table(REF_HEADERS, dataset["reference_records"]),
            _render_table(PROJECTION_HEADERS, dataset["projection_records"]))


def _read_table(raw: bytes, headers: tuple, expected_data_rows: int) -> list[dict]:
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_CSV_BYTES:
        raise InputError("tabular_CSV_input_byte_limit")
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeError:
        raise InputError("tabular_CSV_UTF8_required") from None
    # Canonical ASCII JSON escapes keep source Unicode/control characters
    # inside the payload. The physical CSV itself contains only ASCII and LF.
    if (text.startswith("\ufeff") or not text.endswith("\n")
            or any(ord(char) > 127 or ord(char) == 127
                   or (ord(char) < 32 and char != "\n") for char in text)):
        raise InputError("tabular_CSV_physical_text_policy_rejected")
    physical_rows = raw.splitlines(keepends=True)
    if (len(physical_rows) != expected_data_rows + 1
            or any(len(row) > MAX_ROW_BYTES for row in physical_rows)):
        raise InputError("tabular_CSV_physical_row_count_or_limit")
    try:
        reader = csv.reader(io.StringIO(text, newline=""), delimiter=",", quotechar='"',
                            doublequote=True, escapechar=None, quoting=csv.QUOTE_ALL,
                            strict=True)
        rows = list(reader)
    except csv.Error:
        raise InputError("tabular_CSV_syntax_rejected") from None
    if (len(rows) != expected_data_rows + 1 or not rows
            or rows[0] != list(headers)
            or any(len(row) != len(headers) for row in rows[1:])):
        raise InputError("tabular_CSV_header_column_or_row_mismatch")
    return [{key: decode_cell(cell) for key, cell in zip(headers, row)}
            for row in rows[1:]]


def inspect_csvs(dataset: dict, refs_raw: bytes, projs_raw: bytes) -> dict:
    """Validate decoded types/values and exact dataset-derived CSV bytes.

    This checks the defined wire encoding, not import behavior in any actual
    spreadsheet application and not adversarial formula-injection acceptance.
    """
    dataset = validate_dataset(dataset)
    references = _read_table(refs_raw, REF_HEADERS, len(dataset["reference_records"]))
    projections = _read_table(projs_raw, PROJECTION_HEADERS, len(dataset["projection_records"]))
    if (json_bytes(references) != json_bytes(dataset["reference_records"])
            or json_bytes(projections) != json_bytes(dataset["projection_records"])):
        raise InputError("tabular_CSV_decoded_dataset_mismatch")
    expected_references, expected_projections = render_csvs(dataset)
    # Exact comparison enforces quoting of every field, fixed headers, LF,
    # canonical cell spelling, row order and absence of surplus/hidden rows.
    if refs_raw != expected_references or projs_raw != expected_projections:
        raise InputError("tabular_CSV_rendered_byte_mismatch")
    return {"reference_data_rows": len(references), "projection_data_rows": len(projections)}


__all__ = ("encode_cell", "decode_cell", "render_csvs", "inspect_csvs")
