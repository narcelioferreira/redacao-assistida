"""Cada decisão do modelo de dados (T10, D18) comprovada contra o Postgres."""

import uuid

import psycopg
import pytest
from psycopg import errors

from redacao.ids import uuid7

from .conftest import Cadeia, alembic, nova_avaliacao, nova_escola, nova_redacao, novo_usuario

pytestmark = pytest.mark.integration


def test_migration_desce_e_sobe_sem_erro(url_banco: str) -> None:
    alembic("downgrade", "base")
    alembic("upgrade", "head")


def test_id_que_nao_e_uuid7_e_recusado(conn: psycopg.Connection) -> None:
    """Decisão 5: o próprio banco recusa id sequencial ou UUIDv4."""
    with pytest.raises(errors.CheckViolation):
        conn.execute("INSERT INTO escolas (id, nome) VALUES (%s, 'X')", (uuid.uuid4(),))


@pytest.mark.parametrize("nota", [50, 210, -40])
def test_nota_fora_dos_niveis_do_enem_e_recusada(
    conn: psycopg.Connection, cadeia: Cadeia, nota: int
) -> None:
    """Decisão 2: cada competência só aceita 0, 40, 80, 120, 160 ou 200."""
    with pytest.raises(errors.CheckViolation):
        nova_avaliacao(
            conn, cadeia.escola, cadeia.redacao, notas=(nota, 0, 0, 0, 0), prompt_hash="b" * 64
        )


def test_total_e_calculado_pelo_banco(conn: psycopg.Connection, cadeia: Cadeia) -> None:
    total = conn.execute(
        "SELECT total FROM avaliacoes WHERE id = %s", (cadeia.avaliacao,)
    ).fetchone()
    assert total == (640,)


def test_registro_nao_aponta_para_outra_escola(conn: psycopg.Connection, cadeia: Cadeia) -> None:
    """Decisão 1: a turma da escola B não pode ter o professor da escola A."""
    escola_b = nova_escola(conn, "Escola B")
    with pytest.raises(errors.ForeignKeyViolation):
        conn.execute(
            "INSERT INTO turmas (id, escola_id, professor_id, nome, ano_letivo)"
            " VALUES (%s, %s, %s, '1B', 2026)",
            (uuid7(), escola_b, cadeia.professor),
        )


def test_redacao_nao_entra_em_lote_de_outra_escola(
    conn: psycopg.Connection, cadeia: Cadeia
) -> None:
    escola_b = nova_escola(conn, "Escola B")
    with pytest.raises(errors.ForeignKeyViolation):
        nova_redacao(conn, escola_b, cadeia.lote, aluno_ref="intrusa")


def test_mesma_redacao_e_mesmo_prompt_sao_avaliados_uma_vez(
    conn: psycopg.Connection, cadeia: Cadeia
) -> None:
    """Decisão 3 e D13: a base da idempotência do worker."""
    with pytest.raises(errors.UniqueViolation):
        nova_avaliacao(conn, cadeia.escola, cadeia.redacao)  # mesmo prompt_hash da cadeia


def test_prompt_novo_gera_nova_avaliacao(conn: psycopg.Connection, cadeia: Cadeia) -> None:
    nova_avaliacao(conn, cadeia.escola, cadeia.redacao, prompt_hash="c" * 64)
    quantas = conn.execute(
        "SELECT count(*) FROM avaliacoes WHERE redacao_id = %s", (cadeia.redacao,)
    ).fetchone()
    assert quantas == (2,)


def test_avaliacao_nao_aceita_alteracao(conn: psycopg.Connection, cadeia: Cadeia) -> None:
    """Decisão 3: a nota da IA, uma vez gravada, não muda."""
    with pytest.raises(errors.RestrictViolation, match="só recebe inserção"):
        conn.execute("UPDATE avaliacoes SET c1 = 200 WHERE id = %s", (cadeia.avaliacao,))


def test_revisao_nao_aceita_alteracao_e_a_mais_recente_vale(
    conn: psycopg.Connection, cadeia: Cadeia
) -> None:
    """Decisão 4: corrigir a revisão é inserir outra; a mais recente é a nota final."""
    sql = (
        "INSERT INTO revisoes (id, escola_id, redacao_id, avaliacao_id, professor_id,"
        " c1, c2, c3, c4, c5, criado_em) VALUES (%s, %s, %s, %s, %s, %s, 120, 120, 120, 120,"
        " now() + %s * interval '1 second')"
    )
    primeira, segunda = uuid7(), uuid7()
    base = (cadeia.escola, cadeia.redacao, cadeia.avaliacao, cadeia.professor)
    conn.execute(sql, (primeira, *base, 120, 0))
    conn.execute(sql, (segunda, *base, 200, 1))

    with pytest.raises(errors.RestrictViolation):
        conn.execute("UPDATE revisoes SET c1 = 0 WHERE id = %s", (primeira,))
    conn.rollback()


