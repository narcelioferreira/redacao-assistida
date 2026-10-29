from fastapi.testclient import TestClient


def test_live_informa_versao_e_ambiente(client: TestClient) -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "versao": "abc1234", "ambiente": "ci"}


def test_ready_responde(client: TestClient) -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_respostas_levam_cabecalhos_de_seguranca(client: TestClient) -> None:
    headers = client.get("/health/live").headers

    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["cache-control"] == "no-store"


def test_contrato_openapi_e_documentacao_publicados(client: TestClient) -> None:
    spec = client.get("/openapi.json")

    assert spec.status_code == 200
    assert spec.json()["info"]["title"] == "Redação Assistida API"
    assert "/health/live" in spec.json()["paths"]
    assert client.get("/docs").status_code == 200
