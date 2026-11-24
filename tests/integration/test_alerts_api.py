"""Signed operator JWTs, device bearers and real PostgreSQL for the three alert routes.

No auth dependency is overridden; fixtures come from test_api.py.
"""
from dataclasses import replace
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select

from security_platform.app import create_app
from security_platform.contracts import utc_text
from security_platform.models import Alert, AuditEvent, Principal
from test_api import api_context, api_database, auth, enroll, new_grant  # noqa: F401  (shared fixtures)


pytestmark = pytest.mark.integration
EVENTS = "/api/v1/device/events"
VOLUME = r"\Device\HarddiskVolume3"
WORD = VOLUME + r"\Program Files\Microsoft Office\root\Office16\WINWORD.EXE"
ALERT_KEYS = {"id", "device_id", "rule", "severity", "status", "occurrences", "first_event_seq", "last_event_seq",
              "first_seen_at", "last_seen_at", "evidence", "acknowledged_at", "closed_at", "source",
              "producer_verification"}


def downloads(name):
    return VOLUME + "\\Users\\*\\Downloads\\" + name


def launch(seq, image, *, pid=None, parent=4):
    return {"kind": "process_started", "event_seq": seq, "observed_at": "2030-01-02T03:00:00Z",
            "pid": 5000 + seq if pid is None else pid, "parent_pid": parent, "session_id": 1, "image": image}


def state(seq, value="lost", code=None):
    return {"kind": "sensor_state", "event_seq": seq, "observed_at": "2030-01-02T03:00:02Z", "state": value,
            "error_code": code}


def upload(ctx, device, sequence, *items, client=None):
    response = (client or ctx["client"]).post(EVENTS, json={"schema_version": 1, "batch_id": str(uuid4()),
        "batch_sequence": sequence, "events": list(items)}, headers=auth(device["credential_secret"]))
    assert response.status_code == 200, response.text


def alerts_path(tenant, suffix=""):
    return f"/api/v1/tenants/{tenant}/alerts{suffix}"


def listing(ctx, tenant=None, name="admin_a", query=""):
    response = ctx["client"].get(alerts_path(tenant or ctx["a"]) + query, headers=auth(ctx["token"](name)))
    assert response.status_code == 200, response.text
    return response.json()


def alert_audit(ctx, tenant):
    with ctx["owner"].session() as session:
        return [tuple(row) for row in session.execute(select(AuditEvent.actor_type, AuditEvent.actor_id,
            AuditEvent.action, AuditEvent.object_type, AuditEvent.object_id).where(
            AuditEvent.tenant_id == tenant, AuditEvent.object_type == "alert").order_by(AuditEvent.created_at))]


def stored_alert(ctx, alert_id):
    with ctx["owner"].session() as session:
        return session.get(Alert, UUID(alert_id))


def principal(ctx, name):
    with ctx["owner"].session() as session:
        return session.scalar(select(Principal.id).where(Principal.issuer == ctx["issuer"],
                                                         Principal.subject == ctx["subjects"][name]))


def test_alert_view_has_exactly_the_documented_keys_and_evidence_per_rule(api_context):
    ctx = api_context; client = ctx["client"]
    device, _ = enroll(ctx)
    upload(ctx, device, 1, launch(1, WORD, pid=100), launch(2, VOLUME + r"\Windows\System32\mshta.exe", parent=100),
           launch(3, downloads("setup.exe")), state(4, "failed", "access_denied"))
    upload(ctx, device, 2, state(9, "started"))
    page = listing(ctx, name="viewer")
    assert set(page) == {"items", "next_before"} and page["next_before"] is None
    by_rule = {item["rule"]: item for item in page["items"]}
    assert set(by_rule) == {"user_writable_launch", "office_browser_spawned_tool", "sensor_unstable", "event_loss"}
    evidence = {"user_writable_launch": {"image": downloads("setup.exe"), "pid": 5003},
                "office_browser_spawned_tool": {"image": VOLUME + r"\Windows\System32\mshta.exe", "pid": 5002,
                                                "parent_image": WORD, "parent_pid": 100},
                "sensor_unstable": {"state": "failed", "error_code": "access_denied"},
                "event_loss": {"missing_events": 4}}
    severity = {"user_writable_launch": "low", "office_browser_spawned_tool": "medium", "sensor_unstable": "medium",
                "event_loss": "medium"}
    for rule, item in by_rule.items():
        assert set(item) == ALERT_KEYS
        assert (item["device_id"], item["severity"], item["status"], item["occurrences"], item["evidence"]) == (
            device["device_id"], severity[rule], "open", 1, evidence[rule])
        assert (item["source"], item["producer_verification"]) == ("self_reported", "not_verified")
        assert UUID(item["id"]) and item["acknowledged_at"] is None and item["closed_at"] is None
        assert item["first_seen_at"].endswith("Z") and utc_text(item["first_seen_at"]) and utc_text(item["last_seen_at"])
        assert 1 <= item["first_event_seq"] <= item["last_event_seq"]
    assert (by_rule["event_loss"]["first_event_seq"], by_rule["office_browser_spawned_tool"]["first_event_seq"]) == (9, 2)
    response = client.get(alerts_path(ctx["a"]), headers=auth(ctx["token"]()))
    assert response.headers["cache-control"] == "no-store"
    closed = client.post(alerts_path(ctx["a"], f"/{by_rule['event_loss']['id']}/close"), json={},
                         headers=auth(ctx["token"]()))
    assert closed.status_code == 200 and set(closed.json()) == ALERT_KEYS
    assert closed.headers["cache-control"] == "no-store"


