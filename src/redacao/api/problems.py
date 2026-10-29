"""Erros no formato Problem Details (RFC 9457), com o trace_id da requisição (decisão D8).

Um formato único para todos os erros simplifica o front (um só tratador) e a investigação: o
trace_id que o usuário vê é o que se procura no App Insights.
"""

from collections.abc import Mapping
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from redacao.telemetry import current_trace_id

PROBLEM_JSON = "application/problem+json"

TITLES = {
    400: "Requisição inválida",
    401: "Não autenticado",
    403: "Acesso negado",
    404: "Recurso não encontrado",
    405: "Método não permitido",
    409: "Conflito",
    413: "Conteúdo grande demais",
    415: "Tipo de conteúdo não suportado",
    422: "Dados inválidos",
    429: "Limite de uso atingido",
    500: "Erro interno",
    503: "Serviço indisponível",
}


class CampoInvalido(BaseModel):
    campo: str
    mensagem: str
    tipo: str


class Problem(BaseModel):
    """Corpo de erro. `trace_id` e `erros` são membros de extensão previstos na RFC 9457."""

    type: str = "about:blank"
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None
    trace_id: str | None = None
    erros: list[CampoInvalido] | None = None


def problem_response(
    request: Request,
    status: int,
    detail: str | None = None,
    *,
    erros: list[CampoInvalido] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    problem = Problem(
        title=TITLES.get(status) or HTTPStatus(status).phrase,
        status=status,
        detail=detail,
        instance=request.url.path,
        trace_id=current_trace_id(),
        erros=erros,
    )
    return JSONResponse(
        problem.model_dump(exclude_none=True),
        status_code=status,
        media_type=PROBLEM_JSON,
        headers=headers,
    )


async def _http_error(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):  # pragma: no cover - registrado só para ela
        raise exc
    # O detalhe genérico do Starlette ("Not Found") só repetiria o título.
    generic = HTTPStatus(exc.status_code).phrase
    detail = exc.detail if isinstance(exc.detail, str) and exc.detail != generic else None
    return problem_response(request, exc.status_code, detail, headers=exc.headers)


async def _validation_error(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):  # pragma: no cover - registrado só para ela
        raise exc
    # O valor enviado (`input`) não volta na resposta: pode ser texto de aluno ou dado pessoal.
    erros = [
        CampoInvalido(
            campo=".".join(str(part) for part in error["loc"]),
            mensagem=error["msg"],
            tipo=error["type"],
        )
        for error in exc.errors()
    ]
    return problem_response(request, 422, "Confira os campos listados em `erros`.", erros=erros)


async def _unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    # Nada do erro interno vai para o cliente. A exceção continua subindo depois desta resposta
    # e fica registrada no span da requisição, que o trace_id identifica.
    return problem_response(request, 500)


def install_problem_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(Exception, _unexpected_error)
