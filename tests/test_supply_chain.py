"""Cadeia de suprimentos e identidade do CI/CD (ASI03, ASI04 · docs/03-seguranca.md).

Os testes leem os arquivos do repositório: uma mudança que afrouxa um controle (action por tag,
imagem sem digest, deploy fora do environment) quebra o CI no mesmo PR.
"""

import re
import tomllib
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml

RAIZ = Path(__file__).resolve().parent.parent
WORKFLOWS = sorted((RAIZ / ".github" / "workflows").glob("*.yml"))
SHA_COM_VERSAO = re.compile(r"^[\w.-]+/[\w.-]+(/[\w./-]+)?@[0-9a-f]{40}$")


def _workflow(path: Path) -> dict[str, Any]:
    dados: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return dados


def _steps(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    return [step for job in workflow["jobs"].values() for step in job.get("steps", [])]


def test_existem_workflows() -> None:
    assert {p.name for p in WORKFLOWS} >= {"ci.yml", "cd.yml"}


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_actions_fixadas_por_sha_de_commit(path: Path) -> None:
    for step in _steps(_workflow(path)):
        if "uses" in step:
            assert SHA_COM_VERSAO.match(step["uses"]), f"{path.name}: {step['uses']} sem SHA"
    # O comentário com a versão é o que o Dependabot e quem revisa leem.
    for linha in path.read_text(encoding="utf-8").splitlines():
        if re.search(r"uses: .+@[0-9a-f]{40}", linha):
            assert re.search(r"# v\d", linha), f"{path.name}: falta o comentário da versão: {linha}"


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_checkout_nao_guarda_credencial(path: Path) -> None:
    for step in _steps(_workflow(path)):
        if step.get("uses", "").startswith("actions/checkout@"):
            assert step.get("with", {}).get("persist-credentials") is False


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_permissoes_minimas_por_padrao(path: Path) -> None:
    assert _workflow(path)["permissions"] == {"contents": "read"}


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_nenhum_segredo_alem_do_github_token(path: Path) -> None:
    usados = set(re.findall(r"secrets\.(\w+)", path.read_text(encoding="utf-8")))
    assert usados <= {"GITHUB_TOKEN"}, f"{path.name} usa segredos: {usados - {'GITHUB_TOKEN'}}"


def test_token_oidc_so_no_job_de_deploy_e_no_environment_demo() -> None:
    """D5: o Azure só aceita o token de jobs do environment `demo` (credencial federada)."""
    for path in WORKFLOWS:
        for nome, job in _workflow(path)["jobs"].items():
            if job.get("permissions", {}).get("id-token") == "write":
                assert (path.name, nome) == ("cd.yml", "deploy")
                assert job["environment"] == "demo"


def test_deploy_usa_a_imagem_do_sha_do_commit() -> None:
    deploy = _workflow(RAIZ / ".github" / "workflows" / "cd.yml")["jobs"]["deploy"]
    assert deploy["env"]["TF_VAR_image"].endswith(":${{ github.sha }}")
    assert "--versao" in str(deploy["steps"]) and "GITHUB_SHA" in str(deploy["steps"])


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_uv_do_ci_vem_do_dockerfile(path: Path) -> None:
    """O CI usa o mesmo uv da imagem: a versão é lida do Dockerfile, nunca escrita à mão.

    Achado depois do PR #3: o Dependabot atualizou o uv do Dockerfile, e o CI continuou no antigo.
    """
    for job in _workflow(path)["jobs"].values():
        steps = job.get("steps", [])
        for posicao, step in enumerate(steps):
            if step.get("uses", "").startswith("astral-sh/setup-uv@"):
                assert step["with"]["version"] == "${{ steps.uv.outputs.versao }}"
                anteriores = [s for s in steps[:posicao] if s.get("id") == "uv"]
                assert anteriores and "Dockerfile" in anteriores[0]["run"]


def test_dockerfile_tem_a_versao_do_uv_que_o_ci_le() -> None:
    dockerfile = (RAIZ / "Dockerfile").read_text(encoding="utf-8")
    versoes = re.findall(
        r"^FROM ghcr\.io/astral-sh/uv:([0-9.]+)@sha256:", dockerfile, flags=re.MULTILINE
    )
    assert len(versoes) == 1


def test_imagens_base_por_digest() -> None:
    linhas = (RAIZ / "Dockerfile").read_text(encoding="utf-8").splitlines()
    froms = [linha for linha in linhas if linha.startswith("FROM ")]
    assert froms
    for linha in froms:
        assert re.search(r"@sha256:[0-9a-f]{64}", linha), f"imagem sem digest: {linha}"


def test_container_roda_sem_privilegio() -> None:
    dockerfile = (RAIZ / "Dockerfile").read_text(encoding="utf-8")
    usuarios = re.findall(r"^USER (\S+)$", dockerfile, flags=re.MULTILINE)
    assert usuarios and usuarios[-1] not in {"root", "0"}
    assert "chmod a-s" in dockerfile  # remove os binários setuid/setgid


def _uv_config() -> dict[str, Any]:
    pyproject = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))
    config: dict[str, Any] = pyproject["tool"]["uv"]
    return config


