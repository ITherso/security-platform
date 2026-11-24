"""Signed operator JWTs, device bearers and real PostgreSQL for the two event routes.

No auth dependency is overridden; fixtures come from test_api.py.
"""
from dataclasses import replace
from datetime import timedelta
import json
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from security_platform.app import create_app
from security_platform.contracts import utc_text
from security_platform.event_contracts import (MAX_OBSERVED_AT, MIN_OBSERVED_AT, EventBatch, EventBatchTooLarge,
    canonical_event_batch)
from security_platform.services.common import iso
from test_api import api_context, api_database, auth, enroll, new_grant, snapshot  # noqa: F401  (shared fixtures)


pytestmark = pytest.mark.integration
EVENTS = "/api/v1/device/events"
MASKED = r"\Device\HarddiskVolume3\Users\*\Downloads\setup.exe"
CANARY = "private-input-canary"


def started(seq, **changes):
    return {"kind": "process_started", "event_seq": seq, "observed_at": "2030-01-02T03:00:00.000001Z",
            "pid": 4000 + seq, "parent_pid": 4, "session_id": 1, "image": MASKED, **changes}


def sensor(seq, **changes):
    return {"kind": "sensor_state", "event_seq": seq, "observed_at": "2030-01-02T03:00:02Z",
            "state": "lost", "error_code": "session_in_use", **changes}


def body(sequence=1, items=None, **changes):
    return {"schema_version": 1, "batch_id": str(uuid4()), "batch_sequence": sequence,
            "events": items if items is not None else [started(1), sensor(2)], **changes}


def timeline_path(tenant, device):
    return f"/api/v1/tenants/{tenant}/devices/{device['device_id']}/events"


def timeline(ctx, device, tenant=None, name="admin_a"):
    response = ctx["client"].get(timeline_path(tenant or ctx["a"], device), headers=auth(ctx["token"](name)))
    assert response.status_code == 200, response.text
    return response.json()


def test_event_route_accepts_only_a_device_bearer(api_context):
    ctx = api_context; client = ctx["client"]
    device, _ = enroll(ctx)
    unused_grant = new_grant(ctx)
    payload = body()
    for headers in ({}, auth(ctx["token"]()), auth(ctx["token"]("viewer")), auth(unused_grant["enrollment_token"]),
                    auth("spd_" + "A" * 43), {"Authorization": "Basic " + "A" * 24}):
        response = client.post(EVENTS, json=payload, headers=headers)
        assert response.status_code == 401, response.text
        assert response.headers["www-authenticate"] == "Bearer"
    accepted = client.post(EVENTS, json=payload, headers=auth(device["credential_secret"]))
    assert accepted.status_code == 200, accepted.text
    ack = accepted.json()
    assert set(ack) == {"accepted", "batch_id", "batch_sequence", "last_event_seq", "received_at"}
    assert (ack["accepted"], ack["batch_id"], ack["batch_sequence"], ack["last_event_seq"]) == (
        True, payload["batch_id"], 1, 2)
    assert ack["received_at"].endswith("Z") and utc_text(ack["received_at"])
    assert accepted.headers["cache-control"] == "no-store" and len(accepted.content) <= 4096
    replay = client.post(EVENTS, json=payload, headers=auth(device["credential_secret"]))
    assert replay.status_code == 200 and replay.json() == ack
    # The refused attempts stored nothing: batch 1 was still free to accept.
    assert [item["event_seq"] for item in timeline(ctx, device)["items"]] == [2, 1]


def test_malformed_event_bodies_are_422_without_echo_or_write(api_context):
    ctx = api_context; client = ctx["client"]
    device, _ = enroll(ctx)
    headers = auth(device["credential_secret"])
    malformed = [
        body(metadata=CANARY), body(device_id=device["device_id"]), body(tenant_id=str(ctx["b"])),
        body(source="self_reported"), body(producer_verification="verified"), body(schema_version=2),
        body(batch_sequence=True), body(batch_sequence=0), body(batch_id=CANARY), body(items=[]),
        body(items=[started(1, command_line=CANARY)]),
        body(items=[started(1, image="\\Device\\HarddiskVolume3\\Users\\" + CANARY + "\\tool.exe")]),
        body(items=[started(2), sensor(1)]), body(items=[{**sensor(1), "kind": "network_connection"}]),
        body(items=[sensor(1, state="started", error_code="unknown")]),
        body(items=[started(1, observed_at="2030-01-02T06:00:00+03:00")]),
        body(items=[started(1, pid=2**32)]), body(items=[started(1, image="\\" + "\U0001F600" * 1023)]),
    ]
    for payload in malformed:
        response = client.post(EVENTS, json=payload, headers=headers)
        assert response.status_code == 422, response.text
        assert response.json() == {"detail": "invalid_request"} and CANARY not in response.text
    assert timeline(ctx, device) == {"items": [], "next_before_seq": None, "cap_deleted_events": 0,
                                     "suppressed_alerts": 0}
    assert client.post(EVENTS, json=body(), headers=headers).status_code == 200


