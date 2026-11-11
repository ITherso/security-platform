"""Read the unchanged narrow native assessment and its explicit JSON manifest.

Only the base complete web-review subset accepted by the preserved Phase17
reader is supported. URLs, opaque references and manifest names are not opened.
Byte/summary consistency never authenticates a producer, run or authorized scope.
"""
from __future__ import annotations

from dataclasses import dataclass

from commercial_intake.assessment_reader import (
    AssessmentSource, MAX_ASSESSMENT_BYTES, read_assessment,
)
from commercial_intake.provenance import (
    MAX_MANIFEST_BYTES, ManifestCheck, read_manifest,
)

from .contracts import FileIdentity, InputError, file_identity, read_metadata


ASSESSMENT_SCHEMA = "venom-rendered-assessment/v1"
ASSESSMENT_MANIFEST_SCHEMA = "termivar-report-bundle/v1"


@dataclass(frozen=True, slots=True)
class AssessmentBundle:
    assessment: AssessmentSource
    manifest_check: ManifestCheck
    source_files: tuple[FileIdentity, ...]


def validate_bundle(bundle: AssessmentBundle) -> None:
    """Check this module's closed identity seams without reopening any source."""
    if (type(bundle) is not AssessmentBundle
            or type(bundle.assessment) is not AssessmentSource
            or type(bundle.manifest_check) is not ManifestCheck
            or type(bundle.source_files) is not tuple
            or len(bundle.source_files) != 2
            or any(type(item) is not FileIdentity for item in bundle.source_files)):
        raise InputError("traceability_invalid_assessment_bundle")
    source = bundle.assessment
    manifest = bundle.manifest_check
    selected, selected_manifest = bundle.source_files
    if (source.schema != ASSESSMENT_SCHEMA
            or source.source_schema != "venom-assessment-run/v1"
            or source.run_schema != "venom-run/v1"
            or source.profile_schema != "venom.scan-profile/v1"
            or source.profile != "web-review" or source.status != "complete"
            or selected.role != "assessment"
            or selected.schema_version != ASSESSMENT_SCHEMA
            or selected.sha256 != source.sha256
            or selected.byte_length != source.byte_length
            or selected_manifest.role != "assessment_manifest"
            or selected_manifest.schema_version != ASSESSMENT_MANIFEST_SCHEMA
            or manifest.provided is not True
            or manifest.status != "partial_json_entry_match"
            or manifest.json_entry_matches is not True
            or manifest.summary_matches is not True
            or selected_manifest.sha256 != manifest.sha256
            or selected_manifest.byte_length != manifest.byte_length
            or manifest.html_payload_read is not False
            or manifest.full_bundle_verified is not False
            or manifest.producer_verified is not False):
        raise InputError("traceability_invalid_assessment_bundle")


def load_assessment_bundle(assessment_path: str,
                           assessment_manifest_path: str) -> AssessmentBundle:
    """Read two explicit local files and bind only the JSON entry and summary.

    The preserved parser validates the actual native wire subset. The bounded
    metadata rereads are compared to its exact identities, so a changed reread
    cannot silently become the successful reader result. Hostile filesystem
    races and permissions have not been accepted by runtime security tests.
    """
    assessment = read_assessment(assessment_path)
    manifest = read_manifest(assessment_manifest_path, assessment)
    selected = read_metadata(assessment_path, MAX_ASSESSMENT_BYTES)
    selected_manifest = read_metadata(assessment_manifest_path, MAX_MANIFEST_BYTES)
    if (selected.sha256 != assessment.sha256
            or selected.byte_length != assessment.byte_length
            or selected_manifest.sha256 != manifest.sha256
            or selected_manifest.byte_length != manifest.byte_length):
        raise InputError("traceability_assessment_read_identity_changed")
    bundle = AssessmentBundle(assessment, manifest, (
        file_identity("assessment", selected, ASSESSMENT_SCHEMA),
        file_identity("assessment_manifest", selected_manifest,
                      ASSESSMENT_MANIFEST_SCHEMA),
    ))
    validate_bundle(bundle)
    return bundle


__all__ = (
    "ASSESSMENT_SCHEMA", "ASSESSMENT_MANIFEST_SCHEMA", "AssessmentBundle",
    "validate_bundle", "load_assessment_bundle",
)
