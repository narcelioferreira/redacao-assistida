"""Fábrica da API: `uvicorn --factory redacao.api.app:create_app`."""

from collections.abc import Awaitable, Callable
from importlib.metadata import version

from fastapi import FastAPI, Request, Response

from redacao.api import health
from redacao.api.problems import install_problem_handlers
from redacao.config import Settings, get_settings
from redacao.telemetry import configure_telemetry

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    # As respostas vão carregar texto de aluno: nada de cache em proxy ou navegador.
    "Cache-Control": "no-store",
}


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    # /docs e /openapi.json ficam no ar também no demo: o contrato é parte do produto, consumido
    # pelo front e por quem avalia o projeto (decisão D7).
    app = FastAPI(
        title="Redação Assistida API",
        summary="Pré-correção de redações no estilo ENEM, com revisão humana.",
        version=version("redacao-assistida"),
    )
    app.state.settings = settings
    install_problem_handlers(app)

    @app.middleware("http")
    async def security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers.update(SECURITY_HEADERS)
        return response

    app.include_router(health.router)
    configure_telemetry(app, settings)
    return app
