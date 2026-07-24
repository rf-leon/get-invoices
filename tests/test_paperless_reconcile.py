from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


SCRIPT = Path(__file__).parents[1] / "scripts" / "paperless-reconcile.py"


class PaperlessHandler(BaseHTTPRequestHandler):
    documents = {
        42: {
            "id": 42,
            "title": "Placetel Rechnung Nr. INV-42",
            "content": "Placetel Rechnungsnummer INV-42",
            "tags": [101, 150, 260],
            "correspondent": 1,
            "document_type": None,
        }
    }

    def log_message(self, *_args) -> None:
        return

    def send_json(self, payload, status=200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/documents/":
            query = parse_qs(parsed.query).get("query", [""])[0]
            results = [
                document
                for document in self.documents.values()
                if query in document["title"] or query in document["content"]
            ]
            self.send_json({"count": len(results), "results": results})
            return

        if parsed.path.startswith("/api/documents/"):
            document_id = int(parsed.path.rstrip("/").split("/")[-1])
            self.send_json(self.documents[document_id])
            return

        self.send_json({"detail": "not found"}, status=404)

    def do_PATCH(self) -> None:
        parsed = urlparse(self.path)
        document_id = int(parsed.path.rstrip("/").split("/")[-1])
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length))
        self.documents[document_id].update(payload)
        self.send_json(self.documents[document_id])


class PaperlessReconcileTest(unittest.TestCase):
    def setUp(self) -> None:
        PaperlessHandler.documents[42]["tags"] = [101, 150, 260]
        PaperlessHandler.documents[42]["correspondent"] = 1
        PaperlessHandler.documents[42]["document_type"] = None
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), PaperlessHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def run_helper(self, *arguments: str) -> dict:
        env = {
            **os.environ,
            "PAPERLESS_URL": f"http://127.0.0.1:{self.server.server_port}",
            "PAPERLESS_TOKEN": "test-token",
        }
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *arguments],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        return json.loads(result.stdout)

    def test_dry_run_preserves_unrelated_tags(self) -> None:
        result = self.run_helper(
            "--document-id",
            "42",
            "--ensure-tag",
            "101",
            "--ensure-tag",
            "102",
            "--remove-tag",
            "150",
            "--ensure-correspondent",
            "300",
            "--ensure-document-type",
            "400",
            "--dry-run",
        )
        self.assertEqual(result["old_tags"], [101, 150, 260])
        self.assertEqual(result["desired_tags"], [101, 102, 260])
        self.assertEqual(result["desired_correspondent"], 300)
        self.assertEqual(result["desired_document_type"], 400)
        self.assertEqual(PaperlessHandler.documents[42]["tags"], [101, 150, 260])
        self.assertEqual(PaperlessHandler.documents[42]["correspondent"], 1)
        self.assertIsNone(PaperlessHandler.documents[42]["document_type"])

    def test_invoice_lookup_patches_and_verifies(self) -> None:
        result = self.run_helper(
            "--provider",
            "placetel",
            "--invoice-number",
            "INV-42",
            "--ensure-tag",
            "101",
            "--ensure-tag",
            "102",
            "--remove-tag",
            "150",
            "--ensure-correspondent",
            "300",
            "--ensure-document-type",
            "400",
        )
        self.assertTrue(result["changed"])
        self.assertEqual(result["verified_tags"], [101, 102, 260])
        self.assertEqual(result["verified_correspondent"], 300)
        self.assertEqual(result["verified_document_type"], 400)
        self.assertEqual(PaperlessHandler.documents[42]["tags"], [101, 102, 260])
        self.assertEqual(PaperlessHandler.documents[42]["correspondent"], 300)
        self.assertEqual(PaperlessHandler.documents[42]["document_type"], 400)


if __name__ == "__main__":
    unittest.main()
