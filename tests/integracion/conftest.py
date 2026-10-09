"""Conexiones aisladas para las pruebas que escriben en la base de conocimiento."""

import uuid

import psycopg
import pytest

from multiagente.core.configuracion import ConfiguracionBaseDatos
from multiagente.persistencia.migraciones import aplicar_migraciones
from multiagente.rag.documentos import cargar_corpus
from multiagente.rag.embeddings import VectorizadorTEI
from multiagente.rag.ingesta import ingestar


@pytest.fixture
def conexion_aislada():
    """Conexión cuyo `search_path` apunta a un esquema temporal, que se borra al terminar.

    Las migraciones y la ingesta crean sus tablas en ese esquema, de modo que las pruebas no
    tocan el índice real del corpus. La extensión `vector` sigue disponible desde `public`.
    """
    cadena = ConfiguracionBaseDatos().cadena_conexion()
    esquema = f"prueba_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(cadena, autocommit=True) as administracion:
        administracion.execute(f'CREATE SCHEMA "{esquema}"')
    try:
        with psycopg.connect(cadena, options=f"-c search_path={esquema},public") as conexion:
            yield conexion
    finally:
        with psycopg.connect(cadena, autocommit=True) as administracion:
            administracion.execute(f'DROP SCHEMA "{esquema}" CASCADE')


@pytest.fixture(scope="session")
def vectorizador():
    """Cliente del servicio de embeddings BGE-M3 de docker compose."""
    return VectorizadorTEI()


@pytest.fixture(scope="session")
def base_real(vectorizador):
    """Conexión a un esquema temporal con el corpus real ingerido con BGE-M3.

    Se crea una sola vez por ejecución, porque la ingesta tarda unos 30 s, y se borra al final.
    """
    cadena = ConfiguracionBaseDatos().cadena_conexion()
    esquema = f"prueba_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(cadena, autocommit=True) as administracion:
        administracion.execute(f'CREATE SCHEMA "{esquema}"')
    try:
        with psycopg.connect(cadena, options=f"-c search_path={esquema},public") as conexion:
            aplicar_migraciones(conexion)
            ingestar(conexion, cargar_corpus(), vectorizador)
            conexion.commit()
            yield conexion
    finally:
        with psycopg.connect(cadena, autocommit=True) as administracion:
            administracion.execute(f'DROP SCHEMA "{esquema}" CASCADE')
