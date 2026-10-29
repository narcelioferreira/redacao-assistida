# Decisões registradas

Cada decisão traz o contexto e a consequência. Mudança que contraria uma decisão registra a nova
decisão aqui, no mesmo PR. D13 a D16 já estão decididas e passam a valer quando a fase chegar.

## D1 · Azure como nuvem

A vaga de referência cita Azure primeiro nas duas listas (plataforma de IA e nuvem), e o Azure
OpenAI é comum em empresas brasileiras. O desenho é portável: Container Apps → ECS Fargate ou Lambda,
Service Bus → SQS, Azure OpenAI → Bedrock, Entra → Cognito.

## D2 · Container Apps, plano de consumo, com escala a zero

Kubernetes gerenciado sem operar cluster, com KEDA nativo para escalar o worker pela fila (F2). Sem
tráfego, nenhuma réplica roda: o custo fica dentro da cota grátis. Em troca, a primeira requisição
paga um cold start, medido no experimento P3.

## D3 · Imagem no GHCR público, com tag do SHA do commit

O código já é público, então a imagem também pode ser: o GHCR é grátis e dispensa o Azure Container
Registry (custo fixo mensal). A tag do SHA é imutável: o Terraform recusa tag móvel, e o smoke test
confere que `/health/live` informa o SHA do commit, porque a revisão antiga também responderia 200.

## D4 · Terraform, com bootstrap separado e menor privilégio

O Terraform do CD cria tudo dentro do grupo de recursos do projeto. Grupos, estado remoto, identidade
do CD e registro de provedores ficam num bootstrap executado uma vez pelo dono da assinatura. Assim a
identidade do CD só precisa de Contributor no grupo do projeto e de acesso ao container do estado. O
estado fica num Storage Account sem chave de acesso e com versionamento.

## D5 · Deploy por OIDC, sem segredo no GitHub

O GitHub emite um token OIDC por execução, e o Entra ID troca esse token por um token do Azure. A
credencial federada só aceita jobs do environment `demo` deste repositório. Não existe client secret
para vazar ou expirar. Os IDs cadastrados como variáveis não são segredos.

## D6 · Um ambiente só (demo), mais o local

Para uma PoC, um ambiente de staging dobraria o custo e o trabalho sem trazer aprendizado novo. Os
testes, o build com smoke test da imagem no CI e o smoke test pós-deploy cobrem o risco. Staging é o
próximo passo natural se o projeto crescer.

## D7 · Documentação OpenAPI no ar também no demo

Diferente de um sistema interno, aqui o contrato é parte do produto: o front e quem avalia o projeto
consomem `/docs`. A API não expõe nada além do que o contrato descreve.

## D8 · Erros no formato RFC 9457, com trace_id

Um formato único para todos os erros: o front tem um só tratador, e o `trace_id` liga a resposta ao
trace no App Insights. A resposta nunca traz a mensagem de uma exceção interna nem ecoa o valor
enviado, que pode ser texto de aluno ou dado pessoal.

## D9 · Cadeia de suprimentos

Actions fixadas por SHA de commit e imagens por digest (tags podem ser movidas, OWASP AST02/AST07).
`uv.lock` com hashes, instalado com `--locked`. Só entram versões publicadas há 14 dias ou mais:
`exclude-newer = "14 days"` no `pyproject.toml` (vale também para o Dependabot) e `cooldown` no
Dependabot para actions e providers do Terraform. As imagens base são a exceção, porque as atualizações
delas costumam ser correções de segurança. A imagem publicada leva SBOM e atestado de proveniência.

As duas regras podem entrar em conflito: o `pip-audit` aponta uma vulnerabilidade cuja correção tem
menos de 14 dias. Nesse caso, a correção vence, só para aquele pacote: `exclude-newer-package` com data
de corte exata, comentário com o CVE e a data de remoção (quando a versão completar 14 dias). A
exceção não pode ficar esquecida, porque a data por pacote substitui a janela relativa e travaria as
atualizações seguintes. Primeiro caso: `certifi` e `filelock`, em 29/10/2026.

## D10 · OpenTelemetry com exportação para o App Insights

Instrumentação padrão e portável. Toda requisição tem trace, inclusive local. As probes `/health/*`
ficam fora do trace e a imagem roda sem access log, porque só gerariam custo. O Log Analytics tem
teto de 0,5 GB/dia de ingestão.

## D11 · Python no back-end

A vaga pede Node.js "e/ou" Python. Python é a linguagem dos SDKs e das bibliotecas de IA usadas no
projeto, e o TypeScript aparece no front (F4).

## D12 · Simplificações deliberadas

- **Sem GraphQL:** existe um único front consumindo a API, e REST resolve.
- **Sem Kubernetes próprio:** o Container Apps já roda KEDA gerenciado.
- **Sem framework de agente:** o fluxo de avaliação é fixo, e um pipeline em código é mais simples de
  testar. Na F5, o loop de function calling é escrito à mão.

## D13 · Fila no Service Bus Basic, com consumidor idempotente (F2)

O plano Basic custa centavos, tem DLQ, mas não tem detecção de duplicidade. Por isso o worker é
idempotente: se já existe avaliação para (redação, versão do prompt), ele confirma a mensagem e sai.
A entrega é pelo menos uma vez, e duplicatas não causam dano.

## D14 · A mensagem leva só o id (claim check) (F2)

O texto do aluno fica no banco e nunca passa pelo broker. O limite de tamanho da mensagem deixa de
importar, e há um lugar a menos guardando dado pessoal.

## D15 · Republicação pelo job agendado em vez de outbox transacional (F2)

A API grava o lote e publica as mensagens: se a publicação falhar no meio, algumas redações ficam
"na fila" sem mensagem. Em vez de um outbox, um job agendado republica redações paradas há mais de
10 minutos. Como o consumidor é idempotente (D13), republicar nunca duplica uma avaliação.

## D16 · O arquivo original não é guardado (F2)

A API extrai o texto do `.docx` e descarta o arquivo. Isso dispensa o Blob Storage e minimiza dados de
menores (LGPD).

## D17 · Segurança por OWASP ASI, com teste e mutação por controle

A referência principal é o OWASP Top 10 for Agentic Applications 2026 (ASI01–ASI10), com o AST e o
OWASP API Security Top 10 como mapeamentos complementares (`docs/03-seguranca.md`). É a mesma
estratégia do Lead Qualifier. Um controle só conta como implementado com um teste que o comprova e uma
mutação (`security/mutacoes.toml`) que derruba esse teste quando a proteção é desligada. O CI roda
todas as mutações. Toda task passa pelo ciclo de 5 etapas da política `security/Skill_SecurityFN.md`.