def test_revisao_so_de_avaliacao_da_mesma_redacao(conn: psycopg.Connection, cadeia: Cadeia) -> None:
    outra_redacao = nova_redacao(conn, cadeia.escola, cadeia.lote, aluno_ref="3A-08")
    with pytest.raises(errors.ForeignKeyViolation):
        conn.execute(
            "INSERT INTO revisoes (id, escola_id, redacao_id, avaliacao_id, professor_id,"
            " c1, c2, c3, c4, c5) VALUES (%s, %s, %s, %s, %s, 0, 0, 0, 0, 0)",
            (uuid7(), cadeia.escola, outra_redacao, cadeia.avaliacao, cadeia.professor),
        )


def test_aluno_entrega_uma_redacao_por_lote(conn: psycopg.Connection, cadeia: Cadeia) -> None:
    with pytest.raises(errors.UniqueViolation):
        nova_redacao(conn, cadeia.escola, cadeia.lote, aluno_ref="3A-07")


def test_lote_repetido_com_a_mesma_idempotency_key(
    conn: psycopg.Connection, cadeia: Cadeia
) -> None:
    """HU01: reenviar o mesmo lote por engano não duplica nada."""
    with pytest.raises(errors.UniqueViolation):
        conn.execute(
            "INSERT INTO lotes (id, escola_id, turma_id, proposta_id, criado_por, idempotency_key)"
            " VALUES (%s, %s, %s, %s, %s, 'chave-1')",
            (uuid7(), cadeia.escola, cadeia.turma, cadeia.proposta, cadeia.professor),
        )


def test_anonimizacao_apaga_o_aluno_e_o_texto_e_mantem_as_notas(
    conn: psycopg.Connection, cadeia: Cadeia
) -> None:
    """Decisões 6 e 7: depois da retenção, sobra só a nota, sem dado pessoal."""
    conn.execute("DELETE FROM redacao_textos WHERE redacao_id = %s", (cadeia.redacao,))
    conn.execute("DELETE FROM avaliacao_detalhes WHERE avaliacao_id = %s", (cadeia.avaliacao,))
    conn.execute(
        "UPDATE redacoes SET aluno_ref = NULL, anonimizada_em = now() WHERE id = %s",
        (cadeia.redacao,),
    )

    total = conn.execute(
        "SELECT total FROM avaliacoes WHERE id = %s", (cadeia.avaliacao,)
    ).fetchone()
    assert total == (640,)


def test_aluno_ref_nao_some_sem_registrar_a_anonimizacao(
    conn: psycopg.Connection, cadeia: Cadeia
) -> None:
    with pytest.raises(errors.CheckViolation):
        conn.execute("UPDATE redacoes SET aluno_ref = NULL WHERE id = %s", (cadeia.redacao,))


def test_excluir_o_lote_apaga_tudo_dele(conn: psycopg.Connection, cadeia: Cadeia) -> None:
    """Exclusão a pedido (LGPD): o lote leva redações, textos, avaliações e detalhes."""
    conn.execute("DELETE FROM lotes WHERE id = %s", (cadeia.lote,))

    for tabela in ("redacoes", "redacao_textos", "avaliacoes", "avaliacao_detalhes"):
        restantes = conn.execute(f"SELECT count(*) FROM {tabela}").fetchone()  # noqa: S608
        assert restantes == (0,), tabela


@pytest.mark.parametrize("dias", [0, 731])
def test_retencao_fora_do_limite_e_recusada(conn: psycopg.Connection, dias: int) -> None:
    """Decisão 7: configurável por escola, de 1 a 730 dias (padrão 180)."""
    with pytest.raises(errors.CheckViolation):
        conn.execute(
            "INSERT INTO escolas (id, nome, retencao_dias) VALUES (%s, 'X', %s)", (uuid7(), dias)
        )


def test_retencao_padrao_e_180_dias(conn: psycopg.Connection) -> None:
    escola = nova_escola(conn)
    dias = conn.execute("SELECT retencao_dias FROM escolas WHERE id = %s", (escola,)).fetchone()
    assert dias == (180,)


def test_papel_desconhecido_e_recusado(conn: psycopg.Connection) -> None:
    escola = nova_escola(conn)
    with pytest.raises(errors.CheckViolation):
        novo_usuario(conn, escola, papel="administrador")
