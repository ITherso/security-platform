"""Exact, namespace-aware metadata overlap; never a coverage calculation."""
from __future__ import annotations

from dataclasses import dataclass
import re

from commercial_intake.assessment_reader import NativeItem, SUPPORTED_CAPABILITIES

from .contracts import InputError
from .plan_reader import CatalogCapability


MAPPING_STATUSES = frozenset((
    "declared_in_both", "plan_only", "assessment_only", "unmappable",
    "insufficient_evidence",
))
CATALOG_NAMESPACES = frozenset(("assessment_item", "graphql_catalog", "cli_surface"))


@dataclass(frozen=True, slots=True)
class CapabilityMapping:
    capability_id: str
    namespace: str
    status: str
    planned: bool
    assessment_reported: bool
    observation_pointers: tuple[str, ...]
    explanation: str


def map_capabilities(requested: tuple[str, ...],
                     catalog: tuple[CatalogCapability, ...],
                     items: tuple[NativeItem, ...]) -> tuple[CapabilityMapping, ...]:
    """Match only exact native assessment-item IDs in their own namespace.

    Every source position is retained. Several observations may have the same
    capability or fingerprint; grouping the capability never merges positions.
    Unobserved planned IDs describe a metadata difference, not a failed scan.
    """
    if (type(requested) is not tuple or len(requested) > 32
            or any(type(item) is not str or re.fullmatch(r"[a-z][a-z0-9._:@-]{0,127}", item) is None
                   for item in requested)
            or len(set(requested)) != len(requested)
            or type(catalog) is not tuple or len(catalog) != 11
            or type(items) is not tuple or len(items) > 256):
        raise InputError("traceability_invalid_mapping_input")
    entries = {}
    for entry in catalog:
        if (type(entry) is not CatalogCapability
                or entry.namespace not in CATALOG_NAMESPACES
                or entry.capability_id in entries):
            raise InputError("traceability_ambiguous_capability_namespace")
        entries[entry.capability_id] = entry
    reported: dict[str, list[str]] = {}
    for index, item in enumerate(items):
        if (type(item) is not NativeItem or type(item.index) is not int
                or item.index != index or item.capability_id not in SUPPORTED_CAPABILITIES):
            raise InputError("traceability_unsupported_assessment_capability")
        reported.setdefault(item.capability_id, []).append("/items/" + str(index))

    rows = []
    for capability in requested:
        entry = entries.get(capability)
        if entry is None:
            rows.append(CapabilityMapping(
                capability, "unknown", "insufficient_evidence", True, False, (),
                "Plan kimliği incelenen sınırlı katalogda bulunmuyor; namespace veya karşılık tahmin edilmez.",
            ))
        elif entry.namespace != "assessment_item":
            rows.append(CapabilityMapping(
                capability, entry.namespace, "unmappable", True, False, (),
                "GraphQL metadata family veya CLI surface kimliği native assessment item kimliğine dönüştürülmez.",
            ))
        elif entry.evidence_class == "insufficient_source_evidence":
            rows.append(CapabilityMapping(
                capability, "assessment_item", "insufficient_evidence", True,
                capability in reported, tuple(reported.get(capability, ())),
                "Kaynak sınıfı yapısal eşleme için yeterli kanıt sunmuyor; ada göre destek varsayılmaz.",
            ))
        elif capability in reported:
            rows.append(CapabilityMapping(
                capability, "assessment_item", "declared_in_both", True, True,
                tuple(reported[capability]),
                "Aynı assessment-item kimliği iki belgede de tanımlıdır; bu, planın yürütüldüğü veya kontrolün tamamlandığı anlamına gelmez.",
            ))
        else:
            rows.append(CapabilityMapping(
                capability, "assessment_item", "plan_only", True, False, (),
                "Kimlik planda vardır; bu assessment'ta aynı kimlikle observation raporlanmamıştır. Bu durum başarısız tarama veya temiz sistem sonucu değildir.",
            ))
    for capability, pointers in reported.items():
        entry = entries.get(capability)
        if capability in requested and entry is not None and entry.namespace == "assessment_item":
            continue
        rows.append(CapabilityMapping(
            capability, "assessment_item", "assessment_only", False, True,
            tuple(pointers),
            "Native assessment kimliği raporlanmıştır; planın assessment-item seçiminde aynı kimlik yer almaz. Kapsam dışı yürütme sonucu çıkarılmaz.",
        ))
    return tuple(rows)


def mapping_to_dict(row: CapabilityMapping) -> dict:
    if (type(row) is not CapabilityMapping or row.status not in MAPPING_STATUSES
            or row.namespace not in CATALOG_NAMESPACES | {"unknown"}
            or type(row.planned) is not bool or type(row.assessment_reported) is not bool
            or type(row.observation_pointers) is not tuple):
        raise InputError("traceability_invalid_capability_mapping")
    return {
        "capability_id": row.capability_id, "namespace": row.namespace,
        "status": row.status, "planned": row.planned,
        "assessment_reported": row.assessment_reported,
        "observation_pointers": list(row.observation_pointers),
        "explanation": row.explanation,
    }


__all__ = ("CapabilityMapping", "MAPPING_STATUSES", "map_capabilities", "mapping_to_dict")
