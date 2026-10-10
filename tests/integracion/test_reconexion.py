"""Los pools de un proceso de larga vida, como la web, sobreviven a un reinicio de PostgreSQL.

El reinicio se simula terminando solo las conexiones de esta prueba, que se reconocen por su
`application_name`: así no se afectan otras sesiones abiertas en la misma base.
Requiere `docker compose up -d --wait`:
`pytest -m integracion tests/integracion/test_reconexion.py`.
"""

import uuid

import psycopg
import pytest

from multiagente.core.configuracion import ConfiguracionBaseDatos, ConfiguracionOrquestador
from multiagente.interfaces.operacion import Operador
from multiagente.orquestador.grafo import construir_grafo
from multiagente.orquestador.simulacion import ServiciosSimulados
from multiagente.persistencia.conexiones import ConexionDePool, abrir_pool
from multiagente.persistencia.puntos_control import abrir_checkpointer_compartido

pytestmark = pytest.mark.integracion


def terminar_conexiones(aplicacion: str) -> int:
    """Termina las conexiones de una aplicación, como lo haría un reinicio de la base."""
    with psycopg.connect(ConfiguracionBaseDatos().cadena_conexion(), autocommit=True) as admin:
        filas = admin.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE application_name = %s",
            (aplicacion,),
        ).fetchall()
    return len(filas)


def test_los_pools_se_reconectan_tras_perder_sus_conexiones():
    aplicacion = f"prueba-reconexion-{uuid.uuid4().hex[:8]}"
    with (
        abrir_pool(aplicacion=aplicacion) as pool,
        abrir_checkpointer_compartido(aplicacion=aplicacion) as puntos,
    ):
        conexion = ConexionDePool(pool)
        app = construir_grafo(
            ServiciosSimulados().como_servicios(), ConfiguracionOrquestador(_env_file=None)
        ).compile(checkpointer=puntos)
        operador = Operador(app)
        id_sesion = operador.iniciar("Cliente", "Proyecto", "Registrar mutaciones")
        try:
            assert conexion.execute("SELECT 1").fetchall() == [(1,)]
            assert terminar_conexiones(aplicacion) >= 2

            # Tras perder todas sus conexiones, ambos pools siguen funcionando.
            assert conexion.execute("SELECT 1").fetchall() == [(1,)]
            assert operador.vista(id_sesion).pausa.punto == "dialogo"
            avance = operador.responder(id_sesion, "Analista de conservación catastral")
            assert avance.pausa.punto == "dialogo"
            assert id_sesion in {vista.id_sesion for vista in operador.sesiones()}
        finally:
            puntos.delete_thread(id_sesion)
