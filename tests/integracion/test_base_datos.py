"""Condición de terminado del paso 2: PostgreSQL acepta conexiones y pgvector está activa.

Requiere el contenedor levantado con `docker compose up -d --wait` y el archivo .env.
"""

import psycopg
import pytest

from multiagente.core.configuracion import ConfiguracionBaseDatos

pytestmark = pytest.mark.integracion


@pytest.fixture
def conexion():
    with psycopg.connect(ConfiguracionBaseDatos().cadena_conexion()) as conexion:
        yield conexion


def test_servidor_es_postgresql_16(conexion):
    version = conexion.execute("SHOW server_version_num").fetchone()[0]
    assert int(version) // 10000 == 16


def test_extension_vector_esta_instalada(conexion):
    fila = conexion.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
    assert fila.fetchone() is not None


def test_distancia_vectorial_funciona(conexion):
    distancia = conexion.execute("SELECT '[1,2,3]'::vector <-> '[1,2,4]'::vector").fetchone()[0]
    assert distancia == pytest.approx(1.0)