def test_event_body_limits(api_context):
    ctx = api_context; client = ctx["client"]
    device, _ = enroll(ctx)
    headers = {**auth(device["credential_secret"]), "Content-Type": "application/json"}
    oversized = json.dumps(body(items=[started(seq, image="\\" + "a" * 1000) for seq in range(1, 18)])).encode()
    assert len(oversized) > 16384
    response = client.post(EVENTS, content=oversized, headers=headers)
    assert response.status_code == 413 and response.json() == {"detail": "request_too_large"}
    too_many_nodes = json.dumps(body(items=[0] * 2100)).encode()
    assert len(too_many_nodes) <= 16384
    response = client.post(EVENTS, content=too_many_nodes, headers=headers)
    assert response.status_code == 400 and response.json() == {"detail": "invalid_json"}
    response = client.post(EVENTS, content=json.dumps(body()).encode(), headers={**headers, "Content-Type": "text/plain"})
    assert response.status_code == 415
    # The body fits in 16 KiB, its canonical form (microsecond times, explicit
    # nulls) does not: the service refuses it after schema validation with 413,
    # so a 400 only ever comes from the request boundary.
    compact = [{"kind": "sensor_state", "event_seq": seq, "observed_at": "2030-01-02T03:00:00Z", "state": "lost"}
               for seq in range(1, 161)]
    payload = body(items=compact)
    encoded = json.dumps(payload, separators=(",", ":")).encode()
    assert len(encoded) <= 16384
    with pytest.raises(EventBatchTooLarge, match="event_batch_too_large"):
        canonical_event_batch(EventBatch.model_validate(payload))
    response = client.post(EVENTS, content=encoded, headers=headers)
    assert response.status_code == 413 and response.json() == {"detail": "Event batch too large"}
    assert timeline(ctx, device)["items"] == []
    assert client.post(EVENTS, json=body(), headers=headers).json()["batch_sequence"] == 1


def test_configured_per_device_cap_applies_through_the_api(api_context):
    ctx = api_context
    with TestClient(create_app(replace(ctx["settings"], max_events_per_device=1000)),
                    base_url="https://platform.example.test") as client:
        device, _ = enroll({**ctx, "client": client})
        headers = {**auth(device["credential_secret"]), "Content-Type": "application/json"}
        for sequence in range(1, 9):
            items = [{"kind": "sensor_state", "event_seq": (sequence - 1) * 130 + index, "state": "started",
                      "observed_at": "2030-01-02T03:00:02Z", "error_code": None} for index in range(1, 131)]
            reply = client.post(EVENTS, content=json.dumps(body(sequence, items), separators=(",", ":")).encode(),
                                headers=headers)
            assert reply.status_code == 200, reply.text
        # 1040 sent; the configured cap keeps the newest 1000 (event_seq 41..1040)
        # and the timeline reports the 40 rows it deleted.
        path, admin = timeline_path(ctx["a"], device), auth(ctx["token"]())
        newest = client.get(path + "?limit=1", headers=admin).json()
        assert [item["event_seq"] for item in newest["items"]] == [1040] and newest["cap_deleted_events"] == 40
        oldest = client.get(path + "?before_seq=42", headers=admin).json()
        assert [item["event_seq"] for item in oldest["items"]] == [41] and oldest["cap_deleted_events"] == 40


