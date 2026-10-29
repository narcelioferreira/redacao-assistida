# Changelog

Uma entrada por task fechada: o que foi feito, como foi testado e quais problemas apareceram.

## F0 · Esqueleto no ar

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

**Pendente**
- T07 (bootstrap no Azure) e as primeiras execuções do CI e do CD no GitHub.
- Remover as exceções de `certifi` e `filelock` do `pyproject.toml` a partir de 03/11/2026.
