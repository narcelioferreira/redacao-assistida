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
| F0 · Esqueleto no ar | API mínima, Docker, CI, imagem no GHCR, Terraform, CD com OIDC | 🚧 Código pronto e validado; o deploy aguarda a conta Azure (T07) |
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
make tf-check   # formato e validação do Terraform, sem credencial do Azure
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

## Deploy

O CD publica a imagem no GHCR a cada push na `main` (tag = SHA do commit) e faz o deploy no Azure com
Terraform, autenticado por OIDC, sem nenhum segredo guardado no GitHub. Passo a passo da primeira vez:
[docs/deploy-azure.md](docs/deploy-azure.md).

## Estrutura

```
src/redacao/       API (FastAPI), configuração e telemetria
tests/             testes (com trava de rede: nenhum teste acessa a internet)
scripts/smoke.py   smoke test pós-deploy (só biblioteca padrão)
infra/             Terraform do ambiente demo e o bootstrap do Azure
docs/              visão, arquitetura, plano de tasks, decisões, deploy e changelog
.github/           CI, CD e Dependabot
```

## Documentação

- [Visão do produto e histórias de usuário](docs/00-visao.md)
- [Arquitetura](docs/01-arquitetura.md)
- [Plano de tasks](docs/02-plano-de-tasks.md)
- [Decisões registradas (D1–D16)](docs/decisoes.md)
- [Deploy no Azure](docs/deploy-azure.md)
- [Changelog](docs/CHANGELOG.md)

## Licença e créditos

Código sob licença MIT. A avaliação (F3) usa o corpus
[Essay-BR](https://github.com/lplnufpi/essay-br) (licença MIT), baixado por script e não versionado:
MARINHO, J. C.; ANCHIÊTA, R. T.; MOURA, R. S. *Essay-BR: a Brazilian Corpus to Automatic Essay
Scoring Task*. Journal of Information and Data Management, 2022.
