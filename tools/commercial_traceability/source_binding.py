"""Bind explicit Phase17 payload bytes and positions to a loaded assessment.

This checks the assessment-to-observation file/metadata relation only. It does
not establish that any Phase20 plan was executed, that a producer is authentic,
or that any target, permission, finding or human decision has been verified.
"""
from __future__ import annotations

from dataclasses import dataclass

from commercial_handoff.schema import CONTRACT as HANDOFF_CONTRACT
from commercial_intake import INTAKE_CONTRACT
from commercial_intake.source_mapping import build_source_mapping
from commercial_review.packet_builder import load_prepare_sources

from .assessment_reader import AssessmentBundle, validate_bundle
from .contracts import FileIdentity, InputError, file_identity, read_metadata


# The preserved Phase18 binding reader accepts the narrower 256 KiB mapping
# subset; do not advertise a wider map limit that that reader would then reject.
MAX_MAPPING_BYTES = 256 * 1024
MAX_HANDOFF_BYTES = 256 * 1024
MAX_INTAKE_MANIFEST_BYTES = 64 * 1024
INTAKE_MANIFEST_SCHEMA = "termivar-assessment-intake-manifest/v1"
SOURCE_BINDING_STATUS = "assessment_mapping_byte_and_metadata_consistent"


@dataclass(frozen=True, slots=True)
class ObservationLink:
    observation_id: str
    source_pointer: str
    native_fingerprint: str
    capability_id: str
    native_disposition: str
    subject_ref: str
    evidence_ref_count: int


@dataclass(frozen=True, slots=True)
class SourceBinding:
    observations: tuple[ObservationLink, ...]
    fingerprint_reuse_reported: bool
    source_binding_status: str
    source_files: tuple[FileIdentity, ...]
    source_assessment_sha256: str
    source_assessment_byte_length: int


def bind_source_mapping(bundle: AssessmentBundle, source_mapping_path: str,
                        handoff_input_path: str,
                        intake_manifest_path: str) -> SourceBinding:
    """Bind three actual files, not inferred paths or fabricated file identities.

    Phase18 already checks both actual payload entries, the fresh original
    handoff and all mapping positions. The complete mapping is additionally
    rebuilt from the selected native metadata and actual partial-manifest check
    and compared before its raw object is discarded. This also binds subject,
    category, claim basis, evidence arrays/counts and omitted-field declarations.
    """
    validate_bundle(bundle)
    mapping_file = read_metadata(source_mapping_path, MAX_MAPPING_BYTES)
    handoff_file = read_metadata(handoff_input_path, MAX_HANDOFF_BYTES)
    intake_file = read_metadata(intake_manifest_path, MAX_INTAKE_MANIFEST_BYTES)
    prepared = load_prepare_sources(handoff_input_path, source_mapping_path,
                                    intake_manifest_path)
    source_files = (
        file_identity("source_mapping", mapping_file, INTAKE_CONTRACT),
        file_identity("handoff_input", handoff_file, HANDOFF_CONTRACT),
        file_identity("intake_manifest", intake_file, INTAKE_MANIFEST_SCHEMA),
    )
    for selected, expected in zip(source_files, (
            prepared.phase17_inputs.source_mapping,
            prepared.phase17_inputs.handoff_input,
            prepared.phase17_inputs.intake_manifest)):
        if (selected.sha256 != expected.sha256
                or selected.byte_length != expected.byte_length):
            raise InputError("traceability_phase17_read_identity_changed")
    assessment = bundle.assessment
    if (prepared.source_assessment.sha256 != assessment.sha256
            or prepared.source_assessment.byte_length != assessment.byte_length):
        raise InputError("traceability_assessment_mapping_identity_mismatch")
    expected_mapping = build_source_mapping(assessment, bundle.manifest_check)
    if mapping_file.data != expected_mapping:
        raise InputError("traceability_source_mapping_metadata_mismatch")
    if len(prepared.observations) != len(assessment.items):
        raise InputError("traceability_source_observation_count_mismatch")
    observations = []
    for index, (native, mapped) in enumerate(zip(assessment.items,
                                                prepared.observations)):
        pointer = f"/items/{index}"
        if (native.index != index or mapped.source_json_pointer != pointer
                or mapped.source_assessment_sha256 != assessment.sha256
                or mapped.fingerprint != native.fingerprint
                or mapped.capability_id != native.capability_id
                or mapped.source_disposition != native.disposition):
            raise InputError("traceability_source_observation_link_mismatch")
        observations.append(ObservationLink(
            mapped.observation_id, pointer, native.fingerprint,
            native.capability_id, native.disposition, native.subject_reference,
            native.evidence_count,
        ))
    # Duplicate labels retain every source position. No fingerprint-keyed map,
    # merge, alternative pointer search or native importer acceptance is implied.
    reused = len({item.fingerprint for item in assessment.items}) != len(assessment.items)
    return SourceBinding(tuple(observations), reused, SOURCE_BINDING_STATUS,
                         source_files, assessment.sha256, assessment.byte_length)


__all__ = (
    "MAX_MAPPING_BYTES", "MAX_HANDOFF_BYTES", "MAX_INTAKE_MANIFEST_BYTES",
    "INTAKE_MANIFEST_SCHEMA", "SOURCE_BINDING_STATUS", "ObservationLink",
    "SourceBinding", "bind_source_mapping",
)
