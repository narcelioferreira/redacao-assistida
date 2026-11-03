import pytest

# scripts/mutacao.py (pythonpath no pyproject). Alias: um nome que começa com "test" seria coletado
# pelo pytest como se fosse um teste.
from mutacao import COMANDOS, Mutacao, trocar
from mutacao import testes_que_falharam as falhas_reconhecidas


def _mutacao(de: str, para: str, *, regex: bool = False) -> Mutacao:
    return Mutacao(
        id="MX",
        controle="ASI04",
        descricao="teste",
        arquivo="Dockerfile",
        de=de,
        para=para,
        comando="pytest",
        regex=regex,
    )


def test_trecho_literal_e_trocado() -> None:
    assert trocar("USER 10001\n", _mutacao("USER 10001", "USER root")) == "USER root\n"


def test_regex_sobrevive_a_atualizacao_de_versao() -> None:
    """Achado no PR #3: a mutação com o digest literal quebrava a cada PR do Dependabot."""
    m = _mutacao(
        r"(FROM ghcr\.io/astral-sh/uv:[\d.]+)@sha256:[0-9a-f]{64}( AS uv)", r"\1\2", regex=True
    )
    for versao in ("0.13.1", "0.13.6"):
        texto = f"FROM ghcr.io/astral-sh/uv:{versao}@sha256:{'a' * 64} AS uv\n"
        assert trocar(texto, m) == f"FROM ghcr.io/astral-sh/uv:{versao} AS uv\n"


@pytest.mark.parametrize("texto", ["nada aqui\n", "USER 10001\nUSER 10001\n"])
def test_trecho_ausente_ou_repetido_e_recusado(texto: str) -> None:
    """Sem ocorrência única, a mutação não sabe o que desligar: falha alto em vez de passar."""
    with pytest.raises(ValueError, match="1 vez"):
        trocar(texto, _mutacao("USER 10001", "USER root"))


SAIDA_PYTEST = "FAILED tests/x.py::test_a - assert 1\nFAILED tests/y.py::test_b\n1 passed"
SAIDA_TERRAFORM = '  run "tag_movel"... fail\n  run "escala"... pass\n'


@pytest.mark.parametrize("comando", sorted(COMANDOS))
def test_cada_comando_tem_a_saida_reconhecida(comando: str) -> None:
    """Todo comando de mutação precisa ter as falhas reconhecidas (achado na T10)."""
    saida = SAIDA_TERRAFORM if comando == "terraform" else SAIDA_PYTEST
    assert falhas_reconhecidas(comando, saida)


def test_falhas_do_pytest_e_do_terraform() -> None:
    assert falhas_reconhecidas("pytest", SAIDA_PYTEST) == (
        "tests/x.py::test_a",
        "tests/y.py::test_b",
    )
    assert falhas_reconhecidas("terraform", SAIDA_TERRAFORM) == ("tag_movel",)
