"""Dependências compartilhadas pelas rotas."""

from fastapi import Request

from redacao.config import Settings


def app_settings(request: Request) -> Settings:
    """Settings da app em execução (os testes injetam as suas pela fábrica)."""
    settings: Settings = request.app.state.settings
    return settings
