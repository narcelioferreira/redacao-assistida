# Changelog

Uma entrada por task fechada: o que foi feito, como foi testado e quais problemas apareceram.

## F0 · Esqueleto no ar

### T07 · Bootstrap do Azure (em andamento) · 30/10/2026 · 👥

**Feito**
- Conta Azure criada e bootstrap executado no Cloud Shell pelo Narcelio: grupos, estado remoto,
  identidade OIDC e papéis. Variáveis cadastradas no GitHub.

**Problemas encontrados**
- 1º CD: deploy pulado, porque `AZURE_DEPLOY_ENABLED` não tinha sido cadastrada. O tradutor do
  navegador também alterou o valor de `TFSTATE_STORAGE_ACCOUNT` na tela; corrigido à mão.
- 2º CD: o `terraform init` falhou com `AADSTS700213`. O GitHub emite o *subject* do token OIDC com os
  IDs imutáveis do dono e do repositório (`repo:narcelioferreira@219730014/redacao-assistida@1438882016:environment:demo`),
  e o bootstrap cadastrava o formato só com nomes. Corrigido: o bootstrap busca os IDs na API do
  GitHub e corrige uma credencial antiga no lugar. Teste atualizado e nova mutação (M24).

### TS01 · Fundação de segurança · 29/10/2026 · 🤖 Claude

**Feito**
- `docs/03-seguranca.md`: modelo de ameaças com OWASP ASI01–ASI10, AST e API Security Top 10, LGPD
  e riscos residuais, no formato do Lead Qualifier.
- Ciclo de 5 etapas por task (código, segurança, teste, validação e próxima tarefa) na política
  `security/Skill_SecurityFN.md` e na skill `.claude/skills/securityfn`, com perfis de proveniência,
  regras de confirmação, gate e formato de relatório.
- Gate ampliado: bandit, detect-secrets e zizmor no `make check`; `terraform test` com provider
  simulado; validação por mutação (`scripts/mutacao.py`, `security/mutacoes.toml`) no CI.
- Testes dos controles da F0: cadeia de suprimentos e identidade do CI/CD (20), trava de rede e probes
  fora do trace (3) e 6 testes do Terraform.
- Plano reorganizado: coluna de segurança por task e o ciclo no lugar da "definição de pronto".
- Relatório do gate da F0: `reports/seguranca/F0.md`, no formato obrigatório da fundamentação.
- Política central: a fundamentação original da Skill_SecurityFN ficou como Parte I, sem alterações;
  a Parte II aplica a política ao projeto e registra a exceção formal às regras de confirmação.

**Testado**
- `make check`: 39 testes, 97% de cobertura, bandit, detect-secrets, pip-audit e zizmor sem achados.
- `make tf-check`: 6 de 6 testes do Terraform. `make mutacao`: 23 de 23 mutações mortas.

**Problemas encontrados**
- A primeira versão do script de mutação contava erro de execução como falha de teste. Isso escondeu
  que a M02 gerava um erro de sintaxe (o TOML preservou as barras invertidas). Agora erro e falha são
  separados, e o relatório lista os testes que falharam.
- detect-secrets marcou o nome do secret do App Insights no Terraform e no teste (falsos positivos,
  marcados com `pragma: allowlist secret`).

### T01–T06 e T08 (código) · 29/10/2026 · 🤖 Claude

**Feito**
- Estrutura do repositório com uv, ruff, mypy strict, pytest com trava de rede e Makefile.
- API mínima: `/health/live` (versão e ambiente), `/health/ready`, erros RFC 9457 com `trace_id`,
  cabeçalhos de segurança e OpenAPI em `/docs`.
- Telemetria OpenTelemetry com exportação para o App Insights quando há connection string.
- Dockerfile multi-stage com imagens por digest, usuário sem privilégio e sem binários setuid.
- CI (lint, tipos, testes, pip-audit, gitleaks, build e smoke test da imagem, validação do
  Terraform) e CD (imagem no GHCR com SBOM e proveniência; deploy por Terraform com OIDC, ligado só
  depois do bootstrap).
- Terraform do ambiente demo: Log Analytics, App Insights, ambiente e Container App da API, orçamento.
- Bootstrap do Azure e guia de deploy (`docs/deploy-azure.md`).

**Testado**
- `make check`: ruff, mypy strict, 16 testes com 97% de cobertura, pip-audit sem vulnerabilidades.
- Imagem construída e executada só leitura e sem capabilities: smoke test OK, usuário 10001, nenhum
  binário setuid, healthcheck `healthy`, 404 em Problem Details com `trace_id`.
- Terraform 1.16.6 com azurerm 5.10.0: `fmt`, `init` e `validate`. As expressões do orçamento e da
  validação da imagem foram conferidas no `terraform console`.
- Workflows: actionlint e zizmor (persona pedantic) sem achados; `dependabot.yml` validado contra o
  schema.
- Bootstrap: `bash -n` e shellcheck. **Ainda não executado contra o Azure** (depende da conta, T07).

**Problemas encontrados**
- Sem `logs_destination`, o ambiente do Container Apps só transmite logs ao vivo, e nada chega ao Log
  Analytics. Corrigido com `logs_destination = "log-analytics"`.
- Por padrão, o provider azurerm registra provedores de recurso na assinatura, o que exige uma
  permissão que a identidade do CD não tem (D4). Desligado no provider; o bootstrap faz o registro.
- O orçamento do Azure só aceita início no dia 1 do mês, e o valor é na moeda da conta de cobrança:
  data calculada com `plantimestamp()` e `ignore_changes`, valor padrão 50 (BRL).
- O Starlette passou a pedir `httpx2` no TestClient (aviso de depreciação): trocado na dependência de
  desenvolvimento.
- A regra dos 14 dias (D9) escolheu Terraform 1.16.6 (a 1.17.1 saiu ontem), azurerm 5.10.0 (a 5.12.0
  saiu hoje), uv 0.13.1, `setup-uv` v10.3.0 e `login-action` v4.6.0.
- A mesma regra segurou duas versões vulneráveis: `certifi` 2026.7.22 (PYSEC-2026-4320; vai para
  produção pelo `requests` do SDK do Azure) e `filelock` 4.2.0 (17 CVEs; só no grupo dev, pelo
  `pip-audit`). As correções tinham menos de 14 dias. Entraram por exceção datada
  (`exclude-newer-package`), que deve ser removida em 31/10 (filelock) e 03/11 (certifi). O critério
  foi registrado na D9.

**Validado no GitHub (30/10/2026)**
- CI do PR #1 com os 5 jobs verdes, nos commits assinados (Verified) e sem coautoria.
- `main` protegida por ruleset (sem exclusão nem force push, commits assinados, PR com squash, 5 checks
  obrigatórios, sem bypass) e environment `demo` restrito à `main`. Configurados pelo Narcelio.
- Gate da F0: **Aprovado com ressalvas** (`reports/seguranca/F0.md`).

**Pendente**
- T07 (bootstrap no Azure) e a primeira execução do CD.
- Remover as exceções de `certifi` e `filelock` do `pyproject.toml` a partir de 03/11/2026.
