-- Traza por nodo del grafo y llamadas a los modelos (RF-34, RNF-10, ADR-0016).
-- Una fila por ejecución de un nodo, con su tiempo, su costo y su error, y una por cada llamada
-- al modelo que hizo, con su prompt y versión, sus tokens, su costo y su latencia. No se guarda el
-- contenido de los mensajes: la conversación y los artefactos están en los puntos de control.
-- El costo va en numeric sin escala, para conservar el Decimal exacto (decisión 10).

CREATE TABLE ejecuciones (
    id              bigserial PRIMARY KEY,
    sesion          text NOT NULL,
    nodo            text NOT NULL,
    inicio          timestamptz NOT NULL,
    duracion_ms     integer NOT NULL CHECK (duracion_ms >= 0),
    costo_usd       numeric NOT NULL DEFAULT 0,
    error           text
);

CREATE INDEX ejecuciones_por_sesion ON ejecuciones (sesion, inicio, id);

CREATE TABLE llamadas_modelo (
    id                              bigserial PRIMARY KEY,
    ejecucion                       bigint NOT NULL REFERENCES ejecuciones (id) ON DELETE CASCADE,
    orden                           integer NOT NULL,
    fecha                           timestamptz NOT NULL,
    nodo                            text NOT NULL,
    prompt                          text NOT NULL,
    huella_prompt                   text NOT NULL,
    despliegue                      text NOT NULL,
    modelo                          text NOT NULL,
    region_procesamiento            text,
    esfuerzo                        text NOT NULL,
    max_tokens_salida               integer NOT NULL,
    motivo_fin                      text NOT NULL,
    tokens_entrada                  integer NOT NULL,
    tokens_entrada_cacheada         integer NOT NULL,
    tokens_entrada_escrita_cache    integer NOT NULL,
    tokens_salida                   integer NOT NULL,
    tokens_razonamiento             integer NOT NULL,
    costo_usd                       numeric NOT NULL,
    latencia_ms                     integer NOT NULL,
    error                           text,
    UNIQUE (ejecucion, orden)
);
