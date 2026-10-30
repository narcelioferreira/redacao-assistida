"""Controles em tempo de execução que não têm outro teste (docs/03-seguranca.md)."""

import socket

import pytest
from fastapi.testclient import TestClient
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


def test_trava_de_rede_bloqueia_endereco_externo() -> None:
    """ASI08: um teste que tente falar com a internet (LLM, Azure) falha em vez de gastar."""
    with (
        socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock,
        pytest.raises(RuntimeError, match="rede externa"),
    ):
        sock.connect(("203.0.113.10", 443))  # TEST-NET-3: nunca roteado


def test_trava_de_rede_libera_loopback() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        # Nada escuta na porta 9: a conexão é recusada pelo sistema, não pela trava.
        assert sock.connect_ex(("127.0.0.1", 9)) != 0


@pytest.fixture
def spans(client: TestClient) -> InMemorySpanExporter:
    provider = trace.get_tracer_provider()
    assert isinstance(provider, TracerProvider)
    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return exporter


def test_probes_ficam_fora_do_trace(client: TestClient, spans: InMemorySpanExporter) -> None:
    """D10 · ASI08: as probes rodam a cada poucos segundos e só gerariam custo de ingestão."""
    client.get("/health/live")
    client.get("/health/ready")
    assert spans.get_finished_spans() == ()

    client.get("/nao-existe")
    assert spans.get_finished_spans(), "requisições comuns continuam rastreadas"
