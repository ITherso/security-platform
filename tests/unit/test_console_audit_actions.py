"""The operator console accepts exactly the audit actions the API writes.

The console checks every audit item against closed lists; one unknown action
makes it reject the whole audit page (ClientError "malformed"). This checkout
has no TypeScript toolchain, so the sources are read as text.
"""
import re
from pathlib import Path

import pytest

from security_platform.services import audit


ROOT = Path(__file__).resolve().parents[2]
CONSOLE = ROOT / "operator-console/src"
SERVICES = ROOT / "src/security_platform/services"


def source(relative):
    return (CONSOLE / relative).read_text(encoding="utf-8")


def block(text, start, end):
    """The text between the first `start` and the next `end` after it."""
    head = text.index(start) + len(start)
    return text[head:text.index(end, head)]


def written_audit_objects():
    """action -> object_type of every audit write in the services."""
    pairs = {}
    for path in sorted(SERVICES.glob("*.py")):
        for action, object_type in re.findall(r'action="(\w+)", object_type="(\w+)"', path.read_text(encoding="utf-8")):
            assert pairs.setdefault(action, object_type) == object_type, action
    return pairs


def test_every_api_action_is_written_with_one_object_type():
    assert set(written_audit_objects()) == audit.ACTIONS


def test_audit_action_and_object_unions_match_the_api():
    contracts = source("data/contracts.ts")
    assert set(re.findall(r'"(\w+)"', block(contracts, "export type AuditAction =", ";"))) == audit.ACTIONS
    assert set(re.findall(r'"(\w+)"', block(contracts, "export type AuditObject =", ";"))) == audit.OBJECTS


def test_normalizer_maps_every_action_to_the_object_the_api_writes():
    mapping = dict(re.findall(r'(\w+): "(\w+)"', block(source("data/normalize.ts"), "const AUDIT_OBJECTS:", "};")))
    assert set(mapping) == audit.ACTIONS
    assert mapping == written_audit_objects()
    assert set(mapping.values()) <= audit.OBJECTS
    assert mapping["tenant_event_retention_set"] == "tenant"


def test_label_map_has_one_catalog_key_per_action():
    labels = dict(re.findall(r'(\w+): "([\w.]+)"', block(source("components/ProductViews.tsx"),
                                                          "const AUDIT_ACTIONS:", "};")))
    assert labels == {action: f"product.audit.action.{action}" for action in audit.ACTIONS}


@pytest.mark.parametrize("start,end,label", [
    ("export const productsTr = {", "\n};", "Olay saklama süresi değiştirildi"),
    ("export const productsEn = {", "\n} satisfies", "Event retention changed"),
])
def test_both_catalogs_label_every_action(start, end, label):
    catalog = block(source("i18n/catalogs/products.ts"), start, end)
    entries = dict(re.findall(r'"product\.audit\.action\.(\w+)": "([^"]+)"', catalog))
    assert set(entries) == audit.ACTIONS
    assert entries["tenant_event_retention_set"] == label
