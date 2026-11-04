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

O *subject* aceito usa os IDs imutáveis do dono e do repositório
(`repo:dono@ID/repo@ID:environment:demo`), que é o formato emitido pelo GitHub. Se o repositório for
apagado e alguém criar outro com o mesmo nome, o ID muda e o Azure recusa o token.

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

## D18 · Modelo de dados (T10)

Decidido pelo Narcelio. Schema em SQL explícito (`migrations/versions/0001_modelo_inicial.py`), sem
ORM gerando o banco: cada restrição é legível e defendida por teste de integração e mutação.

1. **`escola_id` em todas as tabelas**, com chave estrangeira composta `(escola_id, id)`: não depende
   de joins para saber de quem é cada linha, e uma linha nunca aponta para outra escola.
2. **Notas em 5 colunas** (`c1`..`c5`), só com os níveis do ENEM: a rubrica é fixa.
3. **Avaliações só por inserção**, várias por redação, únicas por (redação, hash do prompt): a escola
   corrige em quantidade, e cada nova versão do prompt gera outra avaliação.
4. **Revisões só por inserção**: a mais recente é a nota final.
5. **Ids UUIDv7**, conferidos pelo próprio banco.
6. **Texto separado** (`redacao_textos`), e também as justificativas e os trechos citados
   (`avaliacao_detalhes`), porque citam o texto do aluno: a retenção apaga essas tabelas e mantém as
   notas.
7. **Retenção configurável por escola, padrão de 180 dias** (de 1 a 730). Histórico entre anos e
   espelho em PDF ficaram fora (ver `00-visao.md`).
8. **`aluno_ref` em texto livre**: a escola escolhe matrícula ou número da chamada; o sistema nunca
   guarda o nome (pseudonimização).

Consequências que decorrem dessas escolhas, aplicadas no schema:
- **Postgres 17**, por causa da função `uuid_extract_version` usada na decisão 5. O Azure oferece
  essa versão (T11).
- "Só inserção" quer dizer **sem UPDATE**. DELETE continua possível, para a exclusão do lote a pedido
  (LGPD) apagar tudo em cascata.
- Sem campo de comentário na revisão: seria texto livre que a retenção teria de apagar numa tabela que
  não aceita alteração. Volta se aparecer a necessidade, em tabela própria.
- Uma redação por aluno por lote (`UNIQUE (lote_id, aluno_ref)`).
- A revisão aponta para a avaliação que o professor viu, sempre da mesma redação.

## D19 · Azure OpenAI e Postgres no Azure (T11)

Decidido pelo Narcelio, com base na cota real da assinatura (consultada em 03/11/2026).

- **Azure OpenAI no Brazil South, deployment Global Standard, gpt-5-mini como padrão.** No Brazil
  South esses modelos só existem como Global Standard (cota da assinatura: gpt-5-mini 500 mil
  tokens/min, gpt-4.1-mini 200 mil). O texto pode ser processado em outra região: aceito porque chega
  sem nome de aluno e, a partir da T33, com dados pessoais mascarados. Criar o recurso numa região dos
  EUA também tiraria o processamento do Brasil, com menos cota.
- **Teto de 30 mil tokens/min** no deployment (de 1 a 100, validado no Terraform): limite de custo e
  de abuso (ASI08). Sobe só com medição (P1).
- **Sem chave de API** no Azure OpenAI: só a identidade da aplicação, com o papel "Cognitive Services
  OpenAI User".
- **Postgres Flexible B1ms, versão 17, endpoint público com login só por Entra ID** (sem senha), TLS
  obrigatório e firewall só para serviços do Azure. Rede privada foi descartada para a demo: exigiria
  recriar o ambiente do Container Apps e rodar migrations de dentro da Azure, quase dobrando a task.
  Fica como risco residual.
- **Duas identidades gerenciadas:** a da aplicação (OpenAI e, pela T11b, um papel no banco sem DDL) e
  a das migrations (administradora Entra do Postgres). Um comprometimento da API não altera o schema.
- **O CD atribui papéis, com condição.** "Role Based Access Control Administrator" no grupo do projeto,
  limitado por condição ABAC a criar e apagar só atribuições do papel "OpenAI User" para identidades
  de serviço. Amplia a D4 o mínimo necessário: o CD não consegue se dar Owner nem dar acesso a pessoas.
- **Versão do modelo:** sem fixar por enquanto (vale a padrão do Azure na criação). Fixar quando o E3
  escolher o modelo, porque a avaliação depende da versão.
- **Assinatura em avaliação gratuita**, que expira 30 dias depois da criação (por volta de 29/11/2026).
  Sem upgrade (D20).

## D20 · Janela do Azure: avaliação gratuita, sem upgrade

Decidido pelo Narcelio em 04/11/2026. A assinatura é uma avaliação gratuita (crédito de US$ 200, 30
dias) com cartão de terceiros apenas para verificação. **Não haverá upgrade:** quando o crédito ou o
prazo acabar (por volta de 29/11/2026), a Azure desativa os recursos e nada é cobrado.

Consequências:
- **O Azure tem uma janela.** Tudo o que precisa da nuvem para gerar evidência roda até ~28/11, na
  ordem de prioridade do plano (`02-plano-de-tasks.md`, seção "Janela do Azure").
- **As evidências ficam no repositório:** relatórios de avaliação em `reports/`, execuções do CI e do
  CD no GitHub, e capturas de tela feitas pelo Narcelio no fim da janela.
- **O projeto continua reproduzível:** com outra assinatura, bootstrap e `terraform apply` recriam
  tudo. Localmente, `docker compose` roda a API e o banco.
- **Depois da janela, o LLM de desenvolvimento muda por configuração.** O cliente da T15 usa a API
  compatível com OpenAI, então a mesma aplicação fala com Azure OpenAI, Groq ou Ollama.
- **O que não depende de nuvem fica para depois da janela,** se faltar tempo: o front (roda local), o
  login real (a T13 testa com tokens assinados localmente) e as tasks opcionais.
