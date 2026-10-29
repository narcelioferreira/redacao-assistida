import socket
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from redacao.api.app import create_app
from redacao.config import Settings

_LOOPBACK = {"127.0.0.1", "::1", "localhost"}


@pytest.fixture(autouse=True)
def _sem_rede_externa(monkeypatch: pytest.MonkeyPatch) -> None:
    """Trava de rede: nenhum teste fala com a internet (LLM, Azure, APIs de terceiros).

    Loopback continua liberado para o Postgres local e servidores de teste. Não remova: é ela que
    garante que um teste nunca gasta token nem depende de serviço externo.
    """
    connect = socket.socket.connect
    connect_ex = socket.socket.connect_ex

    def _check(sock: socket.socket, address: Any) -> None:
        if sock.family in (socket.AF_INET, socket.AF_INET6) and address[0] not in _LOOPBACK:
            raise RuntimeError(f"teste tentou acessar a rede externa: {address[0]}")

    def guarded_connect(sock: socket.socket, address: Any) -> None:
        _check(sock, address)
        connect(sock, address)

    def guarded_connect_ex(sock: socket.socket, address: Any) -> int:
        _check(sock, address)
        return connect_ex(sock, address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)


@pytest.fixture
def settings() -> Settings:
    # _env_file=None: o .env de quem roda os testes não vaza para dentro deles.
    return Settings(
        _env_file=None, app_env="ci", git_sha="abc1234", applicationinsights_connection_string=None
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings), raise_server_exceptions=False) as test_client:
        yield test_client
