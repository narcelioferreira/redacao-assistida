# Redação Assistida

![CI](https://github.com/narcelioferreira/redacao-assistida/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.12-blue)
![Azure](https://img.shields.io/badge/Azure-Container%20Apps-0078D4)

Pré-correção de redações no estilo ENEM. O professor envia um lote de redações; o sistema avalia
cada uma nas 5 competências, com justificativa e trechos citados; o professor revisa e dá a nota
final. **A IA sugere, o professor decide.**

É um projeto de portfólio de Engenharia de IA no formato de uma PoC corporativa: lote de documentos →
fila → LLM avalia com rubrica → código valida → humano revisa → métricas. Troque "redação" por
contrato, sinistro ou currículo e a arquitetura é a mesma.

## Status

| Fase | Entrega | Situação |
|---|---|---|
| F0 · Esqueleto no ar | API mínima, Docker, CI, imagem no GHCR, Terraform, CD com OIDC | ✅ No ar: [ca-redacao-api.redwater-00b3bec9.brazilsouth.azurecontainerapps.io](https://ca-redacao-api.redwater-00b3bec9.brazilsouth.azurecontainerapps.io/docs) |
| F1 · Uma redação | Login, modelo de dados, avaliação síncrona com Azure OpenAI | ⏳ |
| F2 · Lotes por fila | Service Bus, worker com escala por fila, idempotência, DLQ, progresso em tempo real | ⏳ |
| F3 · Qualidade | Avaliação contra corretores humanos (corpus Essay-BR), guardrails, experimentos | ⏳ |
| F4 · Front e revisão | SPA mínima, revisão do professor, concordância IA × professor | ⏳ |
| F5 · Opcional | Assistente da turma com function calling e busca semântica | ⏳ |

Plano completo, com dono, estimativa e critério de aceite de cada task:
[docs/02-plano-de-tasks.md](docs/02-plano-de-tasks.md).

## Arquitetura (alvo)

```
 Professor ── SPA React+TS (Static Web Apps) ── login OIDC ──► Entra External ID
                    │ Bearer JWT
                    ▼
 ┌─────────────────────────────────┐
 │ API · FastAPI (Container Apps)  │──► PostgreSQL Flexible (RLS por escola)
 │ JWT · papéis · cotas · 202      │
 └──────────────┬──────────────────┘
                │ 1 mensagem por redação (só o id + traceparent)
                ▼
       Service Bus · fila "redacoes" + DLQ
                │ KEDA escala pelo tamanho da fila (0 → N → 0)
                ▼
 ┌─────────────────────────────────┐
 │ Worker (mesma imagem)           │──► Azure OpenAI (Managed Identity)
 │ checa → avalia → valida → grava │──► PostgreSQL
 └─────────────────────────────────┘
 Transversal: App Insights (OpenTelemetry) · Terraform · GitHub Actions (OIDC) · orçamento
```

Já existe (F0): a API, o Container Apps com escala a zero, Log Analytics, App Insights, o orçamento
com alertas e o pipeline de CI/CD. O resto entra fase a fase. Detalhes em
[docs/01-arquitetura.md](docs/01-arquitetura.md).

## Como rodar

Requisitos: [uv](https://docs.astral.sh/uv/) e Docker. Terraform (1.16+) só para validar a infra.

```bash
make install    # dependências exatamente como no uv.lock
make check      # lint, tipos (mypy strict), testes com cobertura e vulnerabilidades conhecidas
make run        # API em http://127.0.0.1:8000 (documentação em /docs)
make docker-run # a mesma API na imagem de produção, só leitura e sem capabilities
make smoke      # o smoke test do CD contra a API local
make tf-check   # formato, validação e testes do Terraform, sem credencial do Azure
make mutacao    # desliga cada controle de segurança e exige que os testes falhem
```

## API (F0)

| Rota | O que faz |
|---|---|
| `GET /health/live` | O processo responde; informa a versão (SHA do commit) e o ambiente |
| `GET /health/ready` | Pronto para receber tráfego (a partir da F1, confere o Postgres) |
| `GET /docs` | Documentação interativa do contrato (OpenAPI) |

Todo erro sai no formato Problem Details (RFC 9457), com o `trace_id` que se procura no App Insights:

```json
{
  "type": "about:blank",
  "title": "Recurso não encontrado",
  "status": 404,
  "instance": "/nao-existe",
  "trace_id": "15155a12cd43f181cc6126efd6c04f1b"
}
```

## Segurança

Os controles seguem o OWASP Top 10 for Agentic Applications 2026 (ASI01–ASI10), com mapeamento
complementar ao OWASP Agentic Skills Top 10 (AST, em revisão pública) e ao OWASP API Security Top 10.
Cada controle implementado tem um teste que o comprova e foi validado por mutação: com a proteção
desligada de propósito, os testes falham. O CI roda as mutações a cada PR
(**25 de 25 mortas**, [relatório](reports/seguranca/mutacao.md)).

O modelo de ameaças, os testes por controle, os mapeamentos complementares e os riscos residuais estão
em [docs/03-seguranca.md](docs/03-seguranca.md).

| Risco (OWASP) | Controles implementados (F0) | Planejado |
|---|---|---|
| ASI01 · Goal Hijack (injeção de prompt) · AST05 | — (a F0 não tem LLM) | Redação em bloco `<redacao_{nonce}>`; saída só com níveis válidos; detector determinístico que marca para revisão humana sem zerar a nota; conjunto adversarial medido (T17, T18, T33, T34) |
| ASI02 · Tool Misuse · AST03 | O LLM não terá ferramentas na F1–F4 (D12) | Ferramentas só de leitura com escopo vindo do código (F5) |
| ASI03 · Identity & Privilege | Deploy por OIDC sem segredo, com credencial presa ao environment `demo`; identidade do CD só no grupo do projeto; estado do Terraform sem chave de acesso; container sem root e sem setuid; `SecretStr`; erros sem detalhe interno | Managed Identity no Azure OpenAI e no Postgres; JWT; papéis, escopo por escola e RLS (T11, T13, T14) |
| ASI04 · Supply Chain · AST02, AST07 | `uv.lock` com hashes; versões com 14+ dias; actions por SHA, imagens por digest, Dependabot com espera; deploy só pela tag do SHA; SBOM e proveniência; ruff, bandit, detect-secrets, gitleaks, pip-audit e zizmor no gate | Prompts com SHA-256 e recusa de iniciar se divergir; oasdiff no contrato (T16, T19) |
| ASI05 · Code Execution · AST04 | Nada executa entrada do usuário | Saída do LLM só como JSON validado; `.docx` lido com limite e sem macros (T18, T22) |
| ASI06 · Context Poisoning | — | Rubrica imutável por versão; trechos recuperados passam pelo detector (T16, T51) |
| ASI07 · Inter-Agent Communication | — | Mensagem da fila só com id e `traceparent`, validada; Service Bus por Managed Identity (T21, T23) |
| ASI08 · Cascading Failures · AST08 | Health sem dependência externa; escala a zero com teto de réplicas; Log Analytics com teto diário; orçamento com alertas; trava de rede nos testes | Retries limitados, DLQ, cota por escola, orçamento de tokens e chave para desligar o LLM (T15, T23, T25) |
| ASI09 · Human Trust | — | Nota final só depois da revisão do professor; trechos citados conferidos em código; saída saneada (T33, T40, T41) |
| ASI10 · Rogue Agents · AST09 | Pipeline com etapas fixas (D12) | Avaliações só por inserção, com modelo e hash do prompt; teto de iterações no loop da F5 (T10, T50) |

**Dados pessoais (LGPD):** os erros não ecoam o valor enviado nem detalhes internos. Planejado: sem
nome de aluno, PII mascarada antes do LLM, `.docx` original descartado, texto fora de logs e filas,
retenção com prazo e exclusão a pedido.

**Riscos residuais conhecidos:** a API do demo é pública e sem login na F0 (só expõe `/health` e
`/docs`, sem dados); confiança na plataforma do GitHub (Actions, OIDC, GHCR); o bootstrap roda com
privilégio de dono da assinatura. Detalhes no documento 03.

**Gate no CI:** ruff (com regras de segurança), mypy strict, pytest com cobertura, bandit,
detect-secrets, gitleaks, pip-audit, zizmor, `terraform test` e validação por mutação.

**Processo:** toda task passa por 5 etapas (código, segurança, teste, validação e próxima tarefa),
definidas em [security/Skill_SecurityFN.md](security/Skill_SecurityFN.md), com relatório e decisão do
gate em [reports/seguranca/](reports/seguranca/).

## Deploy

O CD publica a imagem no GHCR a cada push na `main` (tag = SHA do commit) e faz o deploy no Azure com
Terraform, autenticado por OIDC, sem nenhum segredo guardado no GitHub. Passo a passo da primeira vez:
[docs/deploy-azure.md](docs/deploy-azure.md).

## Estrutura

```
src/redacao/       API (FastAPI), configuração e telemetria
tests/             testes (com trava de rede: nenhum teste acessa a internet)
scripts/           smoke test pós-deploy e validação por mutação
infra/             Terraform do ambiente demo, testes do Terraform e o bootstrap do Azure
security/          política SecurityFN e mutações dos controles
reports/seguranca/ relatório de mutação e relatórios do gate por task
docs/              visão, arquitetura, plano, segurança, decisões, deploy e changelog
.claude/skills/    skill SecurityFN para o Claude Code
.github/           CI, CD e Dependabot
```

## Documentação

- [Visão do produto e histórias de usuário](docs/00-visao.md)
- [Arquitetura](docs/01-arquitetura.md)
- [Plano de tasks](docs/02-plano-de-tasks.md)
- [Segurança: modelo de ameaças e controles](docs/03-seguranca.md)
- [Decisões registradas (D1–D17)](docs/decisoes.md)
- [Deploy no Azure](docs/deploy-azure.md)
- [Changelog](docs/CHANGELOG.md)

## Licença e créditos

Projeto desenvolvido com assistência do Claude (Anthropic).

Código sob licença MIT. A avaliação (F3) usa o corpus
[Essay-BR](https://github.com/lplnufpi/essay-br) (licença MIT), baixado por script e não versionado:
MARINHO, J. C.; ANCHIÊTA, R. T.; MOURA, R. S. *Essay-BR: a Brazilian Corpus to Automatic Essay
Scoring Task*. Journal of Information and Data Management, 2022.
