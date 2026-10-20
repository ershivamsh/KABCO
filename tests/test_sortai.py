import json
import os
import tempfile
import threading
import unittest
from urllib.request import Request, urlopen

DATA_DIR = tempfile.TemporaryDirectory()
os.environ["SORTAI_DATA_FILE"] = os.path.join(DATA_DIR.name, "sortai.json")
from sortai.domain import CATEGORIES, apply_safety_policy, infer_mock
from sortai.server import create_server

class SortAITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server(port=0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        DATA_DIR.cleanup()

    def request(self, path, method="GET", payload=None, token=None):
        headers = {"Content-Type": "application/json"}
        if token: headers["Authorization"] = f"Bearer {token}"
        request = Request(self.base + path, method=method, headers=headers)
        if payload is not None: request.data = json.dumps(payload).encode()
        try:
            with urlopen(request) as response:
                return response.status, json.loads(response.read())
        except Exception as error:
            return error.code, json.loads(error.read())

    def test_taxonomy_and_hazard_policy(self):
        self.assertEqual(CATEGORIES["battery"]["colour"], "red")
        result = apply_safety_policy(infer_mock("swollen-battery.jpg"))
        self.assertTrue(result["reviewRequired"])
        self.assertIn("Do not dismantle", result["warning"])
        unknown = apply_safety_policy(infer_mock("unrecognised.jpg"))
        self.assertEqual(unknown["category"], "unknown")
        self.assertTrue(unknown["reviewRequired"])

    def test_collector_scan_confirmation_and_duplicate_protection(self):
        denied, _ = self.request("/api/scans", "POST", {"mode": "whole-device", "filename": "phone.jpg"}, "demo-recycler")
        self.assertEqual(denied, 401)
        status, scan = self.request("/api/scans", "POST", {"mode": "whole-device", "filename": "phone.jpg"}, "demo-collector")
        self.assertEqual(status, 201)
        self.assertEqual(scan["prediction"]["provider"], "mock")
        status, result = self.request(f"/api/scans/{scan['id']}/confirm", "POST", {"confirmedCategory": "pcb"}, "demo-collector")
        self.assertEqual(status, 201)
        self.assertEqual(result["inventoryItem"]["predictedCategory"], "pcb")
        status, _ = self.request(f"/api/scans/{scan['id']}/confirm", "POST", {"confirmedCategory": "pcb"}, "demo-collector")
        self.assertEqual(status, 409)
        status, inventory = self.request("/api/inventory", token="demo-collector")
        self.assertEqual(status, 200)
        self.assertEqual(len(inventory["items"]), 1)

if __name__ == "__main__": unittest.main()
