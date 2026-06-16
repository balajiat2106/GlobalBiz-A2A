import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from agents.advisor import BusinessAdvisorAgent


ROOT = Path(__file__).resolve().parent
STATIC_ROOT = ROOT / "static"


class MissionControlHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self._send_file(STATIC_ROOT / "index.html", "text/html")
            return

        if self.path.startswith("/static/"):
            relative = unquote(self.path.removeprefix("/static/"))
            target = (STATIC_ROOT / relative).resolve()
            if not str(target).startswith(str(STATIC_ROOT.resolve())):
                self._send_json({"error": "Invalid path"}, status=400)
                return

            content_type = {
                ".css": "text/css",
                ".js": "application/javascript",
                ".html": "text/html",
            }.get(target.suffix, "application/octet-stream")
            self._send_file(target, content_type)
            return

        self._send_json({"error": "Not found"}, status=404)

    def do_POST(self):
        if self.path != "/api/analyze":
            self._send_json({"error": "Not found"}, status=404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            query = payload.get("query", "").strip()
            if not query:
                self._send_json({"error": "Query is required"}, status=400)
                return

            report = BusinessAdvisorAgent().recommend(query)
            self._send_json(report)
        except Exception as error:
            self._send_json({"action": "server_error", "message": str(error)}, status=500)

    def _send_file(self, path, content_type):
        if not path.exists() or not path.is_file():
            self._send_json({"error": "Not found"}, status=404)
            return

        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, payload, status=200):
        content = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format, *args):
        return


def main():
    host = "127.0.0.1"
    port = 8090
    server = ThreadingHTTPServer((host, port), MissionControlHandler)
    print(f"Mission Control running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
