"""Testes contra um Postgres de verdade (marcador `integration`).

Rodam com `make test-integracao` e no CI, que sobe um Postgres 17 com pgvector. A sessão recria o
schema pela própria migration; cada teste roda numa transação desfeita no final.
"""

import os
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import psycopg
import pytest
from alembic import command
from alembic.config import Config

from redacao.ids import uuid7

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


def _url_sqlalchemy() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("defina DATABASE_URL para os testes de integração")
    return url


def alembic(acao: str, alvo: str) -> None:
    config = Config(os.path.join(RAIZ, "alembic.ini"))
    getattr(command, acao)(config, alvo)


@pytest.fixture(scope="session")
def url_banco() -> str:
    url = _url_sqlalchemy()
    alembic("downgrade", "base")
    alembic("upgrade", "head")
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


@pytest.fixture
def conn(url_banco: str) -> Iterator[psycopg.Connection]:
    with psycopg.connect(url_banco) as conexao:
        yield conexao
        conexao.rollback()


@dataclass(frozen=True)
class Cadeia:
    escola: uuid.UUID
    professor: uuid.UUID
    turma: uuid.UUID
    proposta: uuid.UUID
    lote: uuid.UUID
    redacao: uuid.UUID
    avaliacao: uuid.UUID


def nova_escola(conn: psycopg.Connection, nome: str = "Escola A") -> uuid.UUID:
    escola = uuid7()
    conn.execute("INSERT INTO escolas (id, nome) VALUES (%s, %s)", (escola, nome))
    return escola


def novo_usuario(
    conn: psycopg.Connection, escola: uuid.UUID, papel: str = "professor"
) -> uuid.UUID:
    usuario = uuid7()
    conn.execute(
        "INSERT INTO usuarios (id, escola_id, sub, papel) VALUES (%s, %s, %s, %s)",
        (usuario, escola, f"sub-{usuario}", papel),
    )
    return usuario


def nova_redacao(
    conn: psycopg.Connection, escola: uuid.UUID, lote: uuid.UUID, aluno_ref: str = "3A-07"
) -> uuid.UUID:
    redacao = uuid7()
    conn.execute(
        "INSERT INTO redacoes (id, escola_id, lote_id, aluno_ref, expira_em)"
        " VALUES (%s, %s, %s, %s, %s)",
        (redacao, escola, lote, aluno_ref, datetime.now(UTC) + timedelta(days=180)),
    )
    conn.execute(
        "INSERT INTO redacao_textos (redacao_id, escola_id, texto) VALUES (%s, %s, %s)",
        (redacao, escola, "Texto da redação."),
    )
    return redacao


def nova_avaliacao(
    conn: psycopg.Connection,
    escola: uuid.UUID,
    redacao: uuid.UUID,
    *,
    notas: tuple[int, int, int, int, int] = (160, 120, 160, 120, 80),
    prompt_hash: str = "a" * 64,
) -> uuid.UUID:
    avaliacao = uuid7()
    conn.execute(
        "INSERT INTO avaliacoes (id, escola_id, redacao_id, prompt_hash, modelo,"
        " c1, c2, c3, c4, c5, tokens_entrada, tokens_saida, custo_usd, latencia_ms)"
        " VALUES (%s, %s, %s, %s, 'modelo-teste', %s, %s, %s, %s, %s, 4000, 800, 0.003, 2100)",
        (avaliacao, escola, redacao, prompt_hash, *notas),
    )
    conn.execute(
        "INSERT INTO avaliacao_detalhes (avaliacao_id, escola_id, justificativas, trechos)"
        " VALUES (%s, %s, '{}', '[]')",
        (avaliacao, escola),
    )
    return avaliacao


@pytest.fixture
def cadeia(conn: psycopg.Connection) -> Cadeia:
    """Uma escola com professor, turma, proposta, lote, redação e avaliação."""
    escola = nova_escola(conn)
    professor = novo_usuario(conn, escola)
    turma, proposta, lote = uuid7(), uuid7(), uuid7()
    conn.execute(
        "INSERT INTO turmas (id, escola_id, professor_id, nome, ano_letivo)"
        " VALUES (%s, %s, %s, '3A', 2026)",
        (turma, escola, professor),
    )
    conn.execute(
        "INSERT INTO propostas (id, escola_id, criado_por, titulo) VALUES (%s, %s, %s, 'Tema')",
        (proposta, escola, professor),
    )
    conn.execute(
        "INSERT INTO lotes (id, escola_id, turma_id, proposta_id, criado_por, idempotency_key)"
        " VALUES (%s, %s, %s, %s, %s, 'chave-1')",
        (lote, escola, turma, proposta, professor),
    )
    redacao = nova_redacao(conn, escola, lote)
    avaliacao = nova_avaliacao(conn, escola, redacao)
    return Cadeia(escola, professor, turma, proposta, lote, redacao, avaliacao)
