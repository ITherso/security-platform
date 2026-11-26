"""Operator-console preview server (serve.py) startup failures and request guards.

The console build helpers are loaded from operator-console/ by file path so an
unrelated installed ``build`` package can never shadow them.
"""
import copy
import importlib.util
import json
from pathlib import Path
import re
import socket
import sys
import threading
from types import MappingProxyType

import pytest

REPO = Path(__file__).resolve().parents[2]
CONSOLE = REPO / "operator-console"


def _module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build = _module("operator_console_build", CONSOLE / "build.py")
_previous_build = sys.modules.get("build")
sys.modules["build"] = build  # serve.py does `from build import ...`.
try:
    serve = _module("operator_console_serve", CONSOLE / "serve.py")
finally:
    if _previous_build is None:
        sys.modules.pop("build", None)
    else:
        sys.modules["build"] = _previous_build


def _must_not_serve(*args, **kwargs):
    raise AssertionError("preview must not start serving")


@pytest.fixture
def dist(tmp_path, monkeypatch):
    """A minimal schema-2 dist exactly as build.read_dist() expects it."""
    root = tmp_path / "console"
    (root / "dist" / "assets").mkdir(parents=True)
    (root / "THIRD_PARTY_NOTICES.txt").write_text("Fixture notice.\nPermission is hereby granted, for tests only.\n",
                                                  encoding="utf-8")
    monkeypatch.setattr(build, "ROOT", root)
    monkeypatch.setattr(build, "DIST", root / "dist")
    assets = {"index.html": b"<!doctype html><title>console</title><script type=module src=/assets/console.js></script>\n",
              build.ENTRY_JS: build._license_header() + b"console.log('fixture');\n",
              "assets/console.css": b"body{margin:0}\n"}
    for name, raw in assets.items():
        (root / "dist" / name).write_bytes(raw)
    rows = build._rows(assets)
    manifest = {"schema_version": 2, "kind": "operator_console_static_build", "asset_set_sha256": build._digest(rows),
                "files": rows, "entry_files": ["index.html", build.ENTRY_JS, "assets/console.css"],
                "initial_files": ["assets/console.css", build.ENTRY_JS, "index.html"],
                "module_graph": [{"path": build.ENTRY_JS, "imports": [], "dynamic_imports": [], "css": ["assets/console.css"]}]}
    (root / "dist" / build.MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    assert set(build.read_dist()) == set(assets)
    return root


@pytest.fixture
def preview(dist):
    server = serve.PreviewServer(("127.0.0.1", 0), serve.PreviewHandler)
    server.assets = MappingProxyType({"/" + name: raw for name, raw in build.read_dist().items()})
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(5)


def _run(monkeypatch, port):
    monkeypatch.setattr(sys, "argv", ["serve.py", "--port", str(port)])
    monkeypatch.setattr(serve.PreviewServer, "serve_forever", _must_not_serve)
    return serve.main()


def _request(port, target, *, method="GET", hosts=None):
    hosts = [f"127.0.0.1:{port}"] if hosts is None else hosts
    lines = [f"{method} {target} HTTP/1.1", *(f"Host: {host}" for host in hosts), "Connection: close", "", ""]
    with socket.create_connection(("127.0.0.1", port), timeout=5) as connection:
        connection.sendall("\r\n".join(lines).encode("latin-1"))
        response = b""
        while chunk := connection.recv(65536):
            response += chunk
    head, _, body = response.partition(b"\r\n\r\n")
    status_line, *header_lines = head.decode("latin-1").split("\r\n")
    headers = {}
    for line in header_lines:
        key, _, value = line.partition(":")
        headers[key.strip().lower()] = value.strip()
    return int(status_line.split()[1]), headers, body


def test_missing_dist_reports_build_message_without_paths(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(build, "ROOT", tmp_path)
    monkeypatch.setattr(build, "DIST", tmp_path / "dist")
    monkeypatch.setattr(serve, "PreviewServer", _must_not_serve)
    monkeypatch.setattr(sys, "argv", ["serve.py", "--port", "8787"])
    assert serve.main() == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == serve.BUILD_UNAVAILABLE + "\n"
    assert "use the packaged console build or run pnpm build" in captured.err
    assert str(tmp_path) not in captured.err and "Traceback" not in captured.err


def test_build_not_matching_manifest_reports_build_message(dist, monkeypatch, capsys):
    (dist / "dist" / "index.html").write_bytes(b"<!doctype html><title>changed</title>\n")
    monkeypatch.setattr(serve, "PreviewServer", _must_not_serve)
    monkeypatch.setattr(sys, "argv", ["serve.py", "--port", "8787"])
    assert serve.main() == 1
    assert capsys.readouterr().err == serve.BUILD_UNAVAILABLE + "\n"


def test_busy_port_reports_port_message(dist, monkeypatch, capsys):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as holder:
        holder.bind(("127.0.0.1", 0))
        holder.listen(1)
        assert _run(monkeypatch, holder.getsockname()[1]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == serve.PORT_UNAVAILABLE + "\n"
    assert "choose another --port" in captured.err and str(dist) not in captured.err


def test_second_preview_cannot_cobind_running_preview(preview, monkeypatch, capsys):
    assert _run(monkeypatch, preview) == 1
    assert capsys.readouterr().err == serve.PORT_UNAVAILABLE + "\n"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as intruder:
        intruder.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        with pytest.raises(OSError):
            intruder.bind(("127.0.0.1", preview))


def test_preview_bind_is_exclusive_on_windows():
    assert serve.PreviewServer.allow_reuse_port is False
    if sys.platform == "win32":
        assert serve.PreviewServer.allow_reuse_address is False


def test_assets_carry_csp_and_security_headers(preview):
    status, headers, body = _request(preview, "/")
    assert status == 200 and body.startswith(b"<!doctype html>")
    assert headers["content-type"] == "text/html; charset=utf-8"
    assert headers["content-security-policy"] == serve.CSP
    assert "default-src 'none'" in serve.CSP and "frame-ancestors 'none'" in serve.CSP
    assert headers["x-content-type-options"] == "nosniff" and headers["x-frame-options"] == "DENY"
    assert headers["cache-control"] == "no-store" and headers["referrer-policy"] == "no-referrer"
    status, headers, body = _request(preview, "/assets/console.js")
    assert status == 200 and headers["content-type"] == "text/javascript; charset=utf-8"
    assert body.endswith(b"console.log('fixture');\n")
    status, headers, _ = _request(preview, "/", method="POST")
    assert status == 405 and headers["allow"] == "GET, HEAD"


@pytest.mark.parametrize("target", [
    "/../serve.py", "/..%2fserve.py", "/%2e%2e/serve.py", "/assets/../index.html", "/assets/%2e%2e/index.html",
    "/assets/..%5cbuild.py", "/assets\\console.js", "/%69ndex.html", "/index.html%00", "/INDEX.HTML",
    "/index.html?x=1", "/?lang=en", "/assets/console.js?v=1", "/index.html#top", "/build-manifest.json",
    "/assets/", "/dist/index.html", "/serve.py", "/build.py", "/THIRD_PARTY_NOTICES.txt", "//etc/passwd",
    "/C:/Windows/win.ini", "C:/Windows/win.ini", "*",
])
def test_rejects_traversal_encoded_query_and_unknown_targets(preview, target):
    status, headers, body = _request(preview, target)
    assert status == 404 and body == b"Request rejected.\n"
    assert headers["content-security-policy"] == serve.CSP


def test_absolute_form_target_is_rejected(preview):
    status, _, body = _request(preview, f"http://127.0.0.1:{preview}/index.html")
    assert status == 404 and body == b"Request rejected.\n"


@pytest.mark.parametrize("hosts", [["evil.example"], ["evil.example:{port}"], ["127.0.0.1"], ["[::1]:{port}"], [],
                                   [""], ["127.0.0.1:{port}", "127.0.0.1:{port}"], ["127.0.0.1:1"]])
def test_host_header_guard_rejects_foreign_or_ambiguous_hosts(preview, hosts):
    status, headers, body = _request(preview, "/", hosts=[host.format(port=preview) for host in hosts])
    assert status == 421 and body == b"Request rejected.\n"
    assert headers["content-security-policy"] == serve.CSP


@pytest.mark.parametrize("host", ["127.0.0.1:{port}", "localhost:{port}"])
def test_host_header_guard_accepts_loopback_names(preview, host):
    assert _request(preview, "/", hosts=[host.format(port=preview)])[0] == 200


# --- Static checks for the operator-console strictJson profiles (TypeScript is not compiled here).

SRC = CONSOLE / "src"
PROFILES = {"default", "termivar-comparison-v1", "termivar-assessment-v1", "sp-hbf-preview-v1", "sp-events-alerts-v1",
            "sp-device-detail-v1"}
BUDGET = re.compile(r'^\s*"?([a-z0-9-]+)"?: \{ depth: (\d+), nodes: (\d+), stringUnits: (\d+), arrayItems: (\d+), '
                    r'objectKeys: (\d+), tokens: (\d+) \},$', re.M)
TOKEN = re.compile(r'"(?:\\(?:["\\/bfnrt]|u[0-9a-fA-F]{4})|[^"\\\x00-\x1f])*"|[{}\[\]:,]'
                   r'|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?|true|false|null')


def _budgets():
    source = (SRC / "data" / "normalize.ts").read_text(encoding="utf-8")
    start = source.index("const STRICT_JSON_BUDGETS = {")
    table = source[start:source.index("} as const;", start)]
    keys = ("depth", "nodes", "stringUnits", "arrayItems", "objectKeys", "tokens")
    return source, {match[0]: dict(zip(keys, map(int, match[1:]))) for match in BUDGET.findall(table)}


def _usage(text):
    """Python mirror of strictJson's token count and boundedGraph's node walk."""
    tokens = len(TOKEN.findall(text))
    nodes, arrays, keys, strings, stack = 0, 0, 0, 0, [(json.loads(text), 0)]
    depth = 0
    while stack:
        item, level = stack.pop()
        nodes, depth = nodes + 1, max(depth, level)
        if isinstance(item, str):
            strings = max(strings, len(item.encode("utf-16-le")) // 2)
        elif isinstance(item, (list, dict)):
            children = item if isinstance(item, list) else list(item.values())
            arrays, keys = (max(arrays, len(item)), keys) if isinstance(item, list) else (arrays, max(keys, len(item)))
            stack.extend((child, level + 1) for child in children)
    return {"tokens": tokens, "nodes": nodes, "arrayItems": arrays, "objectKeys": keys, "stringUnits": strings, "depth": depth}


def _fits(text, budget):
    usage = _usage(text)
    return all(usage[key] <= budget[key] for key in usage), usage


def test_strict_json_profiles_are_closed_and_wired():
    source, budgets = _budgets()
    assert set(budgets) == PROFILES
    guard = re.search(r"requireValue\((profile === [^;]+)\);", source)[1]
    assert set(re.findall(r'profile === "([a-z0-9-]+)"', guard)) == PROFILES
    termivar = (SRC / "features" / "termivarReview" / "termivarAdapter.ts").read_text(encoding="utf-8")
    assert 'rawJson(selected, MAX_TERMIVAR_REVIEW_BYTES, "termivar-assessment-v1")' in termivar
    assert "strictJson(value, profile)" in termivar
    policy = (SRC / "features" / "policyReview" / "policyReviewAdapter.ts").read_text(encoding="utf-8")
    assert 'strictJson(contents, "sp-hbf-preview-v1")' in policy and "strictJson(contents)" not in policy
    assert budgets["default"] == {"depth": 12, "nodes": 12000, "stringUnits": 1024, "arrayItems": 100,
                                  "objectKeys": 32, "tokens": 60000}
    # The live adapter picks the profile from the fixed route: timeline and alert pages get the event profile.
    adapter = (SRC / "adapters" / "platformReadOnly.ts").read_text(encoding="utf-8")
    assert ('return operation.type === "events" || operation.type === "alerts" ? "sp-events-alerts-v1" : "default";'
            in adapter)
    assert "normalize(await bodyJson(response, responseProfile(operation)))" in adapter
    assert 'decode(bytes), profile); }' in adapter and adapter.count("strictJson(") == 1
    assert budgets["sp-events-alerts-v1"] == {**budgets["default"], "stringUnits": 2048}


def _largest_contract_image(prefix, suffix, fields):
    """The contract-valid process_started image with the most UTF-16 units for these event fields.

    1,024 code points, as many of them non-BMP (two UTF-16 units, four UTF-8 bytes) as the 4 KiB stored-event
    bound allows; the real Platform contract decides.
    """
    from pydantic import ValidationError

    from security_platform.event_contracts import ProcessStarted

    longest = None
    for astral in range(1024 - len(prefix) - len(suffix) + 1):
        image = prefix + "\U0001F512" * astral + "x" * (1024 - len(prefix) - len(suffix) - astral) + suffix
        try:
            ProcessStarted.model_validate({**fields, "image": image})
        except ValidationError:
            break
        longest = image
    return longest


def test_event_profile_fits_contract_maximum_non_bmp_images_in_full_pages():
    from datetime import datetime, timezone
    from types import SimpleNamespace
    from uuid import UUID

    from security_platform.event_contracts import MAX_EVENT_SEQ, ProcessStarted
    from security_platform.services.alerts import alert_view, keyset_time
    from security_platform.services.events import _event_view

    source, budgets = _budgets()
    profile = budgets["sp-events-alerts-v1"]
    # The contract bound: an image of at most 1,024 code points is at most 2,048 UTF-16 units, the profile's budget,
    # and the console's image normalizer (maskedImage -> text) accepts exactly that.
    [limit] = [item.max_length for item in ProcessStarted.model_fields["image"].metadata if hasattr(item, "max_length")]
    assert limit == 1024 and profile["stringUnits"] == 2 * limit
    assert "const image = eventText(value, 1024);" in source
    assert "value.length <= maximum * 2 && [...value].length <= maximum" in source
    assert "image: maskedImage(value.image)" in source and "maskedImage(evidence.parent_image)" in source
    fields = {"kind": "process_started", "event_seq": MAX_EVENT_SEQ, "observed_at": "2030-01-02T03:04:05.000006Z",
              "pid": 2**32 - 1, "parent_pid": 2**32 - 1, "session_id": 2**32 - 1}
    image = _largest_contract_image("\\Device\\HarddiskVolume3\\Users\\*\\Downloads\\", ".exe", fields)
    units = len(image.encode("utf-16-le")) // 2
    assert len(image) == 1024 and budgets["default"]["stringUnits"] < units <= profile["stringUnits"], units
    # Full 100-item pages exactly as the Platform's view functions render them.
    when = datetime(2030, 1, 2, 3, 4, 6, tzinfo=timezone.utc)
    events = [SimpleNamespace(event_seq=MAX_EVENT_SEQ - index, kind="process_started", observed_at=when,
                              received_at=when, payload=ProcessStarted.model_validate(
                                  {**fields, "event_seq": MAX_EVENT_SEQ - index, "image": image}).model_dump(mode="json"))
              for index in range(100)]
    alerts = [SimpleNamespace(id=UUID(int=1000 - index), device_id=UUID(int=7), rule="user_writable_launch",
                              severity="low", status="open", occurrences=2**31, first_event_seq=MAX_EVENT_SEQ - 100,
                              last_event_seq=MAX_EVENT_SEQ - index, first_seen_at=when, last_seen_at=when,
                              evidence={"image": image, "pid": 2**32 - 1}, acknowledged_at=None, closed_at=None)
              for index in range(100)]
    pages = [{"items": [_event_view(row) for row in events], "next_before_seq": events[-1].event_seq,
              "cap_deleted_events": 0, "suppressed_alerts": 0},
             {"items": [alert_view(row) for row in alerts],
              "next_before": {"seen_at": keyset_time(when), "id": str(alerts[-1].id)}}]
    for page in pages:
        text = json.dumps(page, ensure_ascii=False, separators=(",", ":"))
        assert len(text.encode("utf-8")) <= 512 * 1024
        assert not _fits(text, budgets["default"])[0]
        fits, usage = _fits(text, profile)
        assert fits, usage


def test_policy_profile_fits_cli_maximum_preview_within_512_kib():
    _, budgets = _budgets()
    preview = json.loads((SRC / "features/policyReview/examples/preview-output.json").read_text(encoding="utf-8"))
    row = {"policy_id": 1, "policy_name": "", "matched": False, "selected": False, "reasons": ["", "", "", ""]}
    result = preview["results"][0]
    for side in ("base", "candidate"):
        result[side].update(trace=[dict(row, policy_id=index + 1) for index in range(64)], trace_total=500, trace_complete=False)
    preview["results"] = [copy.deepcopy(result) for _ in range(32)]
    for index, entry in enumerate(preview["results"]):
        entry["scenario"]["scenario_id"] = f"s{index}"
    text = json.dumps(preview, separators=(",", ":"))
    assert len(text.encode("utf-8")) <= 512 * 1024
    assert not _fits(text, budgets["default"])[0]
    fits, usage = _fits(text, budgets["sp-hbf-preview-v1"])
    assert fits, usage
    reason = "\U0001F512" * 1024  # 1,024 CLI characters, 2,048 UTF-16 units.
    assert _fits(json.dumps({"reasons": [reason]}), budgets["sp-hbf-preview-v1"])[0]


def test_termivar_profile_fits_assessments_beyond_100_items_within_1_mib():
    _, budgets = _budgets()
    assessment = json.loads((SRC / "features/termivarReview/examples/assessment-example.json").read_text(encoding="utf-8"))
    item = assessment["items"][0]
    assessment["items"] = [dict(item, fingerprint=f"sha256:{index:064x}") for index in range(1200)]
    assessment["item_count"] = len(assessment["items"])
    text = json.dumps(assessment, separators=(",", ":"))
    assert len(text.encode("utf-8")) <= 1024 * 1024
    assert not _fits(text, budgets["default"])[0]
    fits, usage = _fits(text, budgets["termivar-assessment-v1"])
    assert fits, usage
    diagnostic = json.loads((SRC / "features/termivarReview/examples/incomplete-example.json").read_text(encoding="utf-8"))
    form = {"form_reference": "form-0000", "method": "get", "query_parameter_names": ["a"] * 256,
            "control_names": ["a"] * 256, "evidence_count": 0}
    diagnostic["assessment"]["report"]["forms"] = [dict(form, form_reference=f"form-{index:04d}") for index in range(480)]
    text = json.dumps(diagnostic, separators=(",", ":"))  # Densest adapter-shaped content near the 1 MiB cap.
    assert len(text.encode("utf-8")) <= 1024 * 1024
    fits, usage = _fits(text, budgets["termivar-assessment-v1"])
    assert fits, usage


def test_example_readmes_carry_no_local_absolute_paths():
    for relative in ("termivarReview/examples/README.md", "termivarComparison/examples/README.md"):
        text = (SRC / "features" / relative).read_text(encoding="utf-8")
        assert re.search(r"[A-Za-z]:[\\/]Users|/home/|/Users/", text) is None
