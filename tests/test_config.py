import pytest
from pydantic import ValidationError

from redacao.config import Settings


def test_le_do_ambiente(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "demo")
    monkeypatch.setenv("GIT_SHA", "f00ba12")
    monkeypatch.delenv("APPLICATIONINSIGHTS_CONNECTION_STRING", raising=False)

    settings = Settings(_env_file=None)

    assert settings.app_env == "demo"
    assert settings.git_sha == "f00ba12"
    assert settings.applicationinsights_connection_string is None


def test_ambiente_desconhecido_e_recusado(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "producao")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_connection_string_nao_aparece_em_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "InstrumentationKey=chave-secreta")

    assert "chave-secreta" not in repr(Settings(_env_file=None))
