from copy import deepcopy
import json
from uuid import uuid4

from pydantic import ValidationError
import pytest

from security_platform.contracts import (MAX_SEQUENCE, MAX_SNAPSHOT_SEQUENCE, SnapshotEnvelope, canonical_json,
                                         snapshot_digest)
from security_platform.connectors.hostbased_firewall.snapshot_mapper import SnapshotMappingError, map_snapshot


def local_overview():
    # Exact projected fields from HostBasedFirewall src/security_ecosystem.py.
    return {"schema_version": 1, "products": [
        {"id": "hostbasedfirewall", "version": "1.4.4", "available": True, "status": "running",
         "management": "local", "engine_status": {"running": True, "stale": False, "mode": "enforce", "errors": []},
         "description": "DO NOT COPY local source text", "source_url": "https://github.com/kalixsmurf/HostBasedFirewall"},
        {"id": "termivar", "status": "experimental", "available": True,
         "management": "offline_report_import", "scanner_installed": None, "execution_available": False},
        {"id": "antivirus", "status": "planned", "available": False,
         "management": "unavailable", "execution_available": False}],
        "reports": [{"id": "a" * 64, "product_id": "termivar", "schema": "venom-rendered-assessment/v1",
            "profile": "web-review", "status": "complete", "imported_at": 1700000000.25,
            "subject_count": 1, "item_count": 4, "counts": {"informational": 4, "needs_review": 0, "confirmed": 0},
            "severity_counts": {"unassigned": 4, "info": 0, "low": 0, "medium": 0, "high": 0, "critical": 0},
            "producer_verification": "not_verified", "source_claim": "self_reported", "scope": "offline_report_summary"}],
        "limitations": ["Local overview only"]}


def snapshot_payload():
    return map_snapshot(local_overview(), sequence=1, message_id=str(uuid4())).model_dump(mode="json")


def test_mapper_is_pure_deterministic_and_exports_only_typed_summary():
    source = local_overview()
    original = deepcopy(source)
    identity = str(uuid4())
    first = map_snapshot(source, sequence=7, message_id=identity)
    second = map_snapshot(source, sequence=7, message_id=identity)
    assert first == second and source == original
    body = canonical_json(first)
    assert len(body) < 16384
    for forbidden in (b"DO NOT COPY", b"github.com", b"source_url", b"description", b"evidence", b"command"):
        assert forbidden not in body
    assert first.products[0].firewall_mode == "enforce"
    assert first.products[0].source_observed_at is None and first.products[0].installed is None
    assert first.products[0].version == "1.4.4"
    assert first.products[1].scanner_installed is None
    assert first.products[1].latest_report.imported_at == "2023-11-14T22:13:20.250000Z"
    assert first.products[1].latest_report.producer_verification == "not_verified"
    assert first.products[2].status == "planned" and first.products[2].availability == "unavailable"


def test_missing_values_remain_unknown_and_missing_products_are_not_invented():
    result = map_snapshot({"schema_version": 1, "products": [{"id": "hostbasedfirewall"}, {"id": "termivar"}]},
                          sequence=1, message_id=str(uuid4()))
    firewall, termivar = result.products
    assert firewall.status == "unknown" and firewall.firewall_mode == "unknown"
    assert firewall.reported_running is None and firewall.error_codes is None and firewall.catalog_available is None
    assert termivar.report_presence == "unknown" and termivar.latest_report is None
    assert termivar.scanner_installed is None and termivar.execution_available is None
    assert map_snapshot({"schema_version": 1}, sequence=1, message_id=str(uuid4())).products == []


def test_mapper_preserves_unassigned_and_does_not_refresh_import_time():
    source = local_overview()
    old = map_snapshot(source, sequence=1, message_id=str(uuid4())).products[1].latest_report
    new = map_snapshot(source, sequence=2, message_id=str(uuid4())).products[1].latest_report
    assert old == new and new.severity_counts.unassigned == 4
    source["reports"] = []
    assert map_snapshot(source, sequence=3, message_id=str(uuid4())).products[1].report_presence == "none"


