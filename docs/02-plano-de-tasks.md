# Plano de tasks

Cada fase termina em produção. Estimativas em dias de trabalho; anote o tempo real ao fechar a task,
porque "estimei 3 dias, levou 5, e o motivo foi X" é a conversa de estimativa que as vagas pedem.

**Donos** (combinado em `CLAUDE.md`): 👤 Narcelio escreve, Claude revisa · 🤖 Claude escreve,
Narcelio revisa e responde às perguntas de revisão · 👥 Narcelio decide, os dois executam.

**Situação:** ✅ pronta · 🚧 em andamento · ⏳ a fazer

**Segurança:** riscos do [docs/03-seguranca.md](03-seguranca.md) que a task trata (ASI01–ASI10 e
API1–API10). Ao fechar a task, o controle muda de "planejado" para "implementado" naquele documento,
com teste e mutação.

## O ciclo de cada task

Toda task passa pelas 5 etapas da política [security/Skill_SecurityFN.md](../security/Skill_SecurityFN.md),
nesta ordem:

1. **Código.** O dono implementa. Em tasks 👤, os casos de teste são combinados em texto antes do
   código.
2. **Segurança.** Checklist ASI e API sobre o diff; cada controle novo ganha teste e mutação em
   `security/mutacoes.toml`; `docs/03-seguranca.md` atualizado.
3. **Teste.** `make check`, `make tf-check` e `make mutacao` verdes, localmente e no CI.
4. **Validação.** Critério de aceite conferido de verdade (no Azure, quando a task chega lá),
   perguntas de revisão respondidas, CHANGELOG atualizado e relatório em `reports/seguranca/` com a
   decisão do gate.
5. **Próxima tarefa.** Coluna "Real" preenchida e próxima task apontada, com o dono.

A proveniência segue o dono: 👤 `HUMANO` (perfil padrão), 🤖 `IA_ASSISTIDO` e 👥 `HÍBRIDO` (perfil
reforçado).

## F0 · Esqueleto no ar (estimativa: 2 d)

Aceite da fase: um push na `main` publica uma nova revisão no Azure sozinho, e o smoke test confirma
que a versão no ar é a do commit.

| ID | Task | Dono | Segurança | Estim. | Real | Situação |
|---|---|---|---|---|---|---|
| T01 | Estrutura do repo: pyproject com uv (regra dos 14 dias), ruff, mypy strict, pytest com trava de rede, Makefile, `CLAUDE.md`. Aceite: `make check` verde | 🤖 | ASI04, ASI08 | 0,25 | 0,1 | ✅ |
| T02 | API mínima: fábrica, `/health/live` com a versão, `/health/ready`, erros RFC 9457 com `trace_id`, cabeçalhos de segurança, OpenAPI. Aceite: testes de 404, 405, 409, 422 (sem ecoar o valor) e 500 (sem vazar detalhe) | 🤖 | ASI03, API8 | 0,25 | 0,1 | ✅ |
| T03 | Dockerfile multi-stage (digest, usuário 10001, sem setuid, healthcheck) e compose. Aceite: container só leitura e sem capabilities passa no smoke test | 🤖 | ASI03, ASI04 | 0,25 | 0,1 | ✅ |
| T04 | CI: lint, tipos, testes, gate de segurança, build e smoke test da imagem, validação e testes do Terraform. Aceite: primeiro PR verde | 🤖 | ASI04 | 0,25 | 0,1 | 🚧 validado localmente; falta o 1º PR |
| T05 | CD, parte 1: imagem no GHCR a cada push na `main`, com tag do SHA, SBOM e proveniência. Aceite: `ghcr.io/narcelioferreira/redacao-assistida:<sha>` publicada | 🤖 | ASI04 | 0,25 | 0,1 | 🚧 roda no 1º merge |
| T06 | Terraform: Log Analytics com teto diário, App Insights, ambiente e Container App da API com escala a zero, orçamento com alertas. Aceite: `terraform validate` e `terraform test` no CI | 🤖 | ASI03, ASI08 | 0,25 | 0,1 | ✅ |
| TS01 | Fundação de segurança: `docs/03-seguranca.md` (ASI, AST e API Top 10), skill SecurityFN e política, gate com bandit, detect-secrets e zizmor, testes dos controles da F0 e validação por mutação no CI. Aceite: todas as mutações mortas | 🤖 | ASI03, ASI04, ASI08 | 0,5 | 0,3 | ✅ |
| T07 | Bootstrap do Azure: conta, provedores, estado remoto, identidade OIDC, papéis e variáveis no GitHub (`docs/deploy-azure.md`). Aceite: o CD autentica no Azure sem segredo | 👥 | ASI03 | 0,25 | | ⏳ depende da conta |
| T08 | CD, parte 2: `terraform apply` e smoke test (versão no ar = SHA). Aceite: o aceite da fase | 🤖 | ASI03, ASI04 | 0,25 | 0,1 | 🚧 código pronto; roda após a T07 |
| T09 | Refinar as histórias de usuário de `docs/00-visao.md` (rotina real do professor e do coordenador). Aceite: HU01–HU08 com critérios revisados | 👥 | — | 0,25 | | ⏳ |

