"""Bounded assembly of one offline HTML document from a closed projection.

Only three fixed, trusted adjacent assets are read. Packet/observation semantics
belong to the preserved Phase18 validators and desk_projection producer.
"""
from __future__ import annotations

import base64
import hashlib
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re

from commercial_handoff.input_loader import check_existing_path
from commercial_handoff.schema import InputError
from commercial_review import DEMO_LABEL
from commercial_review.review_contracts import (
    DELIVERY_BLOCKERS, REVIEW_REQUIREMENTS, check_json_budget,
)

from . import VIEW_CONTRACT


MAX_HTML_BYTES = 2 * 1024 * 1024
MAX_PROJECTION_BYTES = 256 * 1024
_ASSET_LIMITS = {
    "templates/review_desk.html": 128 * 1024,
    "assets/review_desk.js": 256 * 1024,
    "assets/review_desk.css": 128 * 1024,
}
_MARKERS = ("__DESK_DATA__", "__DESK_CSP__", "__DESK_STYLE__", "__DESK_SCRIPT__")
_ROOT_FIELDS = frozenset((
    "schema_version", "review_packet_digest", "source_assessment_digest", "demo_label",
    "source", "observations", "review_requirements", "delivery_blockers", "demo_only",
    "human_review_verified", "producer_verified", "release_authorized",
))
_SOURCE_FIELDS = frozenset(("profile", "status", "item_count", "manifest_status", "source_verification"))
_ROW_FIELDS = frozenset((
    "observation_id", "observation_key", "source_json_pointer", "fingerprint",
    "capability_id", "source_disposition", "review_status", "scope_status", "client_inclusion",
))


def _object(value, fields) -> dict:
    if type(value) is not dict or set(value) != set(fields):
        raise InputError("desk_invalid_projection_fields")
    return value


def _scalar_text(value) -> None:
    # Transport/shape guard only; the projection producer owns source semantics.
    if type(value) is not str or not value or len(value) > 256:
        raise InputError("desk_invalid_projection_text")


