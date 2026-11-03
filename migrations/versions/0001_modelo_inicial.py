"""Modelo de dados inicial (T10, decisão D18).

Revisão: 0001
Anterior: nenhuma

Decisões do Narcelio, aplicadas aqui:
1. `escola_id` em todas as tabelas, consistente com o pai por chave estrangeira composta
   (escola_id, id): uma linha nunca aponta para um registro de outra escola.
2. Notas em 5 colunas (c1..c5), só com os níveis do ENEM (0, 40, 80, 120, 160, 200).
3. Avaliações só por inserção, únicas por (redação, hash do prompt): base da idempotência do
   worker (D13).
4. Revisões só por inserção: a mais recente é a nota final.
5. Ids UUIDv7, conferidos pelo próprio banco.
6. Texto da redação em tabela separada: a retenção apaga o texto e mantém as notas sem dado pessoal.
7. Retenção configurável por escola, padrão de 180 dias.
8. `aluno_ref` é texto livre definido pela escola (matrícula ou número da chamada), nunca o nome.

Row-Level Security por escola fica para a T14.
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# Níveis válidos de cada competência no ENEM.
_NIVEL = "IN (0, 40, 80, 120, 160, 200)"


def _uuid7(coluna: str = "id") -> str:
    # uuid_extract_version existe a partir do Postgres 17.
    return f"CHECK (uuid_extract_version({coluna}) = 7)"


def upgrade() -> None:
    op.execute(f"""
        CREATE TABLE escolas (
            id            uuid PRIMARY KEY {_uuid7()},
            nome          text NOT NULL CHECK (length(nome) BETWEEN 1 AND 200),
            retencao_dias integer NOT NULL DEFAULT 180 CHECK (retencao_dias BETWEEN 1 AND 730),
            criado_em     timestamptz NOT NULL DEFAULT now()
        );

        CREATE TABLE usuarios (
            id        uuid PRIMARY KEY {_uuid7()},
            escola_id uuid NOT NULL REFERENCES escolas (id),
            -- Identificador do login (claim `sub` do Entra ID). Único no sistema inteiro.
            sub       text NOT NULL UNIQUE CHECK (length(sub) BETWEEN 1 AND 255),
            papel     text NOT NULL CHECK (papel IN ('professor', 'coordenador')),
            criado_em timestamptz NOT NULL DEFAULT now(),
            UNIQUE (escola_id, id)
        );

        CREATE TABLE turmas (
            id           uuid PRIMARY KEY {_uuid7()},
            escola_id    uuid NOT NULL REFERENCES escolas (id),
            professor_id uuid NOT NULL,
            nome         text NOT NULL CHECK (length(nome) BETWEEN 1 AND 100),
            ano_letivo   smallint NOT NULL CHECK (ano_letivo BETWEEN 2020 AND 2100),
            criado_em    timestamptz NOT NULL DEFAULT now(),
            UNIQUE (escola_id, id),
            UNIQUE (escola_id, ano_letivo, nome),
            FOREIGN KEY (escola_id, professor_id) REFERENCES usuarios (escola_id, id)
        );

        CREATE TABLE propostas (
            id              uuid PRIMARY KEY {_uuid7()},
            escola_id       uuid NOT NULL REFERENCES escolas (id),
            criado_por      uuid NOT NULL,
            titulo          text NOT NULL CHECK (length(titulo) BETWEEN 1 AND 300),
            texto_motivador text NOT NULL DEFAULT '' CHECK (length(texto_motivador) <= 20000),
            criado_em       timestamptz NOT NULL DEFAULT now(),
            UNIQUE (escola_id, id),
            FOREIGN KEY (escola_id, criado_por) REFERENCES usuarios (escola_id, id)
        );

        CREATE TABLE lotes (
            id              uuid PRIMARY KEY {_uuid7()},
            escola_id       uuid NOT NULL REFERENCES escolas (id),
            turma_id        uuid NOT NULL,
            proposta_id     uuid NOT NULL,
            criado_por      uuid NOT NULL,
            -- Idempotency-Key do POST: reenviar o mesmo lote não cria outro (HU01).
            idempotency_key text NOT NULL CHECK (length(idempotency_key) BETWEEN 1 AND 255),
            status          text NOT NULL DEFAULT 'recebido' CHECK (
                                status IN ('recebido', 'processando', 'concluido', 'com_falhas')
                            ),
            criado_em       timestamptz NOT NULL DEFAULT now(),
            UNIQUE (escola_id, id),
            UNIQUE (escola_id, idempotency_key),
            FOREIGN KEY (escola_id, turma_id) REFERENCES turmas (escola_id, id),
            FOREIGN KEY (escola_id, proposta_id) REFERENCES propostas (escola_id, id),
            FOREIGN KEY (escola_id, criado_por) REFERENCES usuarios (escola_id, id)
        );

        CREATE TABLE redacoes (
            id             uuid PRIMARY KEY {_uuid7()},
            escola_id      uuid NOT NULL,
            lote_id        uuid NOT NULL,
            -- Código do aluno definido pela escola. Fica nulo depois da anonimização.
            aluno_ref      text CHECK (length(aluno_ref) BETWEEN 1 AND 64),
            status         text NOT NULL DEFAULT 'na_fila' CHECK (
                               status IN ('na_fila', 'avaliando', 'avaliada', 'falhou', 'revisada')
                           ),
            tentativas     smallint NOT NULL DEFAULT 0 CHECK (tentativas >= 0),
            criado_em      timestamptz NOT NULL DEFAULT now(),
            -- Calculado na criação: criado_em + retencao_dias da escola.
            expira_em      timestamptz NOT NULL,
            anonimizada_em timestamptz,
            UNIQUE (escola_id, id),
            -- Um aluno entrega uma redação por lote.
            UNIQUE (lote_id, aluno_ref),
            -- Anonimizada se e somente se o aluno_ref foi apagado.
            CHECK ((aluno_ref IS NULL) = (anonimizada_em IS NOT NULL)),
            CHECK (expira_em > criado_em),
            FOREIGN KEY (escola_id, lote_id) REFERENCES lotes (escola_id, id) ON DELETE CASCADE
        );

        -- Decisão 6: o texto do aluno fica separado e é apagado pela retenção.
        CREATE TABLE redacao_textos (
            redacao_id uuid PRIMARY KEY,
            escola_id  uuid NOT NULL,
            texto      text NOT NULL CHECK (length(texto) BETWEEN 1 AND 20000),
            FOREIGN KEY (escola_id, redacao_id) REFERENCES redacoes (escola_id, id)
                ON DELETE CASCADE
        );

        CREATE TABLE avaliacoes (
            id             uuid PRIMARY KEY {_uuid7()},
            escola_id      uuid NOT NULL,
            redacao_id     uuid NOT NULL,
            -- SHA-256 do prompt e da rubrica usados (T16).
            prompt_hash    text NOT NULL CHECK (prompt_hash ~ '^[0-9a-f]{{64}}$'),
            modelo         text NOT NULL CHECK (length(modelo) BETWEEN 1 AND 100),
            c1             smallint NOT NULL CHECK (c1 {_NIVEL}),
            c2             smallint NOT NULL CHECK (c2 {_NIVEL}),
            c3             smallint NOT NULL CHECK (c3 {_NIVEL}),
            c4             smallint NOT NULL CHECK (c4 {_NIVEL}),
            c5             smallint NOT NULL CHECK (c5 {_NIVEL}),
            total          smallint GENERATED ALWAYS AS (c1 + c2 + c3 + c4 + c5) STORED,
            alerta_injecao boolean NOT NULL DEFAULT false,
            tokens_entrada integer NOT NULL CHECK (tokens_entrada >= 0),
            tokens_saida   integer NOT NULL CHECK (tokens_saida >= 0),
            tokens_cache   integer NOT NULL DEFAULT 0 CHECK (tokens_cache >= 0),
            custo_usd      numeric(10, 6) NOT NULL CHECK (custo_usd >= 0),
            latencia_ms    integer NOT NULL CHECK (latencia_ms >= 0),
            criado_em      timestamptz NOT NULL DEFAULT now(),
            UNIQUE (escola_id, id),
            UNIQUE (escola_id, redacao_id, id),
            -- Idempotência do worker (D13): a mesma redação com o mesmo prompt é avaliada uma vez.
            UNIQUE (redacao_id, prompt_hash),
            FOREIGN KEY (escola_id, redacao_id) REFERENCES redacoes (escola_id, id)
                ON DELETE CASCADE
        );

        -- Justificativas e trechos citam o texto do aluno: também são apagados pela retenção,
        -- enquanto as notas (em `avaliacoes`) continuam imutáveis.
        CREATE TABLE avaliacao_detalhes (
            avaliacao_id   uuid PRIMARY KEY,
            escola_id      uuid NOT NULL,
            justificativas jsonb NOT NULL,
            trechos        jsonb NOT NULL,
            FOREIGN KEY (escola_id, avaliacao_id) REFERENCES avaliacoes (escola_id, id)
                ON DELETE CASCADE
        );

        CREATE TABLE revisoes (
            id           uuid PRIMARY KEY {_uuid7()},
            escola_id    uuid NOT NULL,
            redacao_id   uuid NOT NULL,
            -- A avaliação da IA que o professor tinha na tela ao revisar.
            avaliacao_id uuid NOT NULL,
            professor_id uuid NOT NULL,
            c1           smallint NOT NULL CHECK (c1 {_NIVEL}),
            c2           smallint NOT NULL CHECK (c2 {_NIVEL}),
            c3           smallint NOT NULL CHECK (c3 {_NIVEL}),
            c4           smallint NOT NULL CHECK (c4 {_NIVEL}),
            c5           smallint NOT NULL CHECK (c5 {_NIVEL}),
            total        smallint GENERATED ALWAYS AS (c1 + c2 + c3 + c4 + c5) STORED,
            criado_em    timestamptz NOT NULL DEFAULT now(),
            FOREIGN KEY (escola_id, redacao_id) REFERENCES redacoes (escola_id, id)
                ON DELETE CASCADE,
            -- A avaliação revisada precisa ser desta mesma redação.
            FOREIGN KEY (escola_id, redacao_id, avaliacao_id)
                REFERENCES avaliacoes (escola_id, redacao_id, id) ON DELETE CASCADE,
            FOREIGN KEY (escola_id, professor_id) REFERENCES usuarios (escola_id, id)
        );

        -- Decisões 3 e 4: avaliações e revisões só recebem inserção. DELETE continua possível
        -- (exclusão do lote a pedido, LGPD); UPDATE nunca.
        CREATE FUNCTION recusa_alteracao() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'a tabela % só recebe inserção', TG_TABLE_NAME
                USING ERRCODE = 'restrict_violation';
        END;
        $$;

        CREATE TRIGGER avaliacoes_so_insercao BEFORE UPDATE ON avaliacoes
            FOR EACH ROW EXECUTE FUNCTION recusa_alteracao();
        CREATE TRIGGER revisoes_so_insercao BEFORE UPDATE ON revisoes
            FOR EACH ROW EXECUTE FUNCTION recusa_alteracao();

        -- Índices para as consultas por escola e para as chaves estrangeiras.
        CREATE INDEX turmas_professor ON turmas (escola_id, professor_id);
        CREATE INDEX lotes_turma ON lotes (escola_id, turma_id);
        CREATE INDEX redacoes_lote_status ON redacoes (escola_id, lote_id, status);
        CREATE INDEX redacoes_expiracao ON redacoes (expira_em) WHERE anonimizada_em IS NULL;
        CREATE INDEX avaliacoes_redacao ON avaliacoes (escola_id, redacao_id, criado_em);
        CREATE INDEX revisoes_redacao ON revisoes (escola_id, redacao_id, criado_em);
    """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE revisoes, avaliacao_detalhes, avaliacoes, redacao_textos, redacoes, lotes,
            propostas, turmas, usuarios, escolas;
        DROP FUNCTION recusa_alteracao();
    """)