def test_every_member_reads_and_only_tenant_admins_acknowledge_or_close(api_context):
    ctx = api_context; client = ctx["client"]
    device, _ = enroll(ctx)
    upload(ctx, device, 1, launch(1, downloads("a.exe")), launch(2, downloads("b.exe")))
    for name in ("admin_a", "viewer", "both"):
        assert len(listing(ctx, name=name)["items"]) == 2, name
    first, second = (item["id"] for item in listing(ctx)["items"])
    for action in ("acknowledge", "close"):
        refused = client.post(alerts_path(ctx["a"], f"/{first}/{action}"), json={}, headers=auth(ctx["token"]("viewer")))
        assert refused.status_code == 403 and refused.json() == {"detail": "Tenant administrator role required"}
        # A role claim in the token grants nothing; the current membership decides.
        forged = ctx["token"]("viewer", roles=["tenant_admin"], is_admin=True)
        assert client.post(alerts_path(ctx["a"], f"/{first}/{action}"), json={}, headers=auth(forged)).status_code == 403
    assert stored_alert(ctx, first).status == "open" and alert_audit(ctx, ctx["a"]) == []
    # `both` administers A (and only views B).
    acknowledged = client.post(alerts_path(ctx["a"], f"/{first}/acknowledge"), json={}, headers=auth(ctx["token"]("both")))
    assert acknowledged.status_code == 200 and acknowledged.json()["status"] == "acknowledged"
    closed = client.post(alerts_path(ctx["a"], f"/{second}/close"), headers=auth(ctx["token"]()))
    assert closed.status_code == 200 and closed.json()["status"] == "closed"
    assert alert_audit(ctx, ctx["a"]) == [("operator", principal(ctx, "both"), "alert_acknowledged", "alert", UUID(first)),
                                          ("operator", principal(ctx, "admin_a"), "alert_closed", "alert", UUID(second))]


