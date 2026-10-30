import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
import smoke  # scripts/smoke.py (pythonpath no pyproject)


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        body = json.dumps({"status": "ok", "versao": "abc1234"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:  # silencia o log do servidor de teste
        pass


@pytest.fixture
def api_no_ar() -> Iterator[str]:
    server = HTTPServer(("127.0.0.1", 0), _HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def test_aceita_a_versao_esperada(api_no_ar: str) -> None:
    assert smoke.wait_for_version(api_no_ar, "abc1234", timeout_s=2)


def test_recusa_quando_a_revisao_no_ar_e_outra(api_no_ar: str) -> None:
    assert not smoke.wait_for_version(api_no_ar, "outro-sha", timeout_s=0.3, interval_s=0.1)


def test_falha_quando_ninguem_responde() -> None:
    assert not smoke.wait_for_version("http://127.0.0.1:9", None, timeout_s=0.3, interval_s=0.1)


def test_recusa_esquema_que_nao_e_http() -> None:
    with pytest.raises(ValueError, match="http"):
        smoke.wait_for_version("file:///etc/passwd", None, timeout_s=1)
