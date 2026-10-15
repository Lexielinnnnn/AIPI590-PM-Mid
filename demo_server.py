"""Local Rental Radar web app. Run: python demo_server.py (standard library only)."""
import datetime as dt
import json
import pathlib
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
import rental_radar as rr

ROOT = pathlib.Path(__file__).resolve().parent
LOCK = threading.BoundedSemaphore(2)


def report_for(request):
    address = rr.normalize(str(request.get("address", "")))
    borough = str(request.get("borough", "")).upper()
    start, end = str(request.get("start", "")), str(request.get("end", ""))
    if not 5 <= len(address) <= 150 or not any(c.isdigit() for c in address):
        raise ValueError("Enter a street number and street name, for example 3325 Neptune Avenue.")
    if borough not in {"BROOKLYN", "BRONX", "MANHATTAN", "QUEENS", "STATEN ISLAND"}:
        raise ValueError("Choose one of the five NYC boroughs.")
    days = (dt.date.fromisoformat(end) - dt.date.fromisoformat(start)).days
    if not 1 <= days <= 731:
        raise ValueError("Choose a date window from 1 to 731 days. The end date is exclusive.")
    rows, retrieval = rr.fetch_311(address, borough, start, end)
    bbl, identity = rr.infer_bbl(rows)
    sources = {"311": {"records": rows, "retrieval": retrieval}}
    for key, fetcher in [("hpd_violations", lambda: rr.fetch_hpd_violations(bbl, start, end)),
                         ("bedbug_filings", lambda: rr.fetch_bedbug_filings(bbl))]:
        if bbl:
            records, provenance = fetcher()
        else:
            records, provenance = [], {"status": "skipped", "reason": "BBL unresolved or ambiguous"}
        sources[key] = {"records": records, "retrieval": provenance}
    raw = {"schema_version": 2, "address": address, "borough": borough, "start": start,
           "end": end, "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
           "bbl": bbl, "identity": identity, "sources": sources}
    return {"evidence": rr.build_evidence(raw), "mode": "live", "provenance": {k:v["retrieval"] for k,v in sources.items()}}


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/health":
            return self.send_json(200, {"status": "ready", "live_queries": True, "llm": "not_enabled"})
        if self.path.split("?")[0] not in {"/", "/index.html", "/Rental_Radar_Presentation.html"}:
            return self.send_json(404, {"error": "Not found"})
        page = ROOT / "presentation.html"
        if not page.exists():
            return self.send_json(503, {"error": "presentation.html is missing from the application folder"})
        body = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/api/report":
            return self.send_json(404, {"error": "Not found"})
        origin = self.headers.get("Origin")
        if origin and origin != "http://" + self.headers.get("Host", ""):
            return self.send_json(403, {"error": "Use the application on this local server."})
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self.send_json(415, {"error": "JSON required"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 4096:
                raise ValueError("Invalid request size")
            request = json.loads(self.rfile.read(size))
            if not isinstance(request, dict):
                raise ValueError("Request must be an object")
        except (ValueError, json.JSONDecodeError):
            return self.send_json(400, {"error": "Invalid request"})
        if not LOCK.acquire(blocking=False):
            return self.send_json(429, {"error": "Two queries are already running. Please try again shortly."})
        try:
            result = report_for(request)
            self.send_json(200, result)
        except ValueError as exc:
            self.send_json(400, {"error": str(exc)})
        except Exception:
            self.send_json(502, {"error": "NYC data could not be retrieved completely. Retry later or choose the verified offline example. No partial result is presented as complete."})
        finally:
            LOCK.release()

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    print("Rental Radar: http://127.0.0.1:8766  (Ctrl+C to stop)", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8766), Handler).serve_forever()