def test_alert_routes_hide_other_tenants_and_change_nothing_there(api_context):
    ctx = api_context; client = ctx["client"]
    a_device, _ = enroll(ctx)
    b_device, _ = enroll(ctx, ctx["b"], ctx["token"]("admin_b"))
    upload(ctx, a_device, 1, launch(1, downloads("a.exe")))
    upload(ctx, b_device, 1, launch(1, downloads("b.exe")))
    [a_alert] = listing(ctx)["items"]
    [b_alert] = listing(ctx, ctx["b"], "admin_b")["items"]
    assert (a_alert["device_id"], b_alert["device_id"]) == (a_device["device_id"], b_device["device_id"])
    hidden = (
        ("admin_b", "GET", alerts_path(ctx["a"])),
        ("admin_b", "GET", alerts_path(ctx["b"], f"?device_id={a_device['device_id']}")),
        ("admin_a", "GET", alerts_path(ctx["a"], f"?device_id={b_device['device_id']}")),
        ("admin_a", "GET", alerts_path(ctx["a"], f"?device_id={uuid4()}")),
        ("admin_b", "POST", alerts_path(ctx["a"], f"/{a_alert['id']}/acknowledge")),
        ("admin_b", "POST", alerts_path(ctx["a"], f"/{a_alert['id']}/close")),
        ("admin_b", "POST", alerts_path(ctx["b"], f"/{a_alert['id']}/acknowledge")),
        ("admin_b", "POST", alerts_path(ctx["b"], f"/{a_alert['id']}/close")),
        ("admin_a", "POST", alerts_path(ctx["a"], f"/{b_alert['id']}/close")),
        ("admin_a", "POST", alerts_path(ctx["a"], f"/{uuid4()}/acknowledge")),
        ("viewer", "GET", alerts_path(ctx["b"])),
        ("admin_a", "GET", alerts_path(uuid4())),
    )
    for name, method, url in hidden:
        response = client.request(method, url, json={} if method == "POST" else None, headers=auth(ctx["token"](name)))
        assert response.status_code == 404, (name, method, url, response.text)
        assert response.json() == {"detail": "Resource not found"}
    # A viewer of B learns nothing about an id from A: the role is refused first.
    assert client.post(alerts_path(ctx["b"], f"/{a_alert['id']}/close"), json={},
                       headers=auth(ctx["token"]("both"))).status_code == 403
    for headers in ({}, auth(a_device["credential_secret"]), auth(new_grant(ctx)["enrollment_token"])):
        for method, url in (("GET", alerts_path(ctx["a"])), ("POST", alerts_path(ctx["a"], f"/{a_alert['id']}/close")),
                            ("POST", alerts_path(ctx["a"], f"/{a_alert['id']}/acknowledge"))):
            response = client.request(method, url, json={} if method == "POST" else None, headers=headers)
            assert response.status_code == 401 and response.headers["www-authenticate"] == "Bearer"
    assert [item["id"] for item in listing(ctx, ctx["b"], "admin_b")["items"]] == [b_alert["id"]]
    assert (stored_alert(ctx, a_alert["id"]).status, stored_alert(ctx, b_alert["id"]).status) == ("open", "open")
    assert alert_audit(ctx, ctx["a"]) == [] and alert_audit(ctx, ctx["b"]) == []


def test_every_transition_writes_one_audit_row_and_repeats_write_none(api_context):
    ctx = api_context; client = ctx["client"]
    device, _ = enroll(ctx)
    upload(ctx, device, 1, launch(1, downloads("evidence-canary.exe")), state(2, "lost"))
    first, second = sorted(listing(ctx)["items"], key=lambda item: item["first_event_seq"])
    admin = auth(ctx["token"]())
    admin_id = principal(ctx, "admin_a")

    def post(alert, action, **options):
        return client.post(alerts_path(ctx["a"], f"/{alert['id']}/{action}"), headers=admin, **options)

    acknowledged = post(first, "acknowledge", json={})
    assert acknowledged.status_code == 200
    body = acknowledged.json()
    assert (body["status"], body["closed_at"]) == ("acknowledged", None) and utc_text(body["acknowledged_at"])
    assert {key: value for key, value in body.items() if key not in {"status", "acknowledged_at"}} == {
        key: value for key, value in first.items() if key not in {"status", "acknowledged_at"}}
    # Repeats answer 200 with the unchanged alert; an empty body is the same as {}.
    assert post(first, "acknowledge").json() == body
    assert post(first, "acknowledge", json={}).json() == body
    closed = post(first, "close", json={})
    assert closed.status_code == 200
    assert (closed.json()["status"], closed.json()["acknowledged_at"]) == ("closed", body["acknowledged_at"])
    assert post(first, "close", json={}).json() == closed.json()
    conflict = post(first, "acknowledge", json={})
    assert conflict.status_code == 409 and conflict.json() == {"detail": "Alert is closed"}
    for extra in ({"reason": "x"}, {"status": "closed"}, [], "close"):
        assert post(second, "close", json=extra).status_code == 422
    direct = post(second, "close", json={})
    assert direct.status_code == 200
    assert (direct.json()["status"], direct.json()["acknowledged_at"]) == ("closed", None)
    assert alert_audit(ctx, ctx["a"]) == [("operator", admin_id, "alert_acknowledged", "alert", UUID(first["id"])),
                                          ("operator", admin_id, "alert_closed", "alert", UUID(first["id"])),
                                          ("operator", admin_id, "alert_closed", "alert", UUID(second["id"]))]
    # The audit names the alert; it never carries the evidence.
    audit = client.get(f"/api/v1/tenants/{ctx['a']}/audit", headers=admin)
    assert audit.status_code == 200 and "evidence-canary" not in audit.text
    actions = [(item["action"], item["object_type"], item["object_id"]) for item in audit.json()["items"]
               if item["object_type"] == "alert"]
    assert actions == [("alert_closed", "alert", second["id"]), ("alert_closed", "alert", first["id"]),
                       ("alert_acknowledged", "alert", first["id"])]


