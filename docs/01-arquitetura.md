# Arquitetura

Situação de cada parte: ✅ existe · ⏳ planejada (fase entre parênteses).

## Componentes

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
 Job diário: apaga dados vencidos (retenção) e republica redações presas na fila
```

| Peça | Serviço | Situação |
|---|---|---|
| API | Azure Container Apps, plano de consumo, escala a zero | ✅ |
| Logs e telemetria | Log Analytics (teto diário) + App Insights via OpenTelemetry | ✅ |
| Controle de custo | Orçamento do grupo de recursos com alertas por e-mail | ✅ |
| Imagens | GitHub Container Registry público, tag = SHA do commit | ✅ |
| Infra como código | Terraform (azurerm 5.x), estado remoto em Storage Account | ✅ |
| CI/CD | GitHub Actions; deploy por OIDC | ✅ (o deploy aguarda a T07) |
| Banco | PostgreSQL Flexible B1ms com pgvector | ⏳ (F1) |
| LLM | Azure OpenAI, modelo escolhido pelo experimento E3 | ⏳ (F1) |
| Login | Entra External ID | ⏳ (F1) |
| Fila | Service Bus Basic, fila com DLQ | ⏳ (F2) |
| Worker | Container Apps com escala KEDA pela fila, via Managed Identity | ⏳ (F2) |
| Front | Static Web Apps (plano Free) | ⏳ (F4) |

## Como uma redação é avaliada (F2)

```
mensagem {redacao_id, versao_prompt}
 ├─ 1. idempotência  já avaliada nesta versão? confirma e sai
 ├─ 2. pré-checagem  código: texto insuficiente (regra do ENEM), caracteres invisíveis, PII mascarada
 ├─ 3. injeção       heurística; suspeita → marca para revisão humana (não zera a nota)
 ├─ 4. avaliar       LLM com JSON Schema estrito: nível 0–200 (passos de 40), justificativa e
 │                   trechos literais por competência; a redação entra como dado delimitado
 ├─ 5. validar       código: níveis válidos, cada trecho citado existe no texto;
 │                   reprovou → 1 nova tentativa → senão "falhou" (revisão manual)
 └─ 6. gravar        avaliação + tokens, tokens em cache, custo, latência → progresso do lote
erro transitório (429, 5xx, timeout) → backoff com jitter → esgotou → DLQ + alerta
```

## Contrato da API

```
GET    /health/live                 ✅ versão (SHA) e ambiente
GET    /health/ready                ✅ (F1: confere o Postgres)
POST   /v1/turmas/{id}/lotes        ⏳ Idempotency-Key → 202 + Location
GET    /v1/lotes/{id}               ⏳ status e progresso
GET    /v1/lotes/{id}/eventos       ⏳ progresso em tempo real (SSE)
GET    /v1/lotes/{id}/redacoes      ⏳ paginação por cursor, filtro por status
GET    /v1/redacoes/{id}            ⏳ texto, avaliação da IA, alertas
PUT    /v1/redacoes/{id}/revisao    ⏳ nota final do professor
DELETE /v1/lotes/{id}               ⏳ exclusão a pedido (LGPD)
GET    /v1/turmas/{id}/resumo       ⏳ médias por competência, concordância IA × professor
```

Convenções:
- Erros no formato RFC 9457 (Problem Details) com `trace_id`; o valor enviado nunca volta na resposta.
- Versão no caminho (`/v1`). Mudança incompatível no contrato falha o CI (oasdiff, T19).
- Cota diária por escola esgotada → `429` com `Retry-After`.
- Recurso de outra escola → `404`, não `403`: a API não confirma que o recurso existe.

## Modelo de dados (rascunho para a T10)

`escolas → usuarios (papel) → turmas → lotes → redacoes → avaliacoes → revisoes`

- `avaliacoes` só recebe inserções: cada uma guarda modelo, versão do prompt, tokens, custo e
  latência. Reavaliar com um prompt novo cria outra linha.
- A escola de quem faz a requisição vem do vínculo do usuário no banco, nunca do corpo da requisição.
  O isolamento é reforçado por Row-Level Security no Postgres.
- O aluno é um identificador definido pela escola; o sistema não guarda nome.

## Segurança e privacidade

O modelo de ameaças, os controles (com teste e mutação de cada um) e os riscos residuais estão em
[03-seguranca.md](03-seguranca.md), mapeados ao OWASP ASI, AST e API Security Top 10.

## Observabilidade

- Toda requisição tem um trace (OpenTelemetry). O `trace_id` vai na resposta de erro e é o
  `operation_Id` no App Insights.
- As probes `/health/*` ficam fora do trace, e a imagem roda sem access log: só gerariam custo.
- A partir da F2, o `traceparent` viaja na mensagem da fila, e um lote aparece como um trace único,
  da API ao LLM.

## Custos

| Peça | Custo esperado |
|---|---|
| Container Apps | Dentro da cota grátis mensal (180 mil vCPU-s, 360 mil GiB-s, 2 milhões de requisições) com escala a zero |
| Log Analytics / App Insights | Dentro da franquia gratuita; teto de 0,5 GB/dia de ingestão |
| GHCR | Grátis (imagem pública) |
| PostgreSQL B1ms (F1) | Grátis por 12 meses em conta nova; depois, é o maior custo fixo |
| Azure OpenAI (F1) | Por token: o custo por redação vira métrica publicada |
| Service Bus Basic (F2) | Centavos |

O orçamento do grupo de recursos manda alertas em 50% e 80% do valor real e quando a previsão do mês
passa de 100%.