def test_event_replay_and_conflicts_over_http(api_context):
    ctx = api_context; client = ctx["client"]
    device, _ = enroll(ctx)
    headers = auth(device["credential_secret"])
    first = body(5, [started(10), sensor(11)])
    accepted = client.post(EVENTS, json=first, headers=headers)
    assert accepted.status_code == 200, accepted.text
    assert client.post(EVENTS, json=first, headers=headers).json() == accepted.json()
    identity = "Event batch identity or sequence conflicts with current state"
    for conflicting, detail in (
            (body(5, [started(12)]), identity), ({**first, "batch_sequence": 6, "events": [started(12)]}, identity),
            ({**first, "events": [started(10), sensor(11, state="failed")]}, identity),
            (body(4, [started(12)]), "Event batch sequence is stale"),
            (body(6, [started(11)]), "Event sequence does not follow the last accepted event")):
        response = client.post(EVENTS, json=conflicting, headers=headers)
        # The accepted position, for diagnosis; the agent holds the batch.
        assert response.status_code == 409
        assert response.json() == {"detail": detail, "last_batch_sequence": 5, "last_event_seq": 11}
    later = client.post(EVENTS, json=body(6, [started(12)]), headers=headers)
    assert later.status_code == 200 and later.json()["last_event_seq"] == 12
    stale = client.post(EVENTS, json=body(6, [started(13)]), headers=headers)
    assert stale.status_code == 409 and stale.json() == {"detail": identity, "last_batch_sequence": 6,
                                                         "last_event_seq": 12}


def test_other_routes_keep_the_plain_409_body(api_context):
    ctx = api_context; client = ctx["client"]
    device, grant = enroll(ctx)
    headers = auth(device["credential_secret"])
    message = snapshot()
    assert client.put("/api/v1/device/snapshot", json=message, headers=headers).status_code == 200
    changed = client.put("/api/v1/device/snapshot", json={**message, "products": [
        {"product_id": "antivirus", "status": "planned"}]}, headers=headers)
    assert changed.status_code == 409
    assert changed.json() == {"detail": "Snapshot identity or sequence conflicts with current state"}
    consumed = client.post(f"/api/v1/tenants/{ctx['a']}/enrollment-grants/{grant['grant_id']}/revoke", json={},
                           headers=auth(ctx["token"]()))
    assert consumed.status_code == 409 and set(consumed.json()) == {"detail"}


def test_extreme_accepted_observed_times_keep_the_timeline_readable(api_context):
    ctx = api_context; client = ctx["client"]
    device, _ = enroll(ctx)
    headers = auth(device["credential_secret"])
    earliest, latest = iso(MIN_OBSERVED_AT), iso(MAX_OBSERVED_AT - timedelta(microseconds=1))
    sent = client.post(EVENTS, json=body(1, [started(1, observed_at=earliest), sensor(2, observed_at=latest),
                                             sensor(3)]), headers=headers)
    assert sent.status_code == 200, sent.text
    path, admin = timeline_path(ctx["a"], device), auth(ctx["token"]())
    # Every page holding an extreme renders, whatever the server's time zone.
    for query in ("", "?limit=1&before_seq=3", "?limit=1&before_seq=2"):
        page = client.get(path + query, headers=admin)
        assert page.status_code == 200, (query, page.text)
    assert [(item["event_seq"], item["observed_at"]) for item in client.get(path, headers=admin).json()["items"]] == [
        (3, "2030-01-02T03:00:02Z"), (2, "9998-12-31T23:59:59.999999Z"), (1, "1970-01-01T00:00:00Z")]
    for outside in ("1969-12-31T23:59:59.999999Z", "9999-01-01T00:00:00Z", "9999-12-31T23:59:59.999999Z",
                    "0001-01-01T00:00:00Z"):
        refused = client.post(EVENTS, json=body(2, [sensor(4, observed_at=outside)]), headers=headers)
        assert refused.status_code == 422 and refused.json() == {"detail": "invalid_request"}, outside
    assert len(timeline(ctx, device)["items"]) == 3


