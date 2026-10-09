"""Condición de terminado del paso 7: una conversación produce un requerimiento de calidad.

El elicitador real (BGE-M3 en N2 y Azure OpenAI en N3 y N5) conversa con un cliente simulado
por modelo a partir del caso sintético `evaluacion/casos/elicitacion-mutacion.md`, hasta el
punto de control N6. Cuesta dinero (unos 0,006 USD por corrida, con el cliente simulado) y
requiere los servicios `db` y `embeddings` de docker compose y el archivo .env:
`pytest -m "nube and embeddings" tests/integracion/test_elicitador_nube.py`.
"""

from decimal import Decimal

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from multiagente.agentes.elicitador.servicio import crear_agente_elicitador
from multiagente.core.configuracion import (
    ConfiguracionAzureOpenAI,
    ConfiguracionModelos,
    ConfiguracionOrquestador,
)
from multiagente.interfaces.cliente_simulado import RAIZ_EVALUACION, ClienteSimulado, cargar_caso
from multiagente.llm.cliente import crear_cliente
from multiagente.llm.traza import RegistroEnMemoria
from multiagente.orquestador.ejecucion import avanzar, configuracion_hilo, iniciar_sesion
from multiagente.orquestador.grafo import construir_grafo
from multiagente.orquestador.servicios import Servicios
from multiagente.orquestador.simulacion import ServiciosSimulados
from multiagente.persistencia.puntos_control import serializador

pytestmark = [pytest.mark.nube, pytest.mark.embeddings]

CASO = RAIZ_EVALUACION / "casos" / "elicitacion-mutacion.md"
LATENCIA_MAXIMA_TURNO_MS = 15_000
"""RNF-01: cada turno de la conversación responde en menos de 15 segundos."""


def test_una_conversacion_produce_un_requerimiento_que_pasa_la_calidad(base_real, vectorizador):
    registro = RegistroEnMemoria()
    cliente_modelo = crear_cliente(ConfiguracionAzureOpenAI())
    caso = cargar_caso(CASO)
    elicitador = crear_agente_elicitador(base_real, registro, cliente_modelo, vectorizador)
    simulado = ClienteSimulado(cliente_modelo, ConfiguracionModelos().n3_dialogo, caso, registro)
    simulados = ServiciosSimulados()
    servicios = Servicios(
        elicitador=elicitador, arquitecto=simulados, desarrollador=simulados, tester=simulados
    )
    configuracion = ConfiguracionOrquestador(_env_file=None)
    app = construir_grafo(servicios, configuracion).compile(
        checkpointer=InMemorySaver(serde=serializador())
    )

    id_sesion, avance = iniciar_sesion(app, caso.cliente, caso.proyecto, caso.necesidad)
    preguntas: list[str] = []
    try:
        while avance.pausa is not None and avance.pausa.punto == "dialogo":
            pregunta = avance.pausa.datos["pregunta"]
            preguntas.append(pregunta)
            conversacion = app.get_state(configuracion_hilo(id_sesion)).values["conversacion"]
            avance = avanzar(app, id_sesion, simulado.responder(conversacion, pregunta))
    except Exception:
        # Para diagnosticar con un modelo estocástico: la conversación y el registro del fallo.
        conversacion = app.get_state(configuracion_hilo(id_sesion)).values["conversacion"]
        for turno in conversacion.turnos:
            print(f"[{turno.emisor}] {turno.texto}")
        print(conversacion.registro.model_dump_json(indent=1))
        raise

    estado = app.get_state(configuracion_hilo(id_sesion)).values
    llamadas = registro.llamadas
    for llamada in llamadas:
        print(
            f"{llamada.nodo:17} {llamada.latencia_ms:6} ms · entrada {llamada.consumo.entrada:6}"
            f" (caché {llamada.consumo.entrada_cacheada}) · salida {llamada.consumo.salida:5}"
            f" (razonamiento {llamada.consumo.razonamiento}) · USD {llamada.costo_usd:.6f}"
        )
    sistema = sum(
        (llamada.costo_usd for llamada in llamadas if llamada.nodo != "cliente_simulado"),
        Decimal(0),
    )
    print(f"Turnos: {len(preguntas)} · costo del sistema USD {sistema:.6f}")

    # Llega a la aprobación humana sin defectos de calidad (RF-07).
    assert avance.pausa is not None and avance.pausa.punto == "requerimientos"
    assert avance.pausa.datos["defectos"] == []
    requerimientos = estado["requerimientos"]
    assert requerimientos.historias and requerimientos.requerimientos
    assert estado["conversacion"].registro.resumen_confirmado

    # Cada requerimiento referencia fragmentos que de verdad se recuperaron (RF-04).
    recuperadas = {
        fragmento.referencia
        for fragmentos in estado["contexto"].fragmentos.values()
        for fragmento in fragmentos
    }
    for requerimiento in requerimientos.requerimientos:
        referencias = requerimientos.referencias[requerimiento.id_requerimiento]
        assert referencias and set(referencias) <= recuperadas

    # Una pregunta por turno (RNF-08), turnos dentro del límite y respuesta a tiempo (RNF-01).
    assert all(pregunta.count("?") == 1 for pregunta in preguntas), preguntas
    assert estado["conversacion"].turnos_cliente <= configuracion.max_turnos_elicitacion
    lentas = [
        llamada.latencia_ms
        for llamada in llamadas
        if llamada.nodo == "N3" and llamada.latencia_ms >= LATENCIA_MAXIMA_TURNO_MS
    ]
    assert not lentas, f"Turnos de N3 que superan el RNF-01: {lentas} ms"
