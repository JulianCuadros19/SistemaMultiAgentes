-- Bases de conocimiento: documentos y fragmentos vectorizados (RF-29 a RF-32).
-- Una sola base con filtro obligatorio por colección (decisión 9). La dimensión 1024 corresponde
-- a BGE-M3 (decisión 8): cambiar de modelo de embeddings obliga a recrear la tabla y reindexar.

CREATE TYPE coleccion_conocimiento AS ENUM (
    'elicitacion',
    'dominio_negocio',
    'arquitecturas_referencia',
    'criterios_calidad'
);

CREATE TABLE kb_documentos (
    id                  text PRIMARY KEY,
    coleccion           coleccion_conocimiento NOT NULL,
    ruta                text NOT NULL UNIQUE,
    titulo              text NOT NULL,
    fuente              text NOT NULL,
    tipo_fuente         text NOT NULL,
    version             text NOT NULL,
    fecha               date NOT NULL,
    segmentacion        text NOT NULL,
    etiquetas           text[] NOT NULL DEFAULT '{}',
    huella              char(64) NOT NULL,
    modelo_embeddings   text NOT NULL,
    ingestado           timestamptz NOT NULL DEFAULT now(),
    UNIQUE (id, coleccion)
);

CREATE TABLE kb_fragmentos (
    id              bigserial PRIMARY KEY,
    documento_id    text NOT NULL,
    coleccion       coleccion_conocimiento NOT NULL,
    orden           integer NOT NULL CHECK (orden >= 0),
    titulo          text NOT NULL,
    contenido       text NOT NULL,
    metadatos       jsonb NOT NULL DEFAULT '{}',
    embedding       vector(1024) NOT NULL,
    lexico          tsvector GENERATED ALWAYS AS (
                        to_tsvector('spanish', titulo || ' ' || contenido)
                    ) STORED,
    UNIQUE (documento_id, orden),
    -- El fragmento hereda la colección de su documento; no puede quedar en otra.
    FOREIGN KEY (documento_id, coleccion)
        REFERENCES kb_documentos (id, coleccion) ON DELETE CASCADE
);

CREATE INDEX kb_fragmentos_coleccion ON kb_fragmentos (coleccion);
CREATE INDEX kb_fragmentos_embedding ON kb_fragmentos USING hnsw (embedding vector_cosine_ops);
CREATE INDEX kb_fragmentos_lexico ON kb_fragmentos USING gin (lexico);
