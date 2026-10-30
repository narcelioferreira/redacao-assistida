# Visão do produto

## Problema

Corrigir redação no padrão ENEM é lento: cada texto pede leitura atenta e uma nota em cada uma das 5
competências. Com turmas grandes, a devolutiva chega tarde, e o aluno acaba escrevendo menos do que
precisaria para evoluir.

## Para quem

- **Professor(a) de redação:** envia os textos de uma turma, revisa a pré-correção e devolve a nota
  final ao aluno.
- **Coordenador(a) pedagógico(a):** acompanha as turmas da escola e confere o quanto a pré-correção
  concorda com os professores.

## Proposta

Uma pré-correção que chega em minutos: nota sugerida por competência, justificativa e os trechos do
texto que sustentam cada nota. O professor revisa e decide. A IA nunca dá a nota final.

## Princípios

1. **A IA sugere, o professor decide.** A revisão humana faz parte do fluxo, não é opcional.
2. **Medir antes de afirmar.** Concordância com corretores humanos, custo e latência são medidos e
   publicados, inclusive quando o resultado é ruim.
3. **Dados de menores, o mínimo possível.** Sem nome de aluno (só um identificador definido pela
   escola), sem guardar o arquivo original, com prazo de retenção e exclusão a pedido.
4. **O LLM interpreta, o código confere.** Tudo que dá para verificar (níveis de nota válidos, trechos
   citados que existem no texto, texto insuficiente) é verificado em código.

## Escopo do MVP (F0 a F4)

- Envio de lote de redações digitadas (texto ou `.docx`) de uma turma, com um tema (proposta).
- Avaliação assíncrona por fila, com progresso em tempo real.
- Nota sugerida por competência (0 a 200, em passos de 40), justificativa e trechos citados.
- Alerta de possível manipulação (instruções para a IA escondidas no texto).
- Revisão do professor e registro da nota final.
- Resumo da turma: médias por competência e concordância IA × professor.
- Login, papéis (professor e coordenador) e isolamento entre escolas.

## Fora do escopo, por enquanto

- Redação manuscrita (OCR).
- Outros vestibulares e outras rubricas.
- Integração com plataformas da escola (LMS, Google Classroom).
- Devolutiva direta ao aluno: a pré-correção vai para o professor.

## Métricas de sucesso

| Tipo | Métrica |
|---|---|
| Produto | Tempo para processar um lote de 30 redações |
| Produto | Percentual de notas sugeridas que o professor mantém |
| Qualidade | QWK e MAE por competência contra corretores humanos (corpus Essay-BR) |
| Qualidade | Taxa de discrepância pelo critério do INEP: diferença maior que 100 pontos no total ou maior que 80 em alguma competência, o gatilho do 3º corretor no ENEM |
| Robustez | Variação da nota quando há injeção de prompt escondida no texto (meta: nenhuma) |
| Custo | Custo por redação |
| Operação | Latência p50 e p95, taxa de falha, mensagens na DLQ |

## Histórias de usuário

Rascunho para a T09: o Narcelio refina, porque conhece a rotina do professor e do coordenador.

**HU01 · Enviar um lote.** Como professor, quero enviar as redações de uma turma de uma vez, para
receber a pré-correção sem ficar esperando na tela.
- Aceito texto colado ou `.docx`; cada redação tem um identificador do aluno definido por mim.
- A resposta é imediata (o processamento continua em segundo plano).
- Reenviar o mesmo lote por engano não duplica nada.

**HU02 · Acompanhar o progresso.** Como professor, quero ver quantas redações do lote já foram
avaliadas, para saber quando posso começar a revisar.
- O progresso atualiza sozinho, sem recarregar a página.
- Redações que falharam aparecem como falha, com a opção de tentar de novo.

**HU03 · Ver a pré-correção.** Como professor, quero ver a nota sugerida de cada competência com a
justificativa e os trechos do texto, para revisar rápido.
- Cada trecho citado existe de fato na redação.
- A nota de cada competência é um dos níveis válidos (0, 40, 80, 120, 160, 200).

**HU04 · Revisar e decidir.** Como professor, quero ajustar as notas e registrar a nota final, porque
a decisão é minha.
- A nota sugerida e a final ficam registradas lado a lado.
- A redação só conta como concluída depois da minha revisão.

**HU05 · Acompanhar a turma.** Como coordenador, quero ver as médias por competência e a concordância
entre a IA e os professores, para decidir onde focar.

**HU06 · Desconfiar de manipulação.** Como professor, quero ser avisado quando uma redação parecer
conter instruções para a IA, para olhar essa com mais cuidado.
- O aviso não zera a nota: só marca a redação para revisão atenta.

**HU07 · Apagar dados.** Como escola, quero que os textos sejam apagados depois de um prazo e quando eu
pedir, porque são dados de alunos menores de idade.

**HU08 · Privacidade entre professores e escolas.** Como professor, quero que só eu e a coordenação
da minha escola vejamos as minhas turmas.
