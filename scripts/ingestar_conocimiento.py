"""Aplica las migraciones e ingiere el corpus de `knowledge_base/` con embeddings BGE-M3.

La ingesta es idempotente: solo reindexa los documentos nuevos o modificados y elimina los que
ya no existen. Requiere los servicios `db` y `embeddings` (`docker compose up -d --wait`).

Uso: python scripts/ingestar_conocimiento.py
"""

import time

import psycopg

from multiagente.core.configuracion import ConfiguracionBaseDatos
from multiagente.persistencia.migraciones import aplicar_migraciones
from multiagente.rag.documentos import cargar_corpus
from multiagente.rag.embeddings import VectorizadorTEI
from multiagente.rag.ingesta import ingestar


def main() -> None:
    """Migra el esquema, ingiere el corpus e imprime el resumen por colección."""
    inicio = time.perf_counter()
    corpus = cargar_corpus()
    vectorizador = VectorizadorTEI()
    with psycopg.connect(ConfiguracionBaseDatos().cadena_conexion()) as conexion:
        migraciones = aplicar_migraciones(conexion)
        resumen = ingestar(conexion, corpus, vectorizador)
        conexion.commit()

    print(f"Migraciones aplicadas: {', '.join(migraciones) or 'ninguna pendiente'}")
    print(f"Documentos en el corpus: {len(corpus)} · modelo: {vectorizador.modelo}")
    print(f"  nuevos: {len(resumen.nuevos)} · actualizados: {len(resumen.actualizados)}")
    print(f"  sin cambios: {len(resumen.sin_cambios)} · eliminados: {len(resumen.eliminados)}")
    print("Fragmentos por colección:")
    for coleccion, total in resumen.fragmentos_por_coleccion.items():
        print(f"  {coleccion:26} {total:4}")
    print(f"Tiempo: {time.perf_counter() - inicio:.1f} s")


if __name__ == "__main__":
    main()
