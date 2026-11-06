"""Map an explicitly exported local ecosystem overview without loading its runtime.

The source contract is HostBasedFirewall src/security_ecosystem.py: catalogue
products plus validated numerical report summaries. Its catalogue omits the
engine observation timestamp, so this mapper leaves that timestamp unknown.
Termivar imported_at is the local import time, never report generation time.
"""
from datetime import datetime, timezone
import math

from pydantic import ValidationError

from security_platform.contracts import KNOWN_ERROR_CODES, SnapshotEnvelope


class SnapshotMappingError(ValueError):
    pass


def _require(condition):
    if not condition:
        raise SnapshotMappingError("local_export_not_supported")


def _boolean(value):
    _require(value is None or type(value) is bool)
    return value


def _import_time(value):
    _require(type(value) in (int, float) and math.isfinite(value) and value > 0)
    return datetime.fromtimestamp(value, timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _latest_summary(source):
    if "reports" not in source or source["reports"] is None:
        return "unknown", None
    reports = source["reports"]
    _require(isinstance(reports, list) and len(reports) <= 50)
    if not reports:
        return "none", None
    for report in reports:
        _require(isinstance(report, dict) and report.get("product_id") == "termivar")
        _import_time(report.get("imported_at"))
    latest = max(reports, key=lambda report: report["imported_at"])
    _require(latest.get("schema") == "venom-rendered-assessment/v1"
             and latest.get("profile") == "web-review" and latest.get("status") == "complete"
             and latest.get("source_claim") == "self_reported"
             and latest.get("producer_verification") == "not_verified"
             and latest.get("scope") == "offline_report_summary")
    return "present", {"digest": latest.get("id"), "report_schema": latest["schema"],
        "imported_at": _import_time(latest["imported_at"]), "subject_count": latest.get("subject_count"),
        "item_count": latest.get("item_count"), "counts": latest.get("counts"),
        "severity_counts": latest.get("severity_counts"), "source": "self_reported",
        "producer_verification": "not_verified", "scope": "offline_report_summary"}


def map_snapshot(source, *, sequence, message_id) -> SnapshotEnvelope:
    """Pure conversion: no imports of COM/WinDivert, no files, no HTTP, no clocks."""
    try:
        _require(isinstance(source, dict) and type(source.get("schema_version")) is int
                 and source["schema_version"] == 1)
        catalogue = source.get("products", [])
        _require(isinstance(catalogue, list) and len(catalogue) <= 3)
        products, seen = [], set()
        for product in catalogue:
            _require(isinstance(product, dict))
            identity = product.get("id")
            _require(isinstance(identity, str) and identity in {"hostbasedfirewall", "termivar", "antivirus"}
                     and identity not in seen)
            seen.add(identity)
            mapped = {"product_id": identity, "catalog_available": _boolean(product.get("available")),
                      "version": product.get("version"), "source": "self_reported",
                      "producer_verification": "not_verified", "source_observed_at": None}
            if identity == "hostbasedfirewall":
                health = product.get("engine_status")
                _require(health is None or isinstance(health, dict))
                health = health or {}
                errors = health.get("errors")
                _require(errors is None or isinstance(errors, list)
                         and len(errors) <= 32 and all(isinstance(code, str) for code in errors))
                mapped.update(status=product.get("status", "unknown"), installed=None,
                    reported_running=_boolean(health.get("running")), reported_stale=_boolean(health.get("stale")),
                    firewall_mode=health.get("mode") or "unknown",
                    error_codes=(sorted({code if code in KNOWN_ERROR_CODES else "unknown_error" for code in errors})
                                 if errors is not None else None))
            elif identity == "termivar":
                presence, latest = _latest_summary(source)
                mapped.update(status=product.get("status", "unknown"),
                    scanner_installed=_boolean(product.get("scanner_installed")),
                    execution_available=_boolean(product.get("execution_available")),
                    report_presence=presence, latest_report=latest)
            else:
                mapped.update(status=product.get("status", "unknown"),
                    availability=product.get("management", "unknown"),
                    execution_available=_boolean(product.get("execution_available")))
            products.append(mapped)
        return SnapshotEnvelope.model_validate({"schema_version": 1, "message_id": message_id,
            "sequence": sequence, "source_observed_at": None, "products": products})
    except SnapshotMappingError:
        raise
    except (ValidationError, ValueError, TypeError, KeyError, OverflowError, OSError) as exc:
        raise SnapshotMappingError("local_export_not_supported") from exc
