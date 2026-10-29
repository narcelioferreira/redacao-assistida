import re
from collections.abc import Iterator

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from redacao.api.app import create_app
from redacao.config import Settings

TRACE_ID = re.compile(r"^[0-9a-f]{32}$")


@pytest.fixture
def client_com_rotas_de_teste(settings: Settings) -> Iterator[TestClient]:
    app = create_app(settings)

    @app.get("/_teste/numero")
    def numero(n: int) -> dict[str, int]:
        return {"n": n}

    @app.get("/_teste/conflito")
    def conflito() -> None:
        raise HTTPException(status_code=409, detail="Este lote já foi enviado.")

    @app.get("/_teste/quebra")
    def quebra() -> None:
        raise RuntimeError("detalhe interno: senha=hunter2")

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def test_rota_inexistente_vira_problem_details(client: TestClient) -> None:
    response = client.get("/nao-existe")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["title"] == "Recurso não encontrado"
    assert body["status"] == 404
    assert body["instance"] == "/nao-existe"
    assert TRACE_ID.match(body["trace_id"])
    assert "detail" not in body  # o "Not Found" genérico do Starlette não é repetido


def test_metodo_nao_permitido(client: TestClient) -> None:
    response = client.post("/health/live")

    assert response.status_code == 405
    assert response.json()["title"] == "Método não permitido"
    assert "GET" in response.headers["allow"]


def test_http_exception_mantem_o_detalhe(client_com_rotas_de_teste: TestClient) -> None:
    response = client_com_rotas_de_teste.get("/_teste/conflito")

    assert response.status_code == 409
    assert response.json()["title"] == "Conflito"
    assert response.json()["detail"] == "Este lote já foi enviado."


def test_validacao_lista_os_campos_sem_ecoar_o_valor(
    client_com_rotas_de_teste: TestClient,
) -> None:
    response = client_com_rotas_de_teste.get("/_teste/numero", params={"n": "Maria Silva"})

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["erros"][0]["campo"] == "query.n"
    assert body["erros"][0]["tipo"] == "int_parsing"
    assert "Maria Silva" not in response.text  # o valor enviado pode ser dado pessoal


def test_erro_inesperado_nao_vaza_detalhe_interno(client_com_rotas_de_teste: TestClient) -> None:
    response = client_com_rotas_de_teste.get("/_teste/quebra")

    assert response.status_code == 500
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["title"] == "Erro interno"
    assert "hunter2" not in response.text
    assert TRACE_ID.match(response.json()["trace_id"])
