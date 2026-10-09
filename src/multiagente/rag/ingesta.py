"""Ingesta idempotente del corpus: segmentación, vectorización e indexación (RF-30)."""

from collections.abc import Sequence

from psycopg import Connection
from psycopg.types.json import Jsonb
from pydantic import BaseModel

from multiagente.rag.documentos import DocumentoConocimiento
from multiagente.rag.embeddings import Vectorizador
from multiagente.rag.segmentacion import segmentar


class ResumenIngesta(BaseModel):
    """Resultado de una ingesta: qué documentos cambiaron y cuántos fragmentos hay."""

    nuevos: list[str]
    actualizados: list[str]
    sin_cambios: list[str]
    eliminados: list[str]
    fragmentos_por_coleccion: dict[str, int]


def literal_vector(vector: Sequence[float]) -> str:
    """Representa un vector en el formato de texto de pgvector, p. ej. `[0.1,0.2]`.

    Args:
        vector: Componentes del vector.

    Returns:
        Texto que PostgreSQL convierte con `::vector`.
    """
    return "[" + ",".join(f"{componente:.8g}" for componente in vector) + "]"


def texto_a_vectorizar(titulo: str, contenido: str) -> str:
    """Texto que representa a un fragmento: su título de contexto y su contenido."""
    return f"{titulo}\n\n{contenido}"


def ingestar(
    conexion: Connection,
    documentos: Sequence[DocumentoConocimiento],
    vectorizador: Vectorizador,
) -> ResumenIngesta:
    """Indexa el corpus dentro de la transacción de la conexión.

    Solo se reindexan los documentos nuevos o cuya huella o modelo de embeddings cambió; los
    que ya no están en el corpus se eliminan con sus fragmentos. El llamador confirma la
    transacción.

    Args:
        conexion: Conexión con las tablas de conocimiento en su `search_path`.
        documentos: Corpus completo, como lo devuelve `cargar_corpus`.
        vectorizador: Servicio de embeddings.

    Returns:
        Resumen de la ingesta.
    """
    existentes = {
        identificador: (huella, modelo)
        for identificador, huella, modelo in conexion.execute(
            "SELECT id, huella, modelo_embeddings FROM kb_documentos"
        ).fetchall()
    }
    resumen = ResumenIngesta(
        nuevos=[], actualizados=[], sin_cambios=[], eliminados=[], fragmentos_por_coleccion={}
    )
    for documento in documentos:
        metadatos = documento.metadatos
        if existentes.get(metadatos.id) == (documento.huella, vectorizador.modelo):
            resumen.sin_cambios.append(metadatos.id)
            continue
        fragmentos = segmentar(documento)
        vectores = vectorizador.vectorizar(
            [texto_a_vectorizar(f.titulo, f.contenido) for f in fragmentos]
        )
        conexion.execute("DELETE FROM kb_fragmentos WHERE documento_id = %s", (metadatos.id,))
        conexion.execute(
            """
            INSERT INTO kb_documentos (id, coleccion, ruta, titulo, fuente, tipo_fuente, version,
                fecha, segmentacion, etiquetas, huella, modelo_embeddings)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                coleccion = EXCLUDED.coleccion, ruta = EXCLUDED.ruta, titulo = EXCLUDED.titulo,
                fuente = EXCLUDED.fuente, tipo_fuente = EXCLUDED.tipo_fuente,
                version = EXCLUDED.version, fecha = EXCLUDED.fecha,
                segmentacion = EXCLUDED.segmentacion, etiquetas = EXCLUDED.etiquetas,
                huella = EXCLUDED.huella, modelo_embeddings = EXCLUDED.modelo_embeddings,
                ingestado = now()
            """,
            (
                metadatos.id,
                metadatos.coleccion.value,
                documento.ruta,
                metadatos.titulo,
                metadatos.fuente,
                metadatos.tipo_fuente,
                metadatos.version,
                metadatos.fecha,
                metadatos.segmentacion.value,
                metadatos.tags,
                documento.huella,
                vectorizador.modelo,
            ),
        )
        with conexion.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO kb_fragmentos (documento_id, coleccion, orden, titulo, contenido,
                    metadatos, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s::vector)
                """,
                [
                    (
                        metadatos.id,
                        metadatos.coleccion.value,
                        fragmento.orden,
                        fragmento.titulo,
                        fragmento.contenido,
                        Jsonb(fragmento.metadatos),
                        literal_vector(vector),
                    )
                    for fragmento, vector in zip(fragmentos, vectores, strict=True)
                ],
            )
        destino = resumen.actualizados if metadatos.id in existentes else resumen.nuevos
        destino.append(metadatos.id)

    vigentes = {documento.metadatos.id for documento in documentos}
    resumen.eliminados = sorted(set(existentes) - vigentes)
    if resumen.eliminados:
        conexion.execute("DELETE FROM kb_documentos WHERE id = ANY(%s)", (resumen.eliminados,))
    resumen.fragmentos_por_coleccion = {
        coleccion: total
        for coleccion, total in conexion.execute(
            "SELECT coleccion::text, count(*) FROM kb_fragmentos GROUP BY coleccion ORDER BY 1"
        ).fetchall()
    }
    return resumen
