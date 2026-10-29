---
name: skill-securityfn
description: Revisar e melhorar qualidade, segurança, robustez, testabilidade e manutenibilidade de código em PT-BR. Use ao criar, revisar, refatorar, corrigir, testar ou aprovar código humano, assistido por IA, híbrido ou de origem desconhecida, incluindo APIs, LLMs, agentes, dados sensíveis e infraestrutura.
---

# Skill_SecurityFN para Claude Code

Leia imediatamente `security/Skill_SecurityFN.md` na raiz do repositório e aplique suas instruções
completas: o ciclo de 5 etapas (código, segurança, teste, validação e próxima tarefa), os perfis de
proveniência, o checklist, o gate e o formato do relatório.

Identifique a proveniência do código. Use `HUMANO` para código sem participação substancial de IA;
`IA_ASSISTIDO` para código gerado, corrigido, refatorado, convertido, testado ou alterado por IA;
`HÍBRIDO` para combinação; e `DESCONHECIDO` quando não houver rastreabilidade. Para `DESCONHECIDO`,
use o perfil `IA_ASSISTIDO`.

Antes de modificar arquivos, informe o escopo, os riscos e o plano. Revise o diff completo. Não invente
testes nem resultados. Não exponha segredos. Siga as regras de confirmação humana da seção 3 da
política: produção, publicação, permissões, comandos destrutivos, dependências novas e acesso à rede
fora do lockfile sempre exigem confirmação explícita.

Respeite o modo de trabalho do `CLAUDE.md`: em tasks 👤, revise e aponte problemas, mas não escreva a
implementação.

Ao finalizar, produza o relatório no formato definido na política central, em português do Brasil,
incluindo verificações realmente executadas, limitações, riscos residuais e decisão do gate.