def test_dependencias_com_14_dias_de_publicacao() -> None:
    assert _uv_config()["exclude-newer"] == "14 days"


def test_excecoes_de_seguranca_tem_data_de_remocao_e_nao_venceram() -> None:
    """D9: exceção esquecida trava as atualizações do pacote. Este teste falha quando ela vence."""
    excecoes = _uv_config().get("exclude-newer-package", {})
    texto = (RAIZ / "pyproject.toml").read_text(encoding="utf-8")
    for pacote in excecoes:
        achado = re.search(rf"#\s+{pacote} .*remover em (\d\d)/(\d\d)/(\d{{4}})", texto)
        assert achado, f"exceção de {pacote} sem data de remoção comentada"
        dia, mes, ano = (int(parte) for parte in achado.groups())
        assert date.today() < date(ano, mes, dia), f"exceção de {pacote} venceu: remova-a"


def test_dependabot_cobre_todos_os_ecossistemas_com_espera() -> None:
    config = yaml.safe_load((RAIZ / ".github" / "dependabot.yml").read_text(encoding="utf-8"))
    por_ecossistema = {item["package-ecosystem"]: item for item in config["updates"]}
    assert set(por_ecossistema) == {"uv", "github-actions", "docker", "terraform"}
    for ecossistema in ("github-actions", "terraform"):
        assert por_ecossistema[ecossistema]["cooldown"]["default-days"] >= 14
    # A versão do Python (3.12) só muda por decisão de projeto: o Dependabot propõe só patches.
    ignorados = {
        regra["dependency-name"]: set(regra["update-types"])
        for regra in por_ecossistema["docker"].get("ignore", [])
    }
    assert ignorados.get("python") == {
        "version-update:semver-major",
        "version-update:semver-minor",
    }


def test_credencial_federada_presa_ao_environment() -> None:
    """D5: o subject exige o environment e os IDs imutáveis do dono e do repositório.

    É o formato que o GitHub emite. O formato só com nomes (sem os IDs) faz o Azure recusar o
    login (AADSTS700213, achado no 1º deploy) e não protege contra um repositório recriado com o
    mesmo nome.
    """
    bootstrap = (RAIZ / "infra" / "bootstrap" / "bootstrap.sh").read_text(encoding="utf-8")
    subjects = re.findall(r'^SUBJECT="([^"]+)"$', bootstrap, flags=re.MULTILINE)
    assert subjects == [
        "repo:${GITHUB_REPO%%/*}@${OWNER_ID}/${GITHUB_REPO#*/}@${REPO_ID}"
        ":environment:${GITHUB_ENVIRONMENT}"
    ]


def test_estado_do_terraform_sem_chave_de_acesso() -> None:
    bootstrap = (RAIZ / "infra" / "bootstrap" / "bootstrap.sh").read_text(encoding="utf-8")
    assert "--allow-shared-key-access false" in bootstrap
    assert "--allow-blob-public-access false" in bootstrap
    versions = (RAIZ / "infra" / "versions.tf").read_text(encoding="utf-8")
    assert "use_azuread_auth = true" in versions


def test_cd_nao_registra_provedores_na_assinatura() -> None:
    """D4: a identidade do CD só tem acesso ao grupo do projeto."""
    versions = (RAIZ / "infra" / "versions.tf").read_text(encoding="utf-8")
    assert re.search(r'resource_provider_registrations\s*=\s*"none"', versions)


def test_papeis_do_cd_restritos_ao_projeto() -> None:
    bootstrap = (RAIZ / "infra" / "bootstrap" / "bootstrap.sh").read_text(encoding="utf-8")
    atribuicoes = re.findall(r'^assign "([^"]+)" "\$(\w+)" "\$SP_OBJECT_ID"', bootstrap, re.M)
    assert atribuicoes == [
        ("Contributor", "APP_RG_ID"),
        ("Storage Blob Data Contributor", "STATE_SCOPE"),
    ]