def test_alert_list_pages_filters_and_validates_its_parameters(api_context):
    ctx = api_context; client = ctx["client"]
    device, _ = enroll(ctx)
    other, _ = enroll(ctx)
    b_device, _ = enroll(ctx, ctx["b"], ctx["token"]("admin_b"))
    upload(ctx, device, 1, *[launch(seq, downloads(f"{seq}.exe")) for seq in range(1, 6)])
    upload(ctx, other, 1, launch(1, downloads("x.exe")), state(2, "failed"))
    upload(ctx, device, 2, launch(6, downloads("3.exe")))
    everything = listing(ctx, query="?limit=100")["items"]
    keys = [(item["last_seen_at"], item["id"]) for item in everything]
    assert len(everything) == 7 and len(set(keys)) == 7
    with ctx["owner"].session() as session:
        rows = session.scalars(select(Alert).where(Alert.tenant_id == ctx["a"])).all()
    assert [item["id"] for item in everything] == [
        str(row.id) for row in sorted(rows, key=lambda row: (row.last_seen_at, row.id), reverse=True)]
    assert everything[0]["evidence"]["image"] == downloads("3.exe")
    collected, query = [], "?limit=3"
    while True:
        page = listing(ctx, query=query)
        collected += [item["id"] for item in page["items"]]
        if page["next_before"] is None:
            break
        assert set(page["next_before"]) == {"seen_at", "id"} and page["next_before"]["id"] == page["items"][-1]["id"]
        seen_at = page["next_before"]["seen_at"]
        assert len(seen_at) == 27 and seen_at.endswith("Z") and seen_at[19] == "."
        query = f"?limit=3&before_seen_at={seen_at}&before_id={page['next_before']['id']}"
    assert collected == [item["id"] for item in everything]
    admin = auth(ctx["token"]())
    assert client.post(alerts_path(ctx["a"], f"/{everything[0]['id']}/acknowledge"), json={}, headers=admin).status_code == 200
    assert client.post(alerts_path(ctx["a"], f"/{everything[1]['id']}/close"), json={}, headers=admin).status_code == 200
    for status, expected in (("acknowledged", [everything[0]["id"]]), ("closed", [everything[1]["id"]]),
                             ("open", [item["id"] for item in everything[2:]])):
        assert [item["id"] for item in listing(ctx, query=f"?status={status}")["items"]] == expected, status
    by_device = listing(ctx, query=f"?device_id={other['device_id']}")["items"]
    assert {item["device_id"] for item in by_device} == {other["device_id"]} and len(by_device) == 2
    combined = listing(ctx, query=f"?device_id={device['device_id']}&status=open&limit=1")
    assert len(combined["items"]) == 1 and combined["next_before"]["id"] == combined["items"][0]["id"]
    # The list pages only by the keyset; an offset is not a paging control.
    assert [item["id"] for item in listing(ctx, query="?offset=3")["items"]] == [item["id"] for item in everything]
    identity = everything[0]["id"]
    for query in ("limit=0", "limit=101", "limit=1.5", "limit=abc", "status=resolved", "status=OPEN", "device_id=abc",
                  "before_id=abc", f"before_id={identity}", "before_seen_at=2030-01-02T03:04:05.000000Z",
                  f"before_seen_at=2030-01-02T03:04:05Z&before_id={identity}",
                  f"before_seen_at=2030-01-02T03:04:05.123Z&before_id={identity}",
                  f"before_seen_at=2030-01-02T03:04:05.000000%2B00:00&before_id={identity}",
                  f"before_seen_at=2030-02-30T03:04:05.000000Z&before_id={identity}",
                  f"before_seen_at=2030-01-02T03:04:05.0000000Z&before_id={identity}"):
        response = client.get(alerts_path(ctx["a"]) + "?" + query, headers=admin)
        assert response.status_code == 422 and response.json() == {"detail": "invalid_request"}, query
    assert client.get(alerts_path(ctx["a"], f"?device_id={b_device['device_id']}"), headers=admin).status_code == 404


