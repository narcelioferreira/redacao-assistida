"""Probes do Container Apps.

- /health/live  : o processo responde (liveness).
- /health/ready : pronto para receber tráfego (readiness). Na F1 passa a conferir o Postgres.

Nenhuma das duas chama o LLM: uma instabilidade do provedor tiraria todas as réplicas do ar.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from redacao.api.deps import app_settings
from redacao.config import Settings

router = APIRouter(prefix="/health", tags=["saúde"])


class Saude(BaseModel):
    status: Literal["ok"] = "ok"
    versao: str
    ambiente: str


SettingsDep = Annotated[Settings, Depends(app_settings)]


@router.get("/live", summary="O processo responde")
def live(settings: SettingsDep) -> Saude:
    return Saude(versao=settings.git_sha, ambiente=settings.app_env)


@router.get("/ready", summary="Pronto para receber tráfego")
def ready(settings: SettingsDep) -> Saude:
    return Saude(versao=settings.git_sha, ambiente=settings.app_env)
