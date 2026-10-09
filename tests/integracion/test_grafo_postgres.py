"""Condición de terminado del paso 5 con PostgreSQL: la sesión se reanuda tras interrumpirla.

Cada bloque `with abrir_checkpointer()` representa un proceso distinto: al salir se cierra la
conexión y en el siguiente bloque el grafo se reconstruye desde cero, como tras un reinicio.
Requiere el contenedor levantado con `docker compose up -d --wait` y el archivo .env.
"""

import logging
import uuid

import pytest

from multiagente.core.configuracion import ConfiguracionOrquestador
from multiagente.orquestador.ejecucion import (
    Avance,
    avanzar,
    configuracion_hilo,
    iniciar_sesion,
    pausa_pendiente,
)
from multiagente.orquestador.estado import Fase
from multiagente.orquestador.grafo import Nodo, construir_grafo
from multiagente.orquestador.simulacion import (
    ErrorSimulado,
    ServiciosSimulados,
    continuar,
    guion_completo,
)
from multiagente.persistencia.puntos_control import abrir_checkpointer

pytestmark = pytest.mark.integracion

CONFIGURACION = ConfiguracionOrquestador(
    _env_file=None, max_iteraciones_correccion=3, max_turnos_elicitacion=15
)


def compilar(checkpointer, simulacion: ServiciosSimulados):
    grafo = construir_grafo(simulacion.como_servicios(), CONFIGURACION)
    return grafo.compile(checkpointer=checkpointer)


@pytest.fixture
def id_sesion():
    identificador = f"prueba-{uuid.uuid4()}"
    yield identificador
    with abrir_checkpointer() as checkpointer:
        checkpointer.delete_thread(identificador)


def test_conversacion_se_reanuda_desde_el_ultimo_turno(id_sesion, caplog):
    guion = guion_completo()
    with abrir_checkpointer() as checkpointer:
        app = compilar(checkpointer, ServiciosSimulados())
        _, avance = iniciar_sesion(app, "Realtix", guion.proyecto, guion.necesidad, id_sesion)
        primero = avanzar(app, id_sesion, guion.responder("dialogo"))
        assert primero.pausa.punto == "dialogo"
        visitados = [*avance.nodos, *primero.nodos]

    with caplog.at_level(logging.WARNING, logger="langgraph"), abrir_checkpointer() as checkpointer:
        app = compilar(checkpointer, ServiciosSimulados())
        pausa = pausa_pendiente(app, id_sesion)
        estado = app.get_state(configuracion_hilo(id_sesion)).values
        assert pausa.punto == "dialogo"
        assert pausa.datos["turno"] == 3
        assert estado["conversacion"].turnos_cliente == 2
        assert estado["conversacion"].registro.rol == "Analista de conservación catastral"

        reanudado = Avance(nodos=(), pausa=pausa, fase=estado["sesion"].fase)
        recorrido = continuar(app, id_sesion, guion, reanudado)

    assert recorrido.final.fase is Fase.VALIDADO
    assert set(visitados + recorrido.nodos) == {nodo.value for nodo in Nodo}
    assert not caplog.records, [registro.getMessage() for registro in caplog.records]


def test_ejecucion_se_reanuda_tras_una_caida(id_sesion):
    guion = guion_completo()
    with abrir_checkpointer() as checkpointer:
        app = compilar(checkpointer, ServiciosSimulados(fallos_ejecucion=1))
        _, avance = iniciar_sesion(app, "Realtix", guion.proyecto, guion.necesidad, id_sesion)
        with pytest.raises(ErrorSimulado):
            continuar(app, id_sesion, guion, avance)

    with abrir_checkpointer() as checkpointer:
        simulacion = ServiciosSimulados()
        app = compilar(checkpointer, simulacion)
        reanudado = avanzar(app, id_sesion)
        assert reanudado.nodos[0] == Nodo.N11
        recorrido = continuar(app, id_sesion, guion, reanudado)

    assert recorrido.final.fase is Fase.VALIDADO
    assert simulacion.llamadas["sintetizar"] == 0
    assert simulacion.llamadas["disenar"] == 0
