"""Bind three explicit Phase17 files and prepare metadata for human review.

No native assessment, manifest entry, URL or referenced path is followed. A
coherently edited input set can still bind; this is not source authentication.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from commercial_handoff.input_loader import LoadedInput, load_input
from commercial_handoff.schema import InputError
from commercial_intake import ADAPTER_VERSION, INTAKE_CONTRACT
from commercial_intake.assessment_reader import SUPPORTED_CAPABILITIES, SUPPORTED_CATEGORIES
from commercial_intake.handoff_adapter import (
    _CASE_ID, _DELIVERY_CONSTRAINTS, _EVIDENCE_LIMITATIONS, _PROVENANCE_NOTE,
    _SCOPE_SUMMARY, _SOURCE_ID,
)

from .review_contracts import (
    DEMO_LABEL, DELIVERY_BLOCKERS, MAX_REVIEW_BYTES, PACKET_CONTRACT,
    REVIEW_REQUIREMENTS, SOURCE_VERIFICATION, FileIdentity, ManifestLimitation,
    PacketObservation, Phase17Inputs, ReviewPacket, SourceAssessment,
    array, digest, enum_value, fingerprint, handoff_to_dict, identifier, integer,
    json_bytes, literal, load_review_json, manifest_limitation, object_fields,
    observation_key, packet_to_dict, source_assessment, validate_packet,
)


_MAPPING_FP_LIMIT = (
    "Reported fingerprints are not source authentication. Repeated labels remain separate by exact "
    "source byte SHA256 and JSON pointer; native importer uniqueness acceptance is not established."
)
_INTAKE_FP_LIMIT = (
    "Repeated reported fingerprints remain separate by source byte SHA256 and JSON pointer; "
    "native importer uniqueness acceptance is not established."
)
_OMITTED_CLASSES = (
    "item_title", "item_redacted_summary", "item_remediation", "item_cwe",
    "item_severity", "item_confidence_ppm", "item_verifier_linkage",
)
_SOURCE_LIMIT = (
    "Only the explicitly selected assessment and optional manifest were read. "
    "Hashes identify their actual bytes, not a producer, authorized scope, "
    "finding accuracy or human approval."
)
_PARTIAL_LIMIT = (
    "A matching manifest establishes only the selected JSON-entry byte length, "
    "SHA256 and summary relation. No HTML payload was opened, no full bundle "
    "was verified and no native verifier or signature check was run."
)
_COMPLETION_MARKER = (
    "intake-manifest.json is published last. Its presence alone is not "
    "authentication; check the declared payload bytes before treating the set as complete."
)


@dataclass(frozen=True, slots=True)
class PreparedSources:
    handoff: LoadedInput
    phase17_inputs: Phase17Inputs
    source_assessment: SourceAssessment
    manifest_limitation: ManifestLimitation
    observations: tuple[PacketObservation, ...]


def _identity(loaded) -> FileIdentity:
    return FileIdentity(digest(loaded.sha256), integer(loaded.byte_length, 1, MAX_REVIEW_BYTES))


def _flags(row: dict) -> None:
    literal(row["demo_only"], True)
    for key in ("human_review_verified", "producer_verified", "release_authorized"):
        literal(row[key], False)


def _fixed_array(value: object, expected: tuple[str, ...]) -> None:
    if tuple(array(value, len(expected))) != expected:
        raise InputError("review_phase17_constant_changed")


def _opaque_reference(value: object, kind: str) -> int:
    if type(value) is not str:
        raise InputError("review_invalid_opaque_reference")
    match = re.fullmatch(re.escape(kind) + r"-([0-9]{4}|[1-9][0-9]{4,9})", value)
    if match is None or int(match.group(1)) > 4294967295:
        raise InputError("review_invalid_opaque_reference")
    return int(match.group(1))


def _evidence_metadata(row: dict) -> None:
    references = []
    counts = []
    for key in ("evidence_references", "control_evidence_references", "candidate_evidence_references"):
        values = array(row[key], 256)
        for value in values:
            _opaque_reference(value, "evidence")
        references.extend(values)
        counts.append(len(values))
    count = integer(row["evidence_count"], 0, 256)
    if len(set(references)) != len(references) or len(references) != count:
        raise InputError("review_invalid_evidence_metadata")
    direct, control, candidate = counts
    basis = enum_value(row["claim_basis"], ("observation", "differential", "verifier_transition"))
    disposition = enum_value(row["disposition"], ("informational", "needs_review", "confirmed"))
    if basis == "observation":
        valid = disposition == "informational" and direct > 0 and control == 0 and candidate == 0
    elif basis == "differential":
        valid = (disposition == "needs_review" and
            ((direct == 1 and control == 0 and candidate == 0)
             or (direct == 0 and control > 0 and candidate > 0)))
    else:
        valid = disposition == "confirmed" and direct > 0 and control == 0 and candidate == 0
    if not valid:
        raise InputError("review_invalid_evidence_metadata")
    # Phase17 intentionally omitted verifier linkage. These reduced count/label
    # checks cannot establish native verifier validity or independent findings.


def _mapping(value: object):
    row = object_fields(value, ("schema_version", "adapter_version", "mapping_status",
        "source_assessment", "manifest_check", "source_observation_count", "mapped_observation_count",
        "automatic_merge_performed", "fingerprint_reuse_detected", "native_import_validation_performed",
        "fingerprint_limit", "observations", "omitted_field_classes", "demo_only",
        "human_review_verified", "producer_verified", "release_authorized"))
    literal(row["schema_version"], INTAKE_CONTRACT)
    literal(row["adapter_version"], ADAPTER_VERSION)
    literal(row["mapping_status"], "mapped_metadata_only")
    literal(row["automatic_merge_performed"], False)
    literal(row["native_import_validation_performed"], False)
    literal(row["fingerprint_limit"], _MAPPING_FP_LIMIT)
    _fixed_array(row["omitted_field_classes"], _OMITTED_CLASSES)
    _flags(row)
    source = source_assessment(row["source_assessment"])
    limitation = manifest_limitation(row["manifest_check"])
    observations = []
    for index, item in enumerate(array(row["observations"], 256)):
        item = object_fields(item, ("handoff_observation_id", "source_assessment_sha256",
            "source_json_pointer", "fingerprint", "capability_id", "disposition", "claim_basis",
            "category", "subject_reference", "evidence_count", "evidence_references",
            "control_evidence_references", "candidate_evidence_references", "mapping_status"))
        literal(item["mapping_status"], "mapped_metadata_only")
        enum_value(item["category"], SUPPORTED_CATEGORIES)
        if _opaque_reference(item["subject_reference"], "subject") >= source.subject_count:
            raise InputError("review_subject_reference_mismatch")
        _evidence_metadata(item)
        pointer = literal(item["source_json_pointer"], f"/items/{index}")
        literal(item["source_assessment_sha256"], source.sha256)
        observations.append(PacketObservation(
            literal(identifier(item["handoff_observation_id"]), f"OBS-{index + 1:02d}"),
            observation_key(source.sha256, pointer), source.sha256, pointer,
            fingerprint(item["fingerprint"]), enum_value(item["capability_id"], SUPPORTED_CAPABILITIES),
            enum_value(item["disposition"], ("informational", "needs_review", "confirmed")),
            "unreviewed", "unknown", "pending_decision",
        ))
    count = len(observations)
    for key in ("source_observation_count", "mapped_observation_count"):
        literal(integer(row[key], 0, 256), count)
    literal(source.item_count, count)
    reused = len({item.fingerprint for item in observations}) != count
    literal(row["fingerprint_reuse_detected"], reused)
    return source, limitation, tuple(observations), reused


def _intake(value: object, identities: Phase17Inputs, source: SourceAssessment,
            limitation: ManifestLimitation, reused: bool) -> None:
    row = object_fields(value, ("schema_version", "adapter_contract", "adapter_version", "assessment",
        "optional_manifest", "source_count", "transferred_count", "rejected_or_unsupported_summary",
        "automatic_merge_performed", "fingerprint_reuse_detected", "native_import_validation_performed",
        "fingerprint_limit", "output_files", "files", "manifest_self_excluded", "demo_only",
        "human_review_verified", "producer_verified", "release_authorized", "delivery_blockers",
        "source_provenance_limitation", "partial_manifest_limitation", "completion_marker"))
    literal(row["schema_version"], "termivar-assessment-intake-manifest/v1")
    literal(row["adapter_contract"], INTAKE_CONTRACT)
    literal(row["adapter_version"], ADAPTER_VERSION)
    assessment = object_fields(row["assessment"], ("schema", "sha256", "byte_length"))
    literal(assessment["schema"], source.schema)
    literal(digest(assessment["sha256"]), source.sha256)
    literal(integer(assessment["byte_length"], 1, 1024 * 1024), source.byte_length)
    if manifest_limitation(row["optional_manifest"]) != limitation:
        raise InputError("review_manifest_limitation_mismatch")
    for key in ("source_count", "transferred_count"):
        literal(integer(row[key], 0, 256), source.item_count)
    array(row["rejected_or_unsupported_summary"], 0)
    literal(row["automatic_merge_performed"], False)
    literal(row["fingerprint_reuse_detected"], reused)
    literal(row["native_import_validation_performed"], False)
    literal(row["fingerprint_limit"], _INTAKE_FP_LIMIT)
    _fixed_array(row["output_files"], ("handoff-input.json", "source-mapping.json", "intake-manifest.json"))
    expected = (("handoff-input.json", identities.handoff_input),
                ("source-mapping.json", identities.source_mapping))
    entries = array(row["files"], 2, 2)
    for entry, (name, identity) in zip(entries, expected):
        entry = object_fields(entry, ("name", "bytes", "sha256"))
        literal(entry["name"], name)
        literal(integer(entry["bytes"], 1, MAX_REVIEW_BYTES), identity.byte_length)
        literal(digest(entry["sha256"]), identity.sha256)
    literal(row["manifest_self_excluded"], True)
    _flags(row)
    _fixed_array(row["delivery_blockers"], DELIVERY_BLOCKERS)
    literal(row["source_provenance_limitation"], _SOURCE_LIMIT)
    literal(row["partial_manifest_limitation"], _PARTIAL_LIMIT)
    literal(row["completion_marker"], _COMPLETION_MARKER)


def validate_original_handoff(packet: ReviewPacket, original: LoadedInput) -> None:
    """Bind a loaded original to packet metadata without rewriting its fields."""
    packet_to_dict(packet)
    if type(original) is not LoadedInput:
        raise InputError("review_invalid_original_input")
    if _identity(original) != packet.phase17_inputs.handoff_input:
        raise InputError("review_original_byte_identity_mismatch")
    document = original.document
    handoff_to_dict(document)
    literal(document.case_id, _CASE_ID)
    literal(document.mode, "demo")
    literal(document.scope_summary, _SCOPE_SUMMARY)
    literal(document.authorization_status, "not_provided")
    if document.delivery_constraints != _DELIVERY_CONSTRAINTS or document.review_decisions:
        raise InputError("review_original_not_fresh_phase17")
    if len(document.source_artifacts) != 1:
        raise InputError("review_single_source_required")
    source = document.source_artifacts[0]
    expected = packet.source_assessment
    literal(source.artifact_id, _SOURCE_ID)
    literal(source.contract, expected.schema)
    literal(source.sha256, expected.sha256)
    literal(source.byte_length, expected.byte_length)
    literal(source.completion_status, expected.status)
    literal(source.provenance_note, _PROVENANCE_NOTE)
    if len(document.observations) != len(packet.observations):
        raise InputError("review_original_observation_count_mismatch")
    for original_item, prepared in zip(document.observations, packet.observations):
        for value, expected_value in (
            (original_item.observation_id, prepared.observation_id),
            (original_item.source_artifact, _SOURCE_ID),
            (original_item.observation_ref, prepared.fingerprint),
            (original_item.source_json_pointer, prepared.source_json_pointer),
            (original_item.capability_id, prepared.capability_id),
            (original_item.source_disposition, prepared.source_disposition),
            (original_item.review_status, "unreviewed"), (original_item.scope_status, "unknown"),
            (original_item.client_inclusion, "pending_decision"), (original_item.safe_summary, None),
            (original_item.decision_ref, None), (original_item.evidence_limitations, _EVIDENCE_LIMITATIONS),
        ):
            literal(value, expected_value)


def load_prepare_sources(handoff_path: str, mapping_path: str, intake_path: str) -> PreparedSources:
    handoff = load_input(handoff_path)
    mapping = load_review_json(mapping_path)
    intake = load_review_json(intake_path)
    identities = Phase17Inputs(_identity(handoff), _identity(mapping), _identity(intake))
    source, limitation, observations, reused = _mapping(mapping.data)
    _intake(intake.data, identities, source, limitation, reused)
    prepared = PreparedSources(handoff, identities, source, limitation, observations)
    # The same closed packet validation and original binding are applied before
    # any prepare output can be produced; raw mapping/intake objects are dropped.
    build_packet(prepared)
    return prepared


def build_packet(sources: PreparedSources) -> ReviewPacket:
    if type(sources) is not PreparedSources:
        raise InputError("review_invalid_prepared_sources")
    packet = ReviewPacket(
        PACKET_CONTRACT, "demo", DEMO_LABEL, sources.phase17_inputs, sources.source_assessment,
        sources.manifest_limitation, sources.observations, REVIEW_REQUIREMENTS, DELIVERY_BLOCKERS,
        SOURCE_VERIFICATION, True, False, False, False, False,
    )
    packet = validate_packet(packet_to_dict(packet))
    validate_original_handoff(packet, sources.handoff)
    return packet


def render_packet(packet: ReviewPacket) -> bytes:
    return json_bytes(packet_to_dict(packet))


def render_worksheet(packet: ReviewPacket) -> bytes:
    packet = validate_packet(packet_to_dict(packet))
    lines = ["# Analyst review worksheet", "", "**" + DEMO_LABEL + "**", "",
        "Bu belge karar vermez. Tüm kayıtlar kaynak metadata'sıdır; gerçek reviewer, tarih veya onay yoktur.",
        "Native assessment bu aşamada okunmadı. Yalnız üç açık Phase17 dosyasının byte ve kayıt bağları kontrol edildi.",
        "", "## Bağlanan dosyalar", ""]
    for role in ("handoff_input", "source_mapping", "intake_manifest"):
        identity = getattr(packet.phase17_inputs, role)
        lines.append(f"- {role}: `{identity.sha256}` / {identity.byte_length} byte")
    lines.extend(["", "## Kaynak ve açık sınırlar", "",
        f"- Beyan edilen assessment SHA256: `{packet.source_assessment.sha256}`",
        f"- Observation sayısı: {len(packet.observations)}",
        f"- Önceki manifest ilişkisi: `{packet.manifest_limitation.status}`; burada native bundle/producer doğrulanmadı.",
        "- demo_only=true; human_review_verified=false; producer_verified=false; release_authorized=false.",
        "", "Eksik kanıt, kapsam, güvenli müşteri anlatımı ve paylaşım kararını yalnız gerçek inceleme sonrası ayrı overlay'e yazın.",
        "Bu worksheet doldurulması gerçek inceleme, yetki veya müşteri teslim onayı değildir."])
    for item in packet.observations:
        lines.extend(["", f"## {item.observation_id}", "",
            f"- Observation key: `{item.observation_key}`",
            f"- Native fingerprint — ayrı kaynak etiketi: `{item.fingerprint}`",
            f"- Capability: `{item.capability_id}`",
            f"- Kaynak disposition: `{item.source_disposition}`",
            "- review_status=unreviewed; scope_status=unknown; client_inclusion=pending_decision.",
            "", "| İnceleme konusu | Mevcut kayıt |", "| --- | --- |",
            "| Kapsam dayanağı | not_provided |", "| Gerçekte erişilen/incelenen kanıt | not_provided |",
            "| Eksik kanıt ve takip | not_provided |", "| Gerekçeli review/inclusion kararı | not_provided |",
            "| Güvenli müşteri özeti | not_provided |", "| Gerçek reviewer / reviewed_at | not_provided / not_provided |"])
    lines.extend(["", "## Açık teslim engelleri", ""])
    lines.extend("- `" + code + "`" for code in packet.delivery_blockers)
    lines.extend(["", "Serbest notları veya ham kanıtı bu kaynak modeline eklemeyin; otomatik redaksiyon ve sır taraması yapılmaz.", ""])
    raw = "\n".join(lines).encode("utf-8", "strict")
    if not 0 < len(raw) <= MAX_REVIEW_BYTES:
        raise InputError("review_worksheet_size_limit")
    return raw