def _projection_bytes(projection: dict) -> bytes:
    check_json_budget(projection)
    row = _object(projection, _ROOT_FIELDS)
    if (type(row["schema_version"]) is not str or row["schema_version"] != VIEW_CONTRACT
            or type(row["demo_label"]) is not str or row["demo_label"] != DEMO_LABEL):
        raise InputError("desk_invalid_projection_contract")
    for key, expected in (("demo_only", True), ("human_review_verified", False),
                          ("producer_verified", False), ("release_authorized", False)):
        if type(row[key]) is not bool or row[key] is not expected:
            raise InputError("desk_invalid_projection_guard")
    _scalar_text(row["review_packet_digest"])
    _scalar_text(row["source_assessment_digest"])
    source = _object(row["source"], _SOURCE_FIELDS)
    if type(source["item_count"]) is not int or not 0 <= source["item_count"] <= 256:
        raise InputError("desk_invalid_projection_count")
    for key in _SOURCE_FIELDS - {"item_count"}:
        _scalar_text(source[key])
    observations = row["observations"]
    if type(observations) is not list or len(observations) > 256:
        raise InputError("desk_invalid_projection_array")
    for observation in observations:
        for value in _object(observation, _ROW_FIELDS).values():
            _scalar_text(value)
    for key, expected in (("review_requirements", REVIEW_REQUIREMENTS),
                          ("delivery_blockers", DELIVERY_BLOCKERS)):
        if type(row[key]) is not list or tuple(row[key]) != expected:
            raise InputError("desk_invalid_projection_limits")
    try:
        raw = json.dumps(projection, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8", "strict")
    except (TypeError, ValueError, UnicodeError):
        raise InputError("desk_invalid_projection_json") from None
    if not 0 < len(raw) <= MAX_PROJECTION_BYTES:
        raise InputError("desk_projection_size_limit")
    return raw


def _asset(relative_name: str) -> str:
    maximum = _ASSET_LIMITS.get(relative_name)
    if maximum is None:
        raise InputError("desk_invalid_asset_name")
    path = Path(__file__).absolute().parent / relative_name
    check_existing_path(path, directory=False)
    with path.open("rb") as stream:
        raw = stream.read(maximum + 1)
    if not 0 < len(raw) <= maximum:
        raise InputError("desk_asset_size_limit")
    try:
        value = raw.decode("utf-8", "strict")
    except UnicodeError:
        raise InputError("desk_invalid_asset_utf8") from None
    if value.startswith("\ufeff") or "\x00" in value:
        raise InputError("desk_invalid_asset_text")
    # HTML normalizes CRLF/CR. Hash the normalized text actually embedded below.
    return value.replace("\r\n", "\n").replace("\r", "\n")


class _TemplateGuard(HTMLParser):
    """Check the fixed template's marker contexts, not arbitrary input markup."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.capture = None
        self.fragments = []
        self.counts = {"style": 0, "program": 0, "data": 0, "csp": 0}

    def handle_starttag(self, tag, attrs):
        if tag in {"iframe", "frame", "frameset", "object", "embed", "base", "link",
                   "img", "audio", "video", "source", "track", "form"}:
            raise InputError("desk_invalid_template_resource")
        attributes = dict(attrs)
        if len(attributes) != len(attrs):
            raise InputError("desk_invalid_template_attributes")
        for key, value in attrs:
            if key.startswith("on") or key == "style":
                raise InputError("desk_invalid_template_attributes")
            if key in {"src", "srcset", "poster", "data", "background", "action", "formaction"}:
                raise InputError("desk_invalid_template_resource")
            if key == "href" and (not value or not value.startswith("#")):
                raise InputError("desk_invalid_template_resource")
        if tag == "meta" and "http-equiv" in attributes:
            if (type(attributes["http-equiv"]) is not str
                    or attributes["http-equiv"].lower() != "content-security-policy"
                    or attributes.get("content") != "__DESK_CSP__"):
                raise InputError("desk_invalid_template_csp")
            self.counts["csp"] += 1
        if tag in {"script", "style"}:
            if self.capture is not None:
                raise InputError("desk_invalid_template_context")
            if tag == "style":
                self.capture = "style"
            elif attributes.get("id") == "desk-data" and attributes.get("type") == "application/octet-stream":
                self.capture = "data"
            elif attributes.get("type") in (None, "text/javascript") and attributes.get("id") != "desk-data":
                self.capture = "program"
            else:
                raise InputError("desk_invalid_template_context")
            self.fragments = []

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            expected = {"style": "__DESK_STYLE__", "program": "__DESK_SCRIPT__", "data": "__DESK_DATA__"}
            if self.capture is None or "".join(self.fragments) != expected[self.capture]:
                raise InputError("desk_invalid_template_context")
            self.counts[self.capture] += 1
            self.capture = None
            self.fragments = []

    def handle_data(self, data):
        if self.capture is not None:
            self.fragments.append(data)

    def finish(self):
        if self.capture is not None or any(count != 1 for count in self.counts.values()):
            raise InputError("desk_invalid_template_context")


def _inline_hash(text: str) -> str:
    return base64.b64encode(hashlib.sha256(text.encode("utf-8", "strict")).digest()).decode("ascii")


def render_desk(projection: dict) -> bytes:
    """Assemble trusted fixed assets and base64 metadata without external I/O.

    No input path/URL is followed. Content encoding is not redaction, source
    authentication or acceptance of browser/OS download and isolation behavior.
    """
    data = base64.b64encode(_projection_bytes(projection)).decode("ascii")
    template = _asset("templates/review_desk.html")
    css = _asset("assets/review_desk.css")
    script = _asset("assets/review_desk.js")
    if "</style" in css.casefold() or "</script" in script.casefold():
        raise InputError("desk_invalid_inline_asset_boundary")
    if re.search(r"@import\b|url\s*\(", css, re.IGNORECASE):
        raise InputError("desk_external_css_resource")
    if any(template.count(marker) != 1 for marker in _MARKERS):
        raise InputError("desk_invalid_template_marker")
    guard = _TemplateGuard()
    guard.feed(template)
    guard.close()
    guard.finish()
    csp = "; ".join((
        "default-src 'none'", f"script-src 'sha256-{_inline_hash(script)}'",
        f"style-src 'sha256-{_inline_hash(css)}'", "connect-src 'none'",
        "img-src 'none'", "font-src 'none'", "object-src 'none'", "base-uri 'none'",
        "form-action 'none'", "worker-src 'none'", "frame-src 'none'",
    ))
    replacements = {"__DESK_DATA__": data, "__DESK_CSP__": escape(csp, quote=True),
                    "__DESK_STYLE__": css, "__DESK_SCRIPT__": script}
    # One substitution pass: asset/data contents cannot introduce another marker.
    page = re.sub(r"__DESK_(?:DATA|CSP|STYLE|SCRIPT)__", lambda match: replacements[match.group()], template)
    raw = page.encode("utf-8", "strict")
    if not 0 < len(raw) <= MAX_HTML_BYTES:
        raise InputError("desk_html_size_limit")
    return raw
