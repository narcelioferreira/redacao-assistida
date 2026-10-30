"""Configuração lida do ambiente (12-factor).

Nenhum segredo tem valor padrão: o que falta no ambiente desliga o recurso correspondente
(ex.: sem a connection string do App Insights, a telemetria não é exportada).
"""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["local", "ci", "demo"] = "local"
    # Commit da imagem em execução. O CD injeta o SHA, e o smoke test confere que a revisão no ar
    # é a que acabou de ser publicada (decisão D3).
    git_sha: str = "dev"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    applicationinsights_connection_string: SecretStr | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
