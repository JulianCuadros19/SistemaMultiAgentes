"""Conexiones aisladas para las pruebas que escriben en la base de conocimiento."""

import uuid

import psycopg
import pytest

from multiagente.core.configuracion import ConfiguracionBaseDatos


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
