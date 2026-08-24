import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from extracao_clinica_sasi.server import criar_servidor


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = criar_servidor("127.0.0.1", 0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def test_healthz(self):
        with urlopen(f"http://127.0.0.1:{self.port}/healthz", timeout=2) as response:
            body = json.load(response)
        self.assertEqual(response.status, 200)
        self.assertEqual(body, {"status": "ok", "service": "extracao-clinica-sasi"})

    def test_compile(self):
        payload = {
            "leito": "01",
            "iniciais": "ABC",
            "vitais": {"PAM": [70, 60]},
            "ganhos": [{"nome": "dieta", "ml": 500}],
            "perdas": [{"nome": "diurese", "ml": 400}],
        }
        request = Request(
            f"http://127.0.0.1:{self.port}/v1/compile",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=2) as response:
            body = json.load(response)
        self.assertEqual(response.status, 200)
        self.assertIn("BH: +100 ml", body["texto_clinico"])

    def test_rejects_unknown_path(self):
        request = Request(
            f"http://127.0.0.1:{self.port}/v1/unknown",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(HTTPError) as caught:
            urlopen(request, timeout=2)
        self.assertEqual(caught.exception.code, 404)

    def test_rejects_malformed_json(self):
        request = Request(
            f"http://127.0.0.1:{self.port}/v1/compile",
            data=b"{",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(HTTPError) as caught:
            urlopen(request, timeout=2)
        self.assertEqual(caught.exception.code, 400)

    def test_rejects_payload_without_bed(self):
        request = Request(
            f"http://127.0.0.1:{self.port}/v1/compile",
            data=b'{"vitais": {}}',
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(HTTPError) as caught:
            urlopen(request, timeout=2)
        self.assertEqual(caught.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
