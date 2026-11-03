import time
import uuid

from redacao.ids import timestamp_ms, uuid7


def test_versao_7_e_variante_rfc() -> None:
    identificador = uuid7()

    assert identificador.version == 7
    assert identificador.variant == uuid.RFC_4122


def test_timestamp_e_o_instante_da_criacao() -> None:
    antes = time.time_ns() // 1_000_000
    identificador = uuid7()
    depois = time.time_ns() // 1_000_000

    assert antes <= timestamp_ms(identificador) <= depois


def test_ordem_de_criacao_entre_milissegundos() -> None:
    primeiro = uuid7()
    time.sleep(0.002)
    segundo = uuid7()

    assert primeiro < segundo


def test_nao_se_repete_nem_e_previsivel() -> None:
    """A parte aleatória impede adivinhar o próximo id (BOLA por tentativa)."""
    identificadores = {uuid7() for _ in range(2000)}

    assert len(identificadores) == 2000
