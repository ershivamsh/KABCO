from __future__ import annotations
import json
import os
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from .domain import CATEGORIES, ROLES, apply_safety_policy, confirmable_category, create_id, demo_user_from_token, infer_mock

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = Path(os.getenv("SORTAI_DATA_FILE", str(ROOT / "data" / "sortai.json")))
STORE_LOCK = threading.Lock()

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

def load_store() -> dict:
    if not DATA_FILE.exists():
        return {"scans": [], "inventory": [], "auditEvents": []}
    return json.loads(DATA_FILE.read_text())

def save_store(store: dict) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = DATA_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(store, indent=2))
    temporary.replace(DATA_FILE)

def auth(handler: BaseHTTPRequestHandler, required_role: str | None = None):
    token = handler.headers.get("Authorization", "")
    token = token[7:] if token.lower().startswith("bearer ") else ""
    user = demo_user_from_token(token)
    return user if user and (required_role is None or user["role"] == required_role) else None

class SortAIHandler(BaseHTTPRequestHandler):
    server_version = "SortAI/0.1 Python"
    def log_message(self, *_args):
        return
    def send_json(self, status: int, payload: object) -> None:
        raw = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)
    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")
    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            return self.send_json(200, {"status": "ok", "service": "sortai-api", "phase": 1, "runtime": "python"})
        if path == "/api/categories":
            return self.send_json(200, list(CATEGORIES.values()))
        if path == "/api/inventory":
            user = auth(self, "collector")
            if not user: return self.send_json(401, {"error": "Collector authentication required"})
            with STORE_LOCK: store = load_store()
            return self.send_json(200, {"items": [i for i in store["inventory"] if i["collectorId"] == user["id"]]})
        return self.send_json(404, {"error": "Route not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            data = self.read_json()
        except (ValueError, json.JSONDecodeError):
            return self.send_json(400, {"error": "Request body must be valid JSON"})
        if path == "/api/demo-login":
            if data.get("role") not in ROLES: return self.send_json(400, {"error": "Role must be collector, recycler, or admin"})
            token = f"demo-{data['role']}"
            return self.send_json(200, {"demoOnly": True, "token": token, "user": demo_user_from_token(token)})
        if path == "/api/scans":
            user = auth(self, "collector")
            if not user: return self.send_json(401, {"error": "Collector authentication required"})
            if data.get("mode") not in ("whole-device", "separated-component"):
                return self.send_json(400, {"error": "mode must be whole-device or separated-component"})
            created = now()
            scan = {"id": create_id("scan"), "collectorId": user["id"], "mode": data["mode"], "filename": data.get("filename"), "prediction": apply_safety_policy(infer_mock(data.get("filename", ""))), "status": "pending_confirmation", "createdAt": created}
            with STORE_LOCK:
                store = load_store()
                store["scans"].append(scan)
                store["auditEvents"].append({"id": create_id("audit"), "action": "scan.created", "actorId": user["id"], "entityId": scan["id"], "at": created})
                save_store(store)
            return self.send_json(201, scan)
        prefix, suffix = "/api/scans/", "/confirm"
        if path.startswith(prefix) and path.endswith(suffix):
            user = auth(self, "collector")
            if not user: return self.send_json(401, {"error": "Collector authentication required"})
            scan_id = path[len(prefix):-len(suffix)]
            with STORE_LOCK:
                store = load_store()
                scan = next((s for s in store["scans"] if s["id"] == scan_id and s["collectorId"] == user["id"]), None)
                if not scan: return self.send_json(404, {"error": "Scan not found"})
                if scan["status"] != "pending_confirmation": return self.send_json(409, {"error": "Scan has already been confirmed or cancelled"})
                category_id = data.get("confirmedCategory")
                if not confirmable_category(category_id): return self.send_json(400, {"error": "confirmedCategory is not a supported category"})
                predicted_category = scan["prediction"]["category"]
                confirmed = apply_safety_policy({**scan["prediction"], "category": category_id})
                confirmed_at = now()
                scan.update({"confirmedCategory": category_id, "confirmedAt": confirmed_at, "status": "confirmed", "prediction": confirmed})
                item = {"id": create_id("inventory"), "scanId": scan["id"], "collectorId": user["id"], "category": category_id, "predictedCategory": predicted_category, "confidence": confirmed["confidence"], "crate": confirmed["crate"], "colour": confirmed["colour"], "safetyFlags": ["review_required"] if confirmed["reviewRequired"] else [], "quantity": data.get("quantity", 1), "weightKg": data.get("weightKg"), "weightSource": "manual" if data.get("weightKg") is not None else "not_measured", "createdAt": confirmed_at}
                store["inventory"].append(item)
                store["auditEvents"].append({"id": create_id("audit"), "action": "inventory.confirmed", "actorId": user["id"], "entityId": item["id"], "at": confirmed_at})
                save_store(store)
            return self.send_json(201, {"scan": scan, "inventoryItem": item})
        return self.send_json(404, {"error": "Route not found"})

def create_server(host: str = "127.0.0.1", port: int = 3000) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), SortAIHandler)

def main() -> None:
    port = int(os.getenv("PORT", "3000"))
    server = create_server(port=port)
    print(f"SortAI Python API listening on http://127.0.0.1:{port}")
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__ == "__main__": main()
