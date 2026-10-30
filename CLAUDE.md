# CLAUDE.md

Instruções para o Claude Code neste repositório. Leia antes de qualquer mudança.

## O projeto

Redação Assistida: pré-correção de redações no estilo ENEM com LLM, fila e revisão humana, no Azure.
É o projeto de portfólio do Narcelio para vagas de Engenharia de IA (nível pleno). O valor está em
três coisas: deploy real em nuvem, evidências medidas e código que o autor consegue defender em
entrevista.

## Modo de trabalho: misto (combinado com o Narcelio)

Cada task de `docs/02-plano-de-tasks.md` tem um dono:

- **👤 Narcelio escreve.** É o núcleo que cai em entrevista: pipeline do worker, idempotência,
  guardrails, métricas de avaliação, autenticação e autorização, prompts. **Claude não escreve a
  implementação dessas tasks**, nem como "esboço". Claude pode explicar conceitos, discutir o desenho,
  listar casos de teste em texto, revisar o código, apontar bugs e sugerir melhorias. Se o Narcelio
  pedir explicitamente que Claude escreva uma parte 👤, lembre o combinado uma vez, siga a decisão
  dele e registre a exceção no CHANGELOG.
- **🤖 Claude escreve.** Infra e boilerplate: Terraform, CI/CD, Docker, front, clientes de SDK,
  scripts. Ao terminar, entregue de 3 a 5 perguntas de estudo sobre o diff, **só na conversa**:
  elas não vão para o repositório nem bloqueiam a task (decisão do Narcelio). O conteúdo de estudo é
  entregue à parte, num documento fora do repositório.
- **👥 Juntos.** O Narcelio decide (modelo de dados, histórias, conclusões dos experimentos) e Claude
  ajuda a executar.

Antes de mexer em código, confira o dono da task. Se a mudança não pertence a nenhuma task, pergunte.

## Ciclo de cada task (skill SecurityFN)

Toda task, de qualquer dono, passa por 5 etapas: **código → segurança → teste → validação → próxima
tarefa**. Use a skill `skill-securityfn`, que aplica a política `security/Skill_SecurityFN.md`
(proveniência, checklist ASI e API, regras de confirmação, gate e relatório). Em resumo:

- todo controle novo tem teste **e** mutação em `security/mutacoes.toml` (`make mutacao` exige que
  todas morram);
- `docs/03-seguranca.md` muda no mesmo PR: o controle passa de "planejado" para "implementado";
- o relatório da task vai para `reports/seguranca/`, com a decisão do gate;
- nunca declare uma verificação que não rodou.

## Idioma e nomes

- Português do Brasil em documentação, comentários, docstrings, mensagens de erro, commits e nomes
  de teste.
- Contrato da API (rotas e campos JSON) em português: é a língua do produto.
- No código, termos do domínio em português sem acento (`redacao`, `lote`, `turma`, `competencia`) e
  termos técnicos em inglês (`create_app`, `settings`, `client`).

## Comandos

```bash
make install    # uv sync --locked (versões e hashes do uv.lock)
make check      # ruff, mypy strict, pytest com cobertura, pip-audit
make run        # API local com reload
make docker-run # API na imagem de produção (docker compose)
make smoke      # smoke test contra a API local
make tf-check   # terraform fmt, init sem backend, validate e test (provider simulado)
make mutacao    # validação por mutação dos controles de segurança
```

`make check` inclui o gate de segurança: bandit, detect-secrets, pip-audit e zizmor. Antes de
considerar uma task pronta, `make check`, `make tf-check` e `make mutacao` precisam passar. O CI roda
os três, mais gitleaks e o build com smoke test da imagem.

## Regras que não podem ser quebradas

**Segredos e dados**
- Nenhum segredo no repositório nem no GitHub. O CD entra no Azure por OIDC; a aplicação usa
  Managed Identity. `.env` nunca é commitado.
- Erros sempre em Problem Details (`redacao.api.problems`). Nunca devolva a mensagem de uma exceção
  ao cliente, nem ecoe o valor enviado.
- Texto de redação nunca vai para log, trace ou mensagem de fila: a mensagem leva só o id (D14).
- `/health/*` nunca depende do LLM nem de serviço externo.

**Cadeia de suprimentos (D9)**
- Actions fixadas por SHA, imagens por digest, deploy sempre pela tag do SHA do commit.
- Dependências Python só com 14 dias ou mais de publicação (`exclude-newer` no `pyproject.toml`). Não
  desligue a regra para pegar uma versão nova. A única exceção é correção de segurança apontada pelo
  `pip-audit`: por pacote, com data de corte, CVE e data de remoção comentados. Remova as exceções
  vencidas sempre que mexer no `pyproject.toml`.
- Dependência nova precisa de justificativa no PR.

**Testes**
- Nenhum teste acessa a rede externa (trava em `tests/conftest.py`). LLM sempre falso nos testes. Não
  remova a trava.
- Todo bug encontrado ganha um teste.

**Avaliação e honestidade (a partir da F3)**
- A IA nunca dá a nota final: o produto exige a revisão do professor.
- Nenhuma afirmação de qualidade, custo ou latência sem medição publicada em `reports/`. Resultados
  negativos também são publicados.
- Regras verificáveis (níveis válidos, trechos citados existem no texto, texto insuficiente) ficam em
  código, nunca só no prompt.

**Infra**
- O Terraform é a única fonte da verdade do ambiente demo. Nada é criado à mão no portal, exceto o
  bootstrap.
- A identidade do CD só acessa o grupo de recursos do projeto e o estado (D4). Não amplie sem
  registrar a decisão.

## Estilo de código

- Python 3.12, ruff (100 colunas, com as regras de segurança `S`), mypy strict, Pydantic v2.
- Regras de negócio em funções puras e testáveis; I/O nas bordas (API, repositório, fila, LLM).
- Dependências externas entram por interface (`Protocol`), para os testes usarem fakes.
- Comentários explicam o porquê (uma decisão Dn ou um achado), não o quê.

## Documentação

- `docs/00-visao.md`: problema, princípios, escopo e histórias de usuário.
- `docs/01-arquitetura.md`: componentes, fluxo, contrato da API, modelo de dados, custos.
- `docs/02-plano-de-tasks.md`: fases, tasks, donos, riscos tratados, estimativas e critérios de aceite.
- `docs/03-seguranca.md`: modelo de ameaças, controles com teste e mutação, riscos residuais.
- `docs/decisoes.md`: decisões D1–D17. Mudança que contraria uma decisão registra a nova no mesmo PR.
- `docs/deploy-azure.md`: bootstrap e primeiro deploy.
- `docs/CHANGELOG.md`: uma entrada por task fechada (o que foi feito, como foi testado, problemas
  encontrados). Atualize também a coluna "Real" do plano.

## Commits

`tipo(Txx): descrição` em português, ex.: `feat(T22): criação de lote com Idempotency-Key`.

Sem trailer `Co-Authored-By` nem link de sessão: a assistência do Claude é registrada uma única vez,
no README (decisão do Narcelio).