def test_events_get_reports_alert_openings_the_configured_cap_suppressed(api_context):
    ctx = api_context
    with TestClient(create_app(replace(ctx["settings"], max_open_alerts_per_device=10)),
                    base_url="https://platform.example.test") as client:
        device, _ = enroll({**ctx, "client": client})
        upload(ctx, device, 1, *[launch(seq, downloads(f"{seq}.exe")) for seq in range(1, 13)], client=client)
        upload(ctx, device, 2, launch(13, downloads("1.exe")), client=client)
        admin = auth(ctx["token"]())
        timeline = client.get(f"/api/v1/tenants/{ctx['a']}/devices/{device['device_id']}/events?limit=1", headers=admin)
        assert timeline.status_code == 200
        assert (timeline.json()["suppressed_alerts"], timeline.json()["cap_deleted_events"]) == (2, 0)
        alerts = client.get(alerts_path(ctx["a"], f"?device_id={device['device_id']}&limit=100"), headers=admin).json()
        assert len(alerts["items"]) == 10
        # An update of an open alert is never suppressed.
        assert {item["evidence"]["image"]: item["occurrences"] for item in alerts["items"]}[downloads("1.exe")] == 2
    quiet, _ = enroll(ctx)
    page = ctx["client"].get(f"/api/v1/tenants/{ctx['a']}/devices/{quiet['device_id']}/events",
                             headers=auth(ctx["token"]())).json()
    assert page == {"items": [], "next_before_seq": None, "cap_deleted_events": 0, "suppressed_alerts": 0}


def integers(value):
    """Every integer of a decoded JSON document."""
    if isinstance(value, dict):
        return [number for item in value.values() for number in integers(item)]
    if isinstance(value, list):
        return [number for item in value for number in integers(item)]
    return [value] if isinstance(value, int) and not isinstance(value, bool) else []


def test_event_seq_stops_at_the_consoles_safe_integer_limit(api_context):
    """2^53-1 (the console's Number.MAX_SAFE_INTEGER) is the largest event_seq; a batch holding 2^53 is refused
    whole, so no stored event, alert or page the console reads carries a larger integer."""
    ctx = api_context; client = ctx["client"]
    device, _ = enroll(ctx)
    admin = auth(ctx["token"]())
    timeline = f"/api/v1/tenants/{ctx['a']}/devices/{device['device_id']}/events"

    def post(sequence, *items):
        return client.post(EVENTS, json={"schema_version": 1, "batch_id": str(uuid4()), "batch_sequence": sequence,
                                         "events": list(items)}, headers=auth(device["credential_secret"]))

    upload(ctx, device, 1, state(1, "started"))
    # Each would match three rules and leave a gap after event 1; only the last event_seq differs.
    matching = [launch(5, downloads("a.exe")), state(6, "lost")]
    for last in (2**53, 2**63 - 1):
        refused = post(2, *matching, launch(last, downloads("b.exe"), pid=4242))
        assert refused.status_code == 422 and refused.json() == {"detail": "invalid_request"}, refused.text
    assert [item["event_seq"] for item in client.get(timeline, headers=admin).json()["items"]] == [1]
    assert listing(ctx)["items"] == []
    upload(ctx, device, 2, *matching, launch(2**53 - 1, downloads("b.exe"), pid=4242))
    by_key = {(item["rule"], item["evidence"].get("image")): item for item in listing(ctx)["items"]}
    assert {key: (item["occurrences"], item["first_event_seq"], item["last_event_seq"], item["evidence"])
            for key, item in by_key.items()} == {
        ("user_writable_launch", downloads("a.exe")): (1, 5, 5, {"image": downloads("a.exe"), "pid": 5005}),
        ("user_writable_launch", downloads("b.exe")): (
            1, 2**53 - 1, 2**53 - 1, {"image": downloads("b.exe"), "pid": 4242}),
        ("sensor_unstable", None): (1, 6, 6, {"state": "lost", "error_code": None}),
        # Gaps 2-4 and 7..2^53-2: the cumulative count stays below the limit as well.
        ("event_loss", None): (2, 5, 2**53 - 1, {"missing_events": 2**53 - 5}),
    }
    newest = client.get(timeline + "?limit=1", headers=admin).json()
    assert ([item["event_seq"] for item in newest["items"]], newest["next_before_seq"]) == ([2**53 - 1], 2**53 - 1)
    pages = [listing(ctx), newest, client.get(timeline, headers=admin).json()]
    assert max(number for page in pages for number in integers(page)) == 2**53 - 1
    # The device's numbering ends here: nothing above it is ever stored.
    assert post(3, state(2**53, "started")).status_code == 422
    assert [item["event_seq"] for item in client.get(timeline, headers=admin).json()["items"]] == [2**53 - 1, 6, 5, 1]
