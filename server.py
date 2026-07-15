"""Local web server for the Construction Cost Estimator.

Standard-library only (http.server) apart from openpyxl for the Excel
export. No auth, no database — a single-user local tool.
"""

import json
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from estimator import EstimateError, compute_estimate, format_for_json
from excel_export import build_workbook, export_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(BASE_DIR, "templates", "index.html")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

HOST = "127.0.0.1"
PORT = 8000


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # keep the console quiet for a local dev tool

    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw or b"{}")

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            with open(TEMPLATE_PATH, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/api/quick-estimate":
            self._handle_quick_estimate()
        elif self.path == "/api/quick-estimate-export":
            self._handle_quick_estimate_export()
        else:
            self.send_error(404)

    def _handle_quick_estimate(self):
        body = self._read_json_body()
        try:
            est = compute_estimate(
                building_type=body.get("building_type", ""),
                sf=float(body.get("sf", 0)),
                city=body.get("city", ""),
                quality=body.get("quality", "Average"),
                loan_rate=float(body.get("loan_rate", 8.5)),
                const_months=int(body.get("const_months", 12)),
                land_cost=float(body.get("land_cost", 0)),
            )
        except EstimateError as e:
            self._send_json(400, {"detail": str(e)})
            return
        self._send_json(200, format_for_json(est))

    def _handle_quick_estimate_export(self):
        body = self._read_json_body()
        try:
            est = compute_estimate(
                building_type=body.get("building_type", ""),
                sf=float(body.get("sf", 0)),
                city=body.get("city", ""),
                quality=body.get("quality", "Average"),
                loan_rate=float(body.get("loan_rate", 8.5)),
                const_months=int(body.get("const_months", 12)),
                land_cost=float(body.get("land_cost", 0)),
            )
        except EstimateError as e:
            self._send_json(400, {"detail": str(e)})
            return

        wb = build_workbook(est)
        filename = export_filename(est["city"])
        filepath = os.path.join(OUTPUT_DIR, filename)
        wb.save(filepath)

        with open(filepath, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header(
            "Content-Type",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://{HOST}:{PORT}/"
    print(f"Construction Cost Estimator running at {url}")
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
