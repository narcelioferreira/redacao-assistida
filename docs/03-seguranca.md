# Segurança

Modelo de ameaças, controles e riscos residuais do Redação Assistida.

- **Referência principal:** [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)
  (ASI01–ASI10). O sistema é um fluxo de LLM com etapas fixas, não um agente autônomo, mas os riscos
  se aplicam: texto não confiável chega ao modelo, a saída influencia uma decisão humana e há
  identidades na nuvem.
- **Referências complementares:** [OWASP Agentic Skills Top 10](https://owasp.org/www-project-agentic-skills-top-10/)
  (AST, em revisão pública) e [OWASP API Security Top 10 2023](https://owasp.org/API-Security/editions/2023/en/0x11-t10/),
  porque o produto é uma API multiescola.

**Regras deste documento**
1. Cada controle **implementado** aponta para o teste que o comprova.
2. Cada controle implementado tem uma **mutação** em `security/mutacoes.toml`: com a proteção
   desligada de propósito, pelo menos um teste precisa falhar. O CI roda todas a cada PR
   (`scripts/mutacao.py`, job "Validação por mutação"). Resultado atual: [reports/seguranca/mutacao.md](../reports/seguranca/mutacao.md).
3. O que ainda não existe aparece como **planejado**, com a task correspondente. Ao fechar a task, o
   controle muda de coluna no mesmo PR.

---

## 1. O que está em risco

| Ativo | Por que importa |
|---|---|
| Nota sugerida | Influencia a nota que o professor dá. Uma nota manipulada (injeção escondida no texto) prejudica ou favorece um aluno |
| Texto das redações | Dados de alunos, em geral menores de idade (LGPD, art. 14) |
| Isolamento entre escolas | Uma escola nunca pode ver turmas, lotes ou redações de outra |
| Identidades no Azure | A identidade do CD e, a partir da F1, a Managed Identity da aplicação: acesso a dados e a custo |
| Orçamento | Tokens do LLM e recursos do Azure; um loop ou um abuso vira conta |
| Cadeia de suprimentos | Dependências, actions, imagens e prompts definem o que roda em produção |

**Entradas não confiáveis:** o texto da redação e o `.docx` enviado, o tema informado pela escola,
qualquer campo da requisição, os tokens recebidos e as mensagens lidas da fila.
**Entradas confiáveis:** prompts, rubrica e configuração, protegidos por hash a partir da T16 (ASI04).

---

## 2. Mapeamento ASI Top 10 (2026)

| Risco | Controles implementados | Teste que comprova (mutação) | Planejado |
|---|---|---|---|
| **ASI01 · Agent Goal Hijack** (injeção de prompt) | — (a F0 não tem LLM) | — | **T17/T18:** redação em bloco `<redacao_{nonce}>` com nonce aleatório por chamada, que o texto não consegue fechar; saída só com níveis válidos (0–200, passos de 40) num JSON Schema estrito. **T33:** detector determinístico de instruções para a IA; com suspeita, a redação **é marcada para revisão humana e não é zerada** (um falso positivo não pode punir o aluno). **T34:** conjunto adversarial, com a métrica "a nota não sobe com a injeção" |
| **ASI02 · Tool Misuse** | O LLM não recebe ferramentas na F1–F4 (D12). O smoke test só aceita `http(s)` | `test_recusa_esquema_que_nao_e_http` (M23) | **T50/T51 (F5):** ferramentas só de leitura, com o escopo da turma vindo do código e nunca do modelo; argumentos fora do schema recusados antes de executar |
| **ASI03 · Identity & Privilege Abuse** | Deploy por OIDC sem segredo, com a credencial federada presa ao environment `demo` (D5). Identidade do CD com Contributor só no grupo do projeto e acesso só ao container do estado (D4). Estado sem chave de acesso. Token do workflow com `contents: read` por padrão; checkout sem guardar credencial. Container sem root e sem setuid. Connection string em `SecretStr` e como secret do Container App. Erros sem detalhe interno; cabeçalhos de segurança | `test_token_oidc_so_no_job_de_deploy_e_no_environment_demo` (M07), `test_credencial_federada_presa_ao_environment` (M08), `test_papeis_do_cd_restritos_ao_projeto` (M09), `test_estado_do_terraform_sem_chave_de_acesso` (M10), `test_checkout_nao_guarda_credencial` (M06), `test_container_roda_sem_privilegio` (M05), `test_connection_string_nao_aparece_em_repr` (M03), `connection_string_como_secret` no Terraform (M11), `test_erro_inesperado_nao_vaza_detalhe_interno` (M01), `test_respostas_levam_cabecalhos_de_seguranca` (M04) | **T11:** Managed Identity no Azure OpenAI e no Postgres (sem senha nem chave). **T13:** JWT com assinatura via JWKS, `iss`, `aud`, `exp` e algoritmos permitidos. **T14:** papéis, escopo por escola e Row-Level Security |
| **ASI04 · Agentic Supply Chain** | `uv.lock` com hashes e `--locked`. Só versões com 14 dias ou mais, e exceção de segurança com data de remoção que o teste vigia (D9). Actions por SHA, imagens por digest, Dependabot com espera. Deploy só pela tag do SHA (D3). SBOM e proveniência na imagem. Gate: ruff (regras `S`), bandit, detect-secrets, gitleaks, pip-audit, zizmor | `test_actions_fixadas_por_sha_de_commit` (M12), `test_imagens_base_por_digest` (M13), `test_dependencias_com_14_dias_de_publicacao` (M14), `tag_movel_e_recusada` no Terraform (M15), `test_nenhum_segredo_alem_do_github_token` (M16), `test_dependabot_cobre_todos_os_ecossistemas_com_espera` (M17), `test_excecoes_de_seguranca_tem_data_de_remocao_e_nao_venceram` | **T16:** prompts, rubrica e configuração com SHA-256 num lock; versão publicada é imutável; o worker **recusa iniciar** se algo divergir, e o hash vai em cada avaliação. **T19:** oasdiff barra mudança incompatível no contrato |
| **ASI05 · Unexpected Code Execution** | Nada executa entrada do usuário. O script de mutação só roda comandos fixos, sem shell | bandit no gate | **T18:** a saída do LLM só é lida como JSON validado, nunca executada. **T22:** `.docx` lido com limite de tamanho, sem macros nem conteúdo externo; YAML só com `safe_load` |
| **ASI06 · Memory & Context Poisoning** | — (sem memória nem contexto recuperado na F0) | — | Sem memória de longo prazo. **T16:** rubrica e exemplos imutáveis por versão. **T51 (F5):** trechos recuperados passam de novo pelo detector de injeção, e só vale citação de redação recuperada na própria execução |
| **ASI07 · Insecure Inter-Agent Communication** | — (um único serviço na F0) | — | **T21/T23:** a mensagem da fila leva só o id e o `traceparent` (D14) e é validada com `extra="forbid"`; Service Bus acessado por Managed Identity, sem chave de acesso compartilhada |
| **ASI08 · Cascading Failures** | `/health` nunca depende do LLM. Escala a zero com teto de 2 réplicas. Log Analytics com teto diário. Probes fora do trace. Orçamento com alertas (50%, 80% e previsão de 100%). Trava de rede nos testes. Smoke test que confere a versão no ar | `escala_limitada` e `logs_com_destino_e_teto` no Terraform (M20, M21), `test_probes_ficam_fora_do_trace` (M19), `test_trava_de_rede_bloqueia_endereco_externo` (M18), `test_recusa_quando_a_revisao_no_ar_e_outra` (M22) | **T15/T23:** timeouts, retries limitados com `Retry-After` e jitter, DLQ e alerta. **T25:** cota diária por escola (429) e chave para desligar o LLM. Orçamento de tokens por lote |
| **ASI09 · Human-Agent Trust Exploitation** | — (sem saída de LLM na F0) | — | **T33:** cada trecho citado precisa existir no texto (conferido em código). **T40/T41:** a interface mostra "nota sugerida", e a nota final só existe depois da revisão do professor; justificativa saneada (sem HTML nem links) antes de chegar ao front |
| **ASI10 · Rogue Agents** | Pipeline com etapas fixas (D12): nenhum componente escolhe caminhos sozinho | — | **T10:** avaliações só por inserção, com modelo, hash do prompt, tokens e custo (trilha de auditoria). **T50 (F5):** loop de function calling com teto de iterações e de tokens decidido pelo código |

---

## 3. Mapeamento complementar: AST Top 10

O AST trata de skills (pacotes de habilidades instaláveis). Como o projeto não distribui skills, os
itens se aplicam por analogia aos artefatos que definem o comportamento do sistema: prompts, rubrica,
configuração e a skill de revisão usada no desenvolvimento (`.claude/skills/securityfn`).

| AST | Aplicação neste projeto | Onde está o controle |
|---|---|---|
| AST01 · Malicious Skills | A única skill é a de revisão, versionada no repositório e revisada como código | Revisão do PR |
| AST02 · Supply Chain Compromise | Dependências, actions e imagens | ASI04 |
| AST03 · Over-Privileged Skills | O LLM não tem ferramentas nem decide a nota final | ASI02, ASI09 |
| AST04 · Insecure Metadata | Configuração validada por Pydantic; YAML com `safe_load` | ASI05 |
| AST05 · Untrusted External Instructions | O texto da redação é dado, nunca instrução | ASI01 |
| AST06 · Weak Isolation | Container sem root; identidades com escopo mínimo | ASI03 |
| AST07 · Update Drift | Tag do SHA, digests, lock de prompts (T16) | ASI04 |
| AST08 · Poor Scanning | Gate do CI e conjunto adversarial medido (T34) | ASI04, ASI01 |
| AST09 · No Governance | Este documento, decisões registradas, auditoria das avaliações (T10) | ASI10 |
| AST10 · Cross-Platform Reuse | Não se aplica: um único runtime | — |

---

## 4. Mapeamento complementar: OWASP API Security Top 10 (2023)

| Risco | Controle | Situação |
|---|---|---|
| API1 · Broken Object Level Authorization | Escopo por escola, RLS e teste de BOLA (recurso de outra escola → 404) | ⏳ T14 |
| API2 · Broken Authentication | JWT validado por completo; sem chave de API estática | ⏳ T13 |
| API3 · Broken Object Property Level Authorization | Modelos de resposta explícitos; entrada com `extra="forbid"` | ⏳ T22 |
| API4 · Unrestricted Resource Consumption | Teto de réplicas e de logs ✅; limite de corpo, cota por escola e orçamento de tokens | ⏳ T22, T25 |
| API5 · Broken Function Level Authorization | Papéis professor e coordenador por rota | ⏳ T14 |
| API6 · Unrestricted Access to Sensitive Business Flows | Cota diária por escola para envio de lotes | ⏳ T25 |
| API7 · Server Side Request Forgery | Não se aplica: a API não busca URLs informadas pelo usuário | — |
| API8 · Security Misconfiguration | Cabeçalhos de segurança ✅, erros sem detalhe ✅, CORS restrito | ✅ / ⏳ T42 |
| API9 · Improper Inventory Management | Contrato OpenAPI publicado ✅ e oasdiff no CI | ✅ / ⏳ T19 |
| API10 · Unsafe Consumption of APIs | A resposta do LLM é validada em código antes de qualquer uso | ⏳ T18 |

---

## 5. Dados pessoais (LGPD)

Implementado:
- o erro 422 não ecoa o valor enviado, que pode ser texto de aluno ou dado pessoal (M02);
- o erro 500 não devolve detalhe interno (M01).

Planejado:
- sem nome de aluno: só um identificador definido pela escola (T10);
- PII mascarada antes de o texto ir ao LLM (T33);
- o `.docx` original não é guardado (D16);
- texto de redação fora de logs, traces e mensagens de fila (D14, T26);
- retenção com prazo e exclusão a pedido (T27, `DELETE /v1/lotes/{id}`);
- local de processamento do modelo registrado como decisão de privacidade (T11).

---

## 6. Medição contínua

- **Mutação:** o job "Validação por mutação" do CI roda todas as mutações e falha se alguma
  sobreviver. Toda task que cria um controle acrescenta a sua mutação.
- **Adversarial (F3, T34):** o relatório de avaliação terá uma seção "Segurança" com a variação da nota
  nas redações com injeção, a taxa de detecção e os falsos alarmes em redações legítimas. As regras são
  escritas com o split de desenvolvimento; o split de teste só mede.

---

## 7. Riscos residuais (conhecidos e aceitos por ora)

| Risco | Mitigação atual | Próximo passo |
|---|---|---|
| A API do demo está pública e sem autenticação | Na F0 ela só expõe `/health` e `/docs`, sem dados | Login e autorização (T13, T14) antes de qualquer rota com dados |
| Confiança na plataforma do GitHub (Actions, OIDC, GHCR) | Actions por SHA, credencial presa ao environment, proveniência na imagem | Exigir revisão no environment `demo` (proteção do GitHub) |
| O bootstrap roda com o privilégio de dono da assinatura | É manual, idempotente, curto e versionado | Revisar o script antes de cada execução |
| Uma exceção de segurança da regra dos 14 dias pode ser esquecida | O teste falha quando a data de remoção passa | — |
| Injeção nova que engane as regras e o modelo (F1+) | A nota final é do professor; o alerta não zera | Conjunto adversarial (T34) e revisão dos falsos negativos |
| Texto de aluno processado pelo Azure OpenAI | Sem nome de aluno; PII mascarada (planejado) | Decisão de região e de tipo de implantação (T11) |
