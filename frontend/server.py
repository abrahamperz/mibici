"""Simple dev server: serves index.html and proxies /api/ to the backend."""

import http.server
import urllib.request
import os
import subprocess

API_UPSTREAM = os.getenv("API_UPSTREAM", "http://api:8000")
GOOGLE_MAPS_KEY = os.getenv("GOOGLE_MAPS_KEY", "")
HTML_PATH = "/frontend/index.html"


def read_html():
    """Read HTML file bypassing VirtioFS cache by using a subprocess."""
    try:
        result = subprocess.run(
            ["cat", HTML_PATH],
            capture_output=True,
        )
        return result.stdout
    except Exception:
        with open(HTML_PATH, "rb") as f:
            return f.read()


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/"):
            self._proxy("GET")
        elif self.path.startswith("/favicon.ico"):
            self._serve_file("/frontend/favicon.ico", "image/x-icon")
        elif self.path.startswith("/js/") and self.path.endswith(".js"):
            filename = os.path.basename(self.path.split("?")[0])
            self._serve_file(f"/frontend/js/{filename}", "application/javascript",
                             cache="no-store")
        else:
            self._serve_html()

    def do_POST(self):
        if self.path.startswith("/api/"):
            self._proxy("POST")
        else:
            self.send_error(404)

    def do_PUT(self):
        if self.path.startswith("/api/"):
            self._proxy("PUT")
        else:
            self.send_error(404)

    def do_DELETE(self):
        if self.path.startswith("/api/"):
            self._proxy("DELETE")
        else:
            self.send_error(404)

    def _serve_file(self, path, content_type, cache="max-age=86400"):
        try:
            with open(path, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", cache)
            self.end_headers()
            self.wfile.write(data)
        except FileNotFoundError:
            self.send_error(404)

    def _serve_html(self):
        data = read_html().replace(b"__GOOGLE_MAPS_KEY__", GOOGLE_MAPS_KEY.encode())
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _proxy(self, method):
        upstream = API_UPSTREAM + self.path[4:]  # strip /api prefix
        body = None
        if method in ("POST", "PUT"):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else None
        headers = {}
        for key in ("Content-Type", "X-API-Key"):
            if self.headers.get(key):
                headers[key] = self.headers[key]
        req = urllib.request.Request(upstream, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                resp_body = resp.read()
                self.send_response(resp.status)
                for key, val in resp.getheaders():
                    if key.lower() not in ("transfer-encoding", "connection"):
                        self.send_header(key, val)
                self.end_headers()
                self.wfile.write(resp_body)
        except urllib.error.HTTPError as e:
            resp_body = e.read()
            self.send_response(e.code)
            for key, val in e.headers.items():
                if key.lower() not in ("transfer-encoding", "connection"):
                    self.send_header(key, val)
            self.end_headers()
            self.wfile.write(resp_body)

    def log_message(self, format, *args):
        pass  # silence logs


if __name__ == "__main__":
    server = http.server.HTTPServer(("0.0.0.0", 80), Handler)
    print("Frontend server on :80")
    server.serve_forever()
