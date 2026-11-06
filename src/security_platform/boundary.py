"""Bounded JSON and transport boundary with a per-process request budget."""
import asyncio
from collections import OrderedDict
import ipaddress
import json
import threading
import time


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _reject_constant(_):
    raise ValueError("nonfinite number")


class RequestBoundary:
    def __init__(self, app, *, settings):
        self.app, self.settings = app, settings
        self._buckets, self._lock = OrderedDict(), threading.Lock()

    def _allowed(self, client):
        now = time.monotonic()
        with self._lock:
            start, count = self._buckets.pop(client, (now, 0))
            if now - start >= 60:
                start, count = now, 0
            self._buckets[client] = (start, count + 1)
            while len(self._buckets) > 1024:
                self._buckets.popitem(last=False)
            return count < self.settings.requests_per_minute

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        async def protected_send(message):
            if message["type"] == "http.response.start":
                message = dict(message)
                headers = list(message.get("headers", []))
                present = {name.lower() for name, _ in headers}
                for name, value in ((b"cache-control", b"no-store"), (b"x-content-type-options", b"nosniff"),
                                    (b"referrer-policy", b"no-referrer")):
                    if name not in present:
                        headers.append((name, value))
                message["headers"] = headers
            await send(message)
        async def reject(status, detail):
            body = json.dumps({"detail": detail}).encode()
            await protected_send({"type": "http.response.start", "status": status,
                "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
            await protected_send({"type": "http.response.body", "body": body})
        headers = {}
        for key, value in scope.get("headers", []):
            key = key.lower()
            if key in {b"authorization", b"content-length", b"content-type", b"host", b"origin", b"content-encoding"} and key in headers:
                return await reject(400, "invalid_headers")
            headers[key] = value
        host = headers.get(b"host", b"").decode("latin-1")
        client = (scope.get("client") or ("", 0))[0]
        if scope.get("scheme") != "https":
            try:
                local_client = ipaddress.ip_address(client).is_loopback
            except ValueError:
                local_client = False
            hostname = host.split(":", 1)[0] if not host.startswith("[") else host.partition("]")[0] + "]"
            if not (self.settings.allow_loopback_http and local_client and hostname in {"localhost", "127.0.0.1", "[::1]"}):
                return await reject(400, "https_required")
        if b"origin" in headers and headers[b"origin"].decode("latin-1") != f"{scope.get('scheme')}://{host}":
            return await reject(403, "origin_rejected")
        if len(headers.get(b"authorization", b"")) > 16384:
            return await reject(401, "invalid_credentials")
        if scope["path"] not in {"/livez", "/readyz"} and not self._allowed(client):
            return await reject(429, "request_rate_exceeded")
        if headers.get(b"content-encoding", b"identity").lower() != b"identity":
            return await reject(415, "unsupported_encoding")
        declared = headers.get(b"content-length")
        if declared is not None:
            if (not declared.isdigit() or len(declared) > 8 or b"transfer-encoding" in headers):
                return await reject(400, "invalid_content_length")
            if int(declared) > 16384:
                return await reject(413, "request_too_large")
        parts, size, deadline = [], 0, time.monotonic() + self.settings.body_timeout_seconds
        try:
            for _ in range(1024):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return await reject(408, "body_timeout")
                message = await asyncio.wait_for(receive(), remaining)
                if message["type"] == "http.disconnect":
                    return
                if message["type"] != "http.request":
                    return await reject(400, "invalid_body")
                part = message.get("body", b"")
                size += len(part)
                if size > 16384:
                    return await reject(413, "request_too_large")
                parts.append(part)
                if not message.get("more_body", False):
                    break
            else:
                return await reject(413, "request_too_fragmented")
        except TimeoutError:
            return await reject(408, "body_timeout")
        if declared is not None and size != int(declared):
            return await reject(400, "invalid_content_length")
        body = b"".join(parts)
        if body:
            media = headers.get(b"content-type", b"").split(b";", 1)[0].strip().lower()
            if media != b"application/json":
                return await reject(415, "json_required")
            try:
                value = json.loads(body, object_pairs_hook=_unique, parse_constant=_reject_constant)
                pending, nodes = [(value, 0)], 0
                while pending:
                    value, depth = pending.pop()
                    nodes += 1
                    if depth > 12 or nodes > 2048:
                        raise ValueError("structure budget")
                    if isinstance(value, dict):
                        pending.extend((child, depth + 1) for child in value.values())
                    elif isinstance(value, list):
                        pending.extend((child, depth + 1) for child in value)
            except (ValueError, UnicodeError, RecursionError, OverflowError):
                return await reject(400, "invalid_json")
        delivered = False
        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()
        await self.app(scope, replay, protected_send)