## F1 · Uma redação (estimativa: 3 d)

Aceite da fase: um professor autenticado avalia uma redação em produção, e um professor de outra
escola recebe 404 ao tentar vê-la.

| ID | Task | Dono | Segurança | Estim. | Real | Situação |
|---|---|---|---|---|---|---|
| T10 | Modelo de dados: o Narcelio desenha tabelas, chaves, restrições e o que é só inserção; Claude escreve as migrations (Alembic) e põe o Postgres no compose. Aceite: diagrama no docs e migration aplicada no CI | 👥 | ASI10, LGPD | 0,5 | | ⏳ |
| T11 | Terraform: Postgres Flexible B1ms com pgvector, Azure OpenAI com deployment, identidade gerenciada com papéis; bootstrap ganha permissão restrita de atribuir papéis; decisão de região do modelo. Aceite: apply no demo sem senha no código | 🤖 | ASI03, LGPD | 0,5 | | ⏳ |
| T12 | Entra External ID: o Narcelio configura o tenant e os usuários demo pelo portal, com guia do Claude. Aceite: token de teste obtido | 👥 | ASI03 | 0,25 | | ⏳ |
| T13 | Autenticação: validação do JWT (assinatura via JWKS, `iss`, `aud`, `exp`, algoritmos permitidos) e a dependência `usuario_atual`. Aceite: testes com token forjado, expirado e de outra audiência | 👤 | ASI03, API2 | 0,5 | | ⏳ |
| T14 | Autorização: papéis professor e coordenador, escopo por escola, RLS no Postgres. Aceite: teste de BOLA (professor de outra escola → 404) | 👤 | ASI03, API1, API5 | 0,5 | | ⏳ |
| T15 | `llmkit.client`: cliente OpenAI no endpoint v1 do Azure OpenAI (Managed Identity), timeouts, retries com `Retry-After`, saída estruturada, fake para testes, contagem de tokens e custo. Aceite: testes com 429 e 5xx simulados | 🤖 | ASI03, ASI08 | 0,25 | | ⏳ |
| T16 | `llmkit.prompts`: prompts versionados com SHA-256 num lock; versão publicada imutável; recusa iniciar se divergir; hash gravado em cada avaliação | 🤖 | ASI04, ASI06 | 0,25 | | ⏳ |
| T17 | Prompt v1 e schema de saída da rubrica (5 competências, níveis de 0 a 200), com a redação em bloco delimitado por nonce. Aceite: 5 redações do corpus avaliadas e discutidas | 👤 | ASI01 | 0,25 | | ⏳ |
| T18 | Pipeline síncrono (pré-checagem → LLM → validação em código) e `POST /v1/redacoes:avaliar`. Aceite: o aceite da fase | 👤 | ASI01, ASI05, API10 | 0,5 | | ⏳ |
| T19 | oasdiff no CI: mudança incompatível em `/v1` falha o build | 🤖 | ASI04, API9 | 0,1 | | ⏳ |

## F2 · Lotes por fila (estimativa: 3 d)

Aceite da fase: um lote de 30 redações escala o worker de 0 a N e de volta a 0; uma mensagem
envenenada cai na DLQ e dispara alerta; o App Insights mostra um trace único da API ao LLM.