def test_event_cursor_belongs_to_the_device_across_rotation_and_ends_at_revocation(api_context):
    ctx = api_context; client = ctx["client"]
    device, _ = enroll(ctx)
    assert client.post(EVENTS, json=body(1), headers=auth(device["credential_secret"])).status_code == 200
    rotated = client.post("/api/v1/device/credentials/rotate", json={}, headers=auth(device["credential_secret"]))
    assert rotated.status_code == 200
    secret = rotated.json()["credential_secret"]
    assert client.post(EVENTS, json=body(2, [started(3)]), headers=auth(device["credential_secret"])).status_code == 401
    conflict = client.post(EVENTS, json=body(1, [started(3)]), headers=auth(secret))
    assert conflict.status_code == 409
    assert (conflict.json()["last_batch_sequence"], conflict.json()["last_event_seq"]) == (1, 2)
    assert client.post(EVENTS, json=body(2, [started(3)]), headers=auth(secret)).status_code == 200
    revoked = client.post(f"/api/v1/tenants/{ctx['a']}/devices/{device['device_id']}/revoke", json={},
                          headers=auth(ctx["token"]()))
    assert revoked.status_code == 200
    assert client.post(EVENTS, json=body(3, [started(4)]), headers=auth(secret)).status_code == 401
    assert [item["event_seq"] for item in timeline(ctx, device)["items"]] == [3, 2, 1]


def test_event_identity_comes_from_the_bearer_not_headers(api_context):
    ctx = api_context; client = ctx["client"]
    first, _ = enroll(ctx)
    second, _ = enroll(ctx, ctx["b"], ctx["token"]("admin_b"))
    headers = {**auth(first["credential_secret"]), "X-Device-ID": second["device_id"], "X-Tenant-ID": str(ctx["b"])}
    assert client.post(EVENTS, json=body(), headers=headers).status_code == 200
    assert len(timeline(ctx, first)["items"]) == 2
    assert timeline(ctx, second, ctx["b"], "admin_b")["items"] == []


def test_operator_timeline_authorization_paging_and_bounds(api_context):
    ctx = api_context; client = ctx["client"]
    device, _ = enroll(ctx)
    b_device, _ = enroll(ctx, ctx["b"], ctx["token"]("admin_b"))
    sent = client.post(EVENTS, json=body(1, [started(1), sensor(2), started(3)]), headers=auth(device["credential_secret"]))
    assert sent.status_code == 200
    path = timeline_path(ctx["a"], device)
    for name in ("admin_a", "viewer", "both"):
        response = client.get(path, headers=auth(ctx["token"](name)))
        assert response.status_code == 200, (name, response.text)
        assert [item["event_seq"] for item in response.json()["items"]] == [3, 2, 1]
        assert response.headers["cache-control"] == "no-store"
    hidden = (("admin_b", path), ("admin_b", timeline_path(ctx["b"], device)),
              ("admin_a", timeline_path(ctx["a"], b_device)), ("admin_a", timeline_path(ctx["b"], b_device)),
              ("viewer", timeline_path(ctx["b"], b_device)),
              ("admin_a", f"/api/v1/tenants/{ctx['a']}/devices/{uuid4()}/events"))
    for name, url in hidden:
        assert client.get(url, headers=auth(ctx["token"](name))).status_code == 404, (name, url)
    for headers in ({}, auth(device["credential_secret"]), auth(new_grant(ctx)["enrollment_token"])):
        assert client.get(path, headers=headers).status_code == 401
    admin = auth(ctx["token"]())
    first = client.get(path + "?limit=2", headers=admin).json()
    assert set(first) == {"items", "next_before_seq", "cap_deleted_events", "suppressed_alerts"}
    assert first["cap_deleted_events"] == 0 and first["suppressed_alerts"] == 0
    assert [item["event_seq"] for item in first["items"]] == [3, 2] and first["next_before_seq"] == 2
    second = client.get(path + "?limit=2&before_seq=2", headers=admin).json()
    assert [item["event_seq"] for item in second["items"]] == [1] and second["next_before_seq"] is None
    newest = first["items"][0]
    assert (newest["kind"], newest["image"], newest["source"], newest["producer_verification"]) == (
        "process_started", MASKED, "self_reported", "not_verified")
    for query in ("limit=0", "limit=101", "limit=1.5", "before_seq=0", "before_seq=-1", "before_seq=abc",
                  f"before_seq={2**63}"):
        assert client.get(path + "?" + query, headers=admin).status_code == 422, query
    # The timeline pages only by before_seq; an offset is not a paging control.
    assert [item["event_seq"] for item in client.get(path + "?offset=2", headers=admin).json()["items"]] == [3, 2, 1]