def test_unknown_source_errors_are_not_copied_or_silently_treated_as_healthy():
    source = local_overview()
    source["products"][0]["engine_status"]["errors"] = ["SECRET_PATH unexpected exception", "config_error"]
    result = map_snapshot(source, sequence=1, message_id=str(uuid4()))
    assert result.products[0].error_codes == ["config_error", "unknown_error"]
    assert b"SECRET_PATH" not in canonical_json(result)


@pytest.mark.parametrize("changes", [
    # schema_version 2 is Snapshot V2 (tests/unit/test_snapshot_v2_contracts.py); 3 and non-integers stay closed.
    {"schema_version": True}, {"schema_version": 3}, {"schema_version": 0}, {"schema_version": 2.0},
    {"schema_version": "2"}, {"sequence": True}, {"sequence": 0}, {"sequence": MAX_SNAPSHOT_SEQUENCE + 1},
    {"sequence": MAX_SEQUENCE + 1}, {"sequence": 1.0}, {"sequence": "1"}, {"message_id": "not-a-uuid"},
    {"message_id": "A" * 36}, {"tenant_id": str(uuid4())}, {"device_id": str(uuid4())},
    {"metadata": {"secret": "MUST_NOT_ACCEPT"}}, {"source_observed_at": "2026-11-07T10:00:00"},
    {"source_observed_at": 1700000000}, {"source_observed_at": "2026-11-07T10:00:00+03:00"},
])
def test_envelope_strict_types_and_closed_fields(changes):
    with pytest.raises(ValidationError):
        SnapshotEnvelope.model_validate({**snapshot_payload(), **changes})


@pytest.mark.parametrize("product,changes", [
    (0, {"reported_running": 1}), (0, {"firewall_mode": "protected"}),
    (0, {"error_codes": ["raw secret error"]}), (0, {"error_codes": ["config_error", "config_error"]}),
    (0, {"version": "C:\\private\\secret"}), (0, {"producer_verification": "verified"}),
    (1, {"execution_available": True}), (1, {"target": "https://internal.example"}),
    (2, {"status": "running"}), (2, {"catalog_available": True}), (2, {"execution_available": True}),
    (2, {"version": "active-av-1"}),
])
def test_product_claims_and_closed_types_cannot_be_promoted(product, changes):
    payload = snapshot_payload()
    payload["products"][product].update(changes)
    with pytest.raises(ValidationError):
        SnapshotEnvelope.model_validate(payload)


@pytest.mark.parametrize("value", [True, -1, 1.5, float("nan"), float("inf"), "4"])
def test_report_counts_are_finite_nonnegative_strict_integers(value):
    payload = snapshot_payload()
    payload["products"][1]["latest_report"]["counts"]["informational"] = value
    with pytest.raises(ValidationError):
        SnapshotEnvelope.model_validate(payload)


def test_duplicate_and_unknown_products_fail_and_content_identity_is_canonical():
    payload = snapshot_payload()
    first = SnapshotEnvelope.model_validate(payload)
    reordered = json.loads(json.dumps(dict(reversed(list(payload.items())))))
    assert snapshot_digest(first) == snapshot_digest(SnapshotEnvelope.model_validate(reordered))
    payload["products"] = [payload["products"][0], payload["products"][0]]
    with pytest.raises(ValidationError):
        SnapshotEnvelope.model_validate(payload)
    payload["products"][0]["product_id"] = "made-up-product"
    with pytest.raises(ValidationError):
        SnapshotEnvelope.model_validate(payload)


@pytest.mark.parametrize("mutation", [
    lambda source: source["reports"][0].update(producer_verification="verified"),
    lambda source: source["reports"][0].update(imported_at=True),
    lambda source: source["reports"][0].update(imported_at=10**400),
    lambda source: source["products"][0]["engine_status"].update(running="true"),
    lambda source: source["products"][2].update(status="running"),
])
def test_invalid_local_exports_fail_with_fixed_error(mutation):
    source = local_overview()
    mutation(source)
    with pytest.raises(SnapshotMappingError, match="^local_export_not_supported$"):
        map_snapshot(source, sequence=1, message_id=str(uuid4()))
