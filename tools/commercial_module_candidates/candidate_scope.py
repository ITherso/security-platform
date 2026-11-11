"""Validate explicit operator scope before any candidate path is queried."""
from __future__ import annotations

import copy

from .candidate_contracts import (
    SCOPE_SCHEMA, REVIEW_FIELDS, GROUP_SCHEMAS, MAX_METADATA_BYTES,
    closed, fixed, validate_reference, validate_group, validate_review_scope, unique, fail,
)


def validate_scope(value: object) -> dict:
    scope = closed(value, ("schema_version", "mode", "source_reference", *GROUP_SCHEMAS, *REVIEW_FIELDS), "scope_fields")
    fixed(scope["schema_version"], SCOPE_SCHEMA, "scope_schema")
    fixed(scope["mode"], "demo", "scope_mode")
    reference = validate_reference(scope["source_reference"], full=False)
    paths, total = [], 0
    for name in GROUP_SCHEMAS:
        group = validate_group(scope[name], name, paths=True)
        paths.extend(r["path"].casefold() for r in group.values())
        total += sum(r["bytes"] for r in group.values())
    unique(paths, "duplicate_artifact_paths")
    if total > MAX_METADATA_BYTES:
        fail("declared_metadata_budget")
    validate_review_scope({key: scope[key] for key in REVIEW_FIELDS}, reference["source_commits"])
    return copy.deepcopy(scope)


def review_from_scope(scope: dict, context: dict) -> dict:
    return validate_review_scope({key: scope[key] for key in REVIEW_FIELDS}, scope["source_reference"]["source_commits"], context)