| ID | Task | Dono | Segurança | Estim. | Real | Situação |
|---|---|---|---|---|---|---|
| T20 | Terraform: Service Bus Basic (fila com DLQ), worker no Container Apps com escala KEDA por Managed Identity, alertas (DLQ > 0, taxa de 5xx) | 🤖 | ASI03, ASI07, ASI08 | 0,5 | | ⏳ |
| T21 | Porta de fila (`Protocol`) com adaptadores Service Bus e em memória (testes); mensagem validada com `extra="forbid"` | 🤖 | ASI07 | 0,25 | | ⏳ |
| T22 | Criação de lote: `POST /v1/turmas/{id}/lotes` com `Idempotency-Key`, 202 + `Location`, limite de corpo, `.docx` lido com segurança, uma mensagem por redação (só o id) | 👤 | ASI05, ASI07, API3, API4 | 0,5 | | ⏳ |
| T23 | Worker: consumo idempotente por (redação, versão do prompt), retries com backoff e jitter, DLQ para falha permanente | 👤 | ASI07, ASI08 | 0,75 | | ⏳ |
| T24 | Progresso do lote: `GET /v1/lotes/{id}` e SSE em `/eventos` | 🤖 | API1 | 0,25 | | ⏳ |
| T25 | Cota diária por escola (429 + `Retry-After`), orçamento de tokens por lote e chave para desligar o LLM | 👥 | ASI08, API4, API6 | 0,25 | | ⏳ |
| T26 | Trace de ponta a ponta: `traceparent` na mensagem, spans GenAI (modelo, tokens, custo), sem texto de aluno | 🤖 | ASI08, LGPD | 0,25 | | ⏳ |
| T27 | Job agendado: retenção de dados e republicação de redações presas na fila (D15) | 🤖 | ASI08, LGPD | 0,25 | | ⏳ |

## F3 · Qualidade (estimativa: 3 d)

Aceite da fase: o README tem a tabela de resultados medidos, inclusive os negativos.

| ID | Task | Dono | Segurança | Estim. | Real | Situação |
|---|---|---|---|---|---|---|
| T30 | Loader do Essay-BR: script de download, splits do próprio corpus, nada versionado | 🤖 | ASI04 | 0,25 | | ⏳ |
| T31 | Métricas: QWK, MAE, taxa de discrepância INEP. Aceite: testes com valores calculados à mão | 👤 | — | 0,5 | | ⏳ |
| T32 | Runner de avaliação, relatório no Job Summary e gate no CI com teto de custo | 🤖 | ASI08 | 0,5 | | ⏳ |
| T33 | Guardrails: caracteres invisíveis, mascaramento de PII, heurística de injeção (marca para revisão, não zera), validador de trechos citados | 👤 | ASI01, ASI09, LGPD | 0,75 | | ⏳ |
| T34 | Conjunto adversarial (injeções escondidas na redação), teste de robustez e seção "Segurança" no relatório | 👥 | ASI01 | 0,25 | | ⏳ |
| T35 | Experimentos E1–E3 (1 chamada × 5; C5 em código × LLM; modelo mini × maior). Claude roda e tabula; as conclusões são do Narcelio | 👥 | — | 0,5 | | ⏳ |
| T36 | Experimentos de desempenho P1–P3 (concorrência do worker, cache de prompt, cold start) | 👥 | ASI08 | 0,25 | | ⏳ |

## F4 · Front e revisão (estimativa: 3 d)

Aceite da fase: um recrutador entra com o usuário demo e faz o fluxo inteiro em menos de 3 minutos.

| ID | Task | Dono | Segurança | Estim. | Real | Situação |
|---|---|---|---|---|---|---|
| T40 | SPA React + TypeScript (Vite) com cliente gerado do OpenAPI e login MSAL: turmas, envio de lote com progresso, redação com avaliação (marcada como sugestão, saneada) e revisão | 🤖 | ASI09 | 1,5 | | ⏳ |
| T41 | Revisão do professor: `PUT /v1/redacoes/{id}/revisao` (nota final só depois da revisão) e concordância IA × professor no resumo da turma | 👤 | ASI09, API1 | 0,5 | | ⏳ |
| T42 | Static Web Apps no Terraform, CD do front, CORS restrito, usuários demo e dados semeados | 🤖 | ASI03, API8 | 0,5 | | ⏳ |
| T43 | Guia de integração do front (`docs/integracao-front.md`) e mock do contrato | 🤖 | — | 0,25 | | ⏳ |

## F5 · Opcional: assistente da turma (estimativa: 2 d)

| ID | Task | Dono | Segurança | Estim. | Real | Situação |
|---|---|---|---|---|---|---|
| T50 | Loop de function calling escrito à mão: limite de iterações, teto de tokens, timeout por ferramenta | 👤 | ASI02, ASI08, ASI10 | 0,75 | | ⏳ |
| T51 | Ferramentas só de leitura (o escopo da turma vem do código, nunca do modelo) e busca semântica com pgvector; trechos recuperados passam pelo detector | 🤖 | ASI02, ASI06 | 0,75 | | ⏳ |
| T52 | Avaliação do assistente: os números da resposta batem com a saída das ferramentas | 👥 | ASI09 | 0,5 | | ⏳ |
