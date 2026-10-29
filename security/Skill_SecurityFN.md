# Skill SecurityFN · Política central

Política de qualidade e segurança aplicada a toda task do Redação Assistida. A skill
(`.claude/skills/securityfn/SKILL.md`) só aponta para este arquivo.

## 1. O ciclo de cada task

Toda task do `docs/02-plano-de-tasks.md`, de qualquer fase e de qualquer dono, passa por 5 etapas,
nesta ordem. Uma etapa só começa quando a anterior terminou.

| # | Etapa | O que é feito | Sai daqui |
|---|---|---|---|
| 1 | **Código** | Implementação pelo dono da task. Em tasks 👤, os casos de teste são combinados em texto **antes** do código | Diff completo e casos de teste |
| 2 | **Segurança** | Revisão do diff com o checklist da seção 4. Cada controle novo ganha teste e mutação em `security/mutacoes.toml`. `docs/03-seguranca.md` é atualizado | Achados corrigidos ou aceitos como risco residual |
| 3 | **Teste** | `make check`, `make tf-check` e `make mutacao`, localmente e no CI | Saída real dos comandos |
| 4 | **Validação** | O critério de aceite conferido de verdade (no Azure, quando a task chega lá); o autor responde às perguntas de revisão; CHANGELOG atualizado | Relatório da seção 6 com a decisão do gate |
| 5 | **Próxima tarefa** | Coluna "Real" do plano preenchida; próxima task e seu dono apontados; riscos novos registrados | Plano atualizado |

## 2. Proveniência

Toda task declara a proveniência do código entregue:

| Proveniência | Quando | Perfil aplicado |
|---|---|---|
| `HUMANO` | Escrito pelo Narcelio sem participação substancial de IA (tasks 👤) | Padrão |
| `IA_ASSISTIDO` | Gerado, corrigido, refatorado, convertido ou testado por IA (tasks 🤖) | Reforçado |
| `HÍBRIDO` | Combinação dos dois (tasks 👥, ou 👤 com trechos sugeridos por IA) | Reforçado nas partes de IA |
| `DESCONHECIDO` | Sem rastreabilidade (código colado, origem incerta) | Reforçado |

**Perfil padrão:** checklist completo, gate da seção 5, revisão do Claude.

**Perfil reforçado**, além do padrão:
- revisão do diff completo, linha a linha, não por amostragem;
- todo controle novo com mutação (o teste precisa falhar com a proteção desligada);
- nenhuma dependência, permissão ou serviço novo sem justificativa escrita;
- de 3 a 5 perguntas de revisão, que o Narcelio responde antes do merge;
- desconfiar de testes que só confirmam o próprio código: um teste precisa conseguir falhar.

## 3. Confirmação humana

**Sempre pedir confirmação explícita** antes de:
- tocar em produção ou no Azure (apply, deploy, mudança no portal);
- publicar: push para a `main`, merge, release, comentário público;
- alterar permissões (papéis, tokens, `permissions:` de workflow);
- comando destrutivo (`rm -rf`, `git reset --hard`, `terraform destroy`, força no push);
- adicionar dependência, action ou imagem nova;
- acessar a rede para algo que não seja instalar a partir do lockfile.

**Liberado sem perguntar:** instalar exatamente o que está no lockfile (`uv sync --locked`), build
local, rodar testes, lint e mutação, e criar commits locais. Push para branch de trabalho já autorizada
pelo Narcelio também é liberado.

## 4. Checklist de segurança (etapa 2)

Para cada item, responder "não se aplica", "atendido (teste X)" ou "achado".

**ASI (OWASP Top 10 for Agentic Applications 2026)**
- ASI01: algum texto não confiável chega ao LLM? Está delimitado com nonce? A saída é restrita?
- ASI02: o LLM ganhou alguma ferramenta? O escopo vem do código?
- ASI03: identidade, segredo ou permissão nova? Tem escopo mínimo? Algum segredo em log ou erro?
- ASI04: dependência, action, imagem ou prompt novo? Está fixado (hash, SHA, digest)?
- ASI05: algo da entrada ou da saída do LLM é executado ou desserializado sem schema?
- ASI06: algum conteúdo vira contexto em execuções futuras? Passa pelo detector?
- ASI07: mensagem entre componentes? Leva só o necessário e é validada?
- ASI08: há limite de tempo, de tentativas, de custo e de volume? Falha vira erro controlado?
- ASI09: a saída chega a uma pessoa? Está saneada e marcada como sugestão?
- ASI10: algum componente decide o próprio caminho? Há teto em código e trilha de auditoria?

**API e dados**
- Autorização por objeto e por função (OWASP API1, API5): recurso de outra escola dá 404?
- Entrada com `extra="forbid"` e limite de tamanho; resposta só com os campos do contrato.
- Erros em Problem Details, sem detalhe interno e sem ecoar o valor enviado.
- LGPD: texto de aluno fora de logs, traces e filas; nada de nome de aluno; retenção respeitada.

## 5. Gate (decisão da etapa 4)

| Decisão | Quando |
|---|---|
| ✅ **Aprovado** | `make check`, `make tf-check` e `make mutacao` verdes; critério de aceite verificado; nenhum achado aberto; perguntas de revisão respondidas (perfil reforçado) |
| ⚠️ **Aprovado com ressalvas** | Tudo acima, mas com achado de baixo risco aceito e registrado em `docs/03-seguranca.md` (riscos residuais), com task para tratar |
| ⏳ **Aguardando validação** | Etapas 1 a 3 concluídas e verdes, mas falta algo que só o Narcelio ou o ambiente real podem fazer: o CI no GitHub, o critério de aceite no Azure, as respostas às perguntas de revisão. Não pode ir para a `main` nesse estado |
| ❌ **Reprovado** | Qualquer verificação vermelha, mutação sobrevivente, segredo exposto, controle sem teste, ou critério de aceite que falhou quando foi verificado |

Nunca declarar uma verificação que não foi executada. O que não pôde rodar (por exemplo, por falta de
conta ou de rede) aparece em "Limitações", e a decisão leva isso em conta.

## 6. Relatório (em português do Brasil)

```markdown
## Relatório SecurityFN · <task> · <data>

**Escopo:** <arquivos e o que mudou>
**Proveniência:** HUMANO | IA_ASSISTIDO | HÍBRIDO | DESCONHECIDO → perfil <padrão | reforçado>

### Riscos considerados
<checklist da seção 4: só os itens que se aplicam, com a resposta>

### Verificações executadas
| Verificação | Comando | Resultado real |
|---|---|---|

### Achados
| # | Severidade | Achado | Tratamento |
|---|---|---|---|

### Limitações
<o que não foi verificado e por quê>

### Riscos residuais
<o que fica, com a task que trata>

### Perguntas de revisão (perfil reforçado)
1. ...

### Decisão do gate: ✅ Aprovado | ⚠️ Aprovado com ressalvas | ⏳ Aguardando validação | ❌ Reprovado
### Próxima tarefa: <ID> · <dono>
```

Os relatórios ficam em `reports/seguranca/` (um por task ou por grupo de tasks entregues juntas).
