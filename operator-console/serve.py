"""Loopback-only immutable static preview. No API forwarding or runtime access."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import sys
from types import MappingProxyType

from build import BuildError, read_dist

CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
       "img-src 'self'; font-src 'self'; base-uri 'none'; object-src 'none'; "
       "frame-ancestors 'none'; form-action 'none'")
CONTENT_TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
                 ".css": "text/css; charset=utf-8"}


class PreviewServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 16

    def handle_error(self, request, client_address):
        pass  # Connection failures must not dump request context or tracebacks.

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(5)
        return connection, address


class PreviewHandler(BaseHTTPRequestHandler):
    server_version = "OperatorConsolePreview"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass  # Request targets and headers must never enter preview logs.

    def _headers(self, status, length, media="text/plain; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", media)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Connection", "close")
        if status == 405:
            self.send_header("Allow", "GET, HEAD")
        self.end_headers()
        self.close_connection = True

    def send_error(self, code, message=None, explain=None):
        raw = b"Request rejected.\n"
        self._headers(code, len(raw))
        if getattr(self, "command", "") != "HEAD":
            self.wfile.write(raw)

    def _asset(self, *, head=False):
        port = self.server.server_address[1]
        host = self.headers.get_all("Host", [])
        allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        if port == 80:
            allowed_hosts.update(("127.0.0.1", "localhost"))
        if len(host) != 1 or host[0] not in allowed_hosts:
            return self.send_error(421)
        # Literal canonical paths only: no percent decoding, queries, aliases,
        # source traversal, directory fallback, redirects or project file access.
        target = "/index.html" if self.path == "/" else self.path
        raw = self.server.assets.get(target)
        if raw is None:
            return self.send_error(404)
        extension = target[target.rfind("."):]
        self._headers(200, len(raw), CONTENT_TYPES[extension])
        if not head:
            self.wfile.write(raw)

    def do_GET(self):
        self._asset()

    def do_HEAD(self):
        self._asset(head=True)

    def _unsupported(self):
        self.send_error(405)

    do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = do_TRACE = do_CONNECT = _unsupported


def _port(value):
    try:
        port = int(value)
        if not 1 <= port <= 65535:
            raise ValueError
        return port
    except ValueError as exc:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535") from exc


def main():
    parser = argparse.ArgumentParser(description="Serve the built console only on 127.0.0.1")
    parser.add_argument("--port", type=_port, default=8787)
    args = parser.parse_args()
    server = None
    try:
        assets = read_dist()
        server = PreviewServer(("127.0.0.1", args.port), PreviewHandler)
        server.assets = MappingProxyType({"/" + name: raw for name, raw in assets.items()})
        print(f"http://127.0.0.1:{server.server_address[1]}/", flush=True)
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    except (BuildError, OSError, ValueError, TypeError, RecursionError, OverflowError):
        print("preview_unavailable", file=sys.stderr)
        return 1
    finally:
        if server is not None:
            server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
