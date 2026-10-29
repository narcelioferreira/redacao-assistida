"""Validação por mutação dos controles de segurança (docs/03-seguranca.md).

Para cada mutação de `security/mutacoes.toml`: desliga o controle de propósito (troca um trecho do
arquivo), roda os testes e exige que eles falhem. Se os testes passam com a proteção desligada, o
controle não está comprovado, e o script termina com erro. O arquivo original sempre volta, mesmo
com Ctrl+C.

Uso: python3 scripts/mutacao.py [--relatorio reports/seguranca/mutacao.md] [--id M01 ...]
"""

import argparse
import re

# Só roda os comandos fixos de COMANDOS, sem shell.
import subprocess  # nosec B404
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
COMANDOS = {
    "pytest": ["uv", "run", "--no-sync", "pytest", "-q", "-p", "no:cacheprovider", "--no-cov"],
    "terraform": ["terraform", "-chdir=infra", "test", "-no-color"],
}


@dataclass(frozen=True)
class Mutacao:
    id: str
    controle: str
    descricao: str
    arquivo: str
    de: str
    para: str
    comando: str


@dataclass(frozen=True)
class Resultado:
    mutacao: Mutacao
    # Testes que falharam. Vazio com `erro` falso: a mutação sobreviveu (controle sem teste).
    falhas: tuple[str, ...]
    # A suíte não chegou a rodar (erro de coleta ou de configuração): não comprova o controle.
    erro: bool = False

    @property
    def morta(self) -> bool:
        return bool(self.falhas) and not self.erro


def carregar(path: Path) -> list[Mutacao]:
    dados = tomllib.loads(path.read_text(encoding="utf-8"))
    mutacoes = [Mutacao(**item) for item in dados["mutacao"]]
    ids = [m.id for m in mutacoes]
    if len(ids) != len(set(ids)):
        raise ValueError("ids de mutação repetidos")
    for m in mutacoes:
        if m.comando not in COMANDOS:
            raise ValueError(f"{m.id}: comando desconhecido {m.comando!r}")
    return mutacoes


def testes_que_falharam(comando: str, saida: str) -> tuple[str, ...]:
    if comando == "pytest":
        return tuple(re.findall(r"^FAILED (\S+)", saida, flags=re.MULTILINE))
    return tuple(re.findall(r'^\s+run "([^"]+)"\.\.\. fail', saida, flags=re.MULTILINE))


def aplicar(m: Mutacao) -> Resultado:
    alvo = RAIZ / m.arquivo
    original = alvo.read_bytes()
    texto = original.decode("utf-8")
    if texto.count(m.de) != 1:
        raise ValueError(
            f"{m.id}: o trecho precisa aparecer 1 vez em {m.arquivo}, aparece {texto.count(m.de)}"
        )
    try:
        alvo.write_text(texto.replace(m.de, m.para), encoding="utf-8")
        processo = subprocess.run(  # noqa: S603  # nosec B603
            COMANDOS[m.comando], cwd=RAIZ, capture_output=True, text=True, timeout=600, check=False
        )
        falhas = testes_que_falharam(m.comando, processo.stdout + processo.stderr)
        return Resultado(m, falhas, erro=processo.returncode != 0 and not falhas)
    finally:
        alvo.write_bytes(original)


def relatorio(resultados: list[Resultado]) -> str:
    linhas = [
        "# Validação por mutação",
        "",
        "Gerado por `scripts/mutacao.py`. Cada linha desliga um controle de propósito;",
        "o controle só conta como comprovado se pelo menos um teste falha.",
        "",
        "| ID | Controle | Mutação (proteção desligada) | Testes que falharam | Resultado |",
        "|---|---|---|---|---|",
    ]
    for r in resultados:
        if r.erro:
            situacao = "⚠️ erro (a suíte não rodou)"
        else:
            situacao = "✅ morta" if r.morta else "❌ sobreviveu"
        m = r.mutacao
        testes = "<br>".join(f"`{nome.split('::')[-1]}`" for nome in r.falhas) or "—"
        linhas.append(f"| {m.id} | {m.controle} | {m.descricao} | {testes} | {situacao} |")
    mortas = sum(1 for r in resultados if r.morta)
    linhas += ["", f"**{mortas} de {len(resultados)} mutações mortas.**", ""]
    return "\n".join(linhas)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validação por mutação dos controles.")
    parser.add_argument("--arquivo", type=Path, default=RAIZ / "security" / "mutacoes.toml")
    parser.add_argument("--relatorio", type=Path, help="grava o relatório em Markdown")
    parser.add_argument("--id", action="append", help="roda só estas mutações")
    args = parser.parse_args(argv)

    mutacoes = carregar(args.arquivo)
    if args.id:
        mutacoes = [m for m in mutacoes if m.id in set(args.id)]
    resultados = []
    for m in mutacoes:
        r = aplicar(m)
        situacao = "ERRO" if r.erro else ("morta" if r.morta else "SOBREVIVEU")
        print(f"{m.id} {m.controle}: {situacao} ({len(r.falhas)} testes falharam)")
        resultados.append(r)

    texto = relatorio(resultados)
    if args.relatorio:
        args.relatorio.parent.mkdir(parents=True, exist_ok=True)
        args.relatorio.write_text(texto, encoding="utf-8")
    print(texto)
    return 0 if all(r.morta for r in resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
