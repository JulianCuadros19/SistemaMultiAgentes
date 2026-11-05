"""Condición de terminado del paso 13: el presupuesto detiene una ejecución que lo supera.

Con el elicitador real (BGE-M3 en N2 y Azure OpenAI en N3) y respuestas fijas del cliente, una
sesión con un presupuesto de 0,005 USD se detiene a los pocos turnos, antes de que N3 vuelva a
llamar al modelo (RNF-10). Una persona lo amplía y la sesión sigue un turno más. Al final, la
traza en PostgreSQL tiene, por nodo, los prompts, los tokens, el costo y los tiempos (RF-34).

Cuesta unos 0,03 USD y requiere el archivo .env y los servicios `db` y `embeddings`:
`pytest -m "nube and embeddings" tests/integracion/test_presupuesto_nube.py`.
"""

from decimal import Decimal

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from multiagente.agentes.elicitador.servicio import crear_agente_elicitador
from multiagente.core.configuracion import ConfiguracionAzureOpenAI, ConfiguracionOrquestador
from multiagente.interfaces.cliente_simulado import RAIZ_EVALUACION, cargar_caso
from multiagente.interfaces.operacion import Operador
from multiagente.llm.cliente import crear_cliente
from multiagente.llm.prompts import cargar_prompt
from multiagente.llm.traza import RegistroEnMemoria
from multiagente.orquestador.grafo import Nodo, construir_grafo
from multiagente.orquestador.servicios import Servicios
from multiagente.orquestador.simulacion import ServiciosSimulados
from multiagente.persistencia.ejecuciones import TrazaEjecuciones
from multiagente.persistencia.puntos_control import serializador

pytestmark = [pytest.mark.nube, pytest.mark.embeddings]

PRESUPUESTO = Decimal("0.005")
RESPUESTAS = [
    "Lo usa el analista de conservación catastral.",
    "Para tramitar el cambio de propietario del predio y hacerle seguimiento sin perder papeles.",
    "La solicitud se acepta solo si el número predial existe en la base catastral.",
    "Se necesita el número predial de 30 dígitos y la fecha del documento soporte.",
    "Se entrega un radicado único con el estado inicial en trámite.",
    "Si el número predial no existe, la solicitud se rechaza con un mensaje.",
]


def test_el_presupuesto_detiene_una_sesion_real_que_lo_supera(base_real, vectorizador, pool_traza):
    caso = cargar_caso(RAIZ_EVALUACION / "casos" / "elicitacion-mutacion.md")
    registro = RegistroEnMemoria()
    simulados = ServiciosSimulados(fallos_veredicto=0)
    servicios = Servicios(
        elicitador=crear_agente_elicitador(
            base_real, registro, crear_cliente(ConfiguracionAzureOpenAI()), vectorizador
        ),
        arquitecto=simulados,
        desarrollador=simulados,
        tester=simulados,
    )
    traza = TrazaEjecuciones(pool_traza)
    configuracion = ConfiguracionOrquestador(
        _env_file=None, presupuesto_maximo_por_modulo_usd=PRESUPUESTO
    )
    app = construir_grafo(servicios, configuracion, traza).compile(
        checkpointer=InMemorySaver(serde=serializador())
    )
    operador = Operador(app, traza=traza)
    id_sesion = operador.iniciar(caso.cliente, caso.proyecto, caso.necesidad)
    respuestas = list(RESPUESTAS)
    while (vista := operador.vista(id_sesion)).pausa.punto == "dialogo" and respuestas:
        operador.responder(id_sesion, respuestas.pop(0))

    # El presupuesto detuvo la sesión antes de que N3 volviera a llamar al modelo.
    vista = operador.vista(id_sesion)
    assert vista.pausa is not None and vista.pausa.punto == "presupuesto", vista.describir()
    assert vista.costo_usd >= PRESUPUESTO
    gastado_en_la_pausa = sum((llamada.costo_usd for llamada in registro.llamadas), Decimal(0))
    assert vista.costo_usd == gastado_en_la_pausa
    print(f"\n{vista.describir()} · {len(registro.llamadas)} llamadas")

    # Ampliado, la sesión sigue: N3 procesa la respuesta pendiente con el modelo.
    llamadas = len(registro.llamadas)
    avance = operador.ampliar_presupuesto(
        id_sesion, "Laura", vista.costo_usd + Decimal("0.05"), "Prueba del paso 13"
    )
    assert avance.pausa.punto == "dialogo"
    operador.responder(id_sesion, respuestas.pop(0))
    assert len(registro.llamadas) > llamadas
    control = operador.estado(id_sesion)["control"]
    assert control.ampliaciones[0].revisor == "Laura"
    assert control.costo_acumulado_usd == sum(
        (llamada.costo_usd for llamada in registro.llamadas), Decimal(0)
    )

    # Criterio del RF-34: por nodo, los prompts, los tokens, el costo y los tiempos.
    ejecuciones = operador.ejecuciones(id_sesion)
    assert {Nodo.N1.value, Nodo.N2.value, Nodo.N3.value} <= {e.nodo for e in ejecuciones}
    dialogos = [e for e in ejecuciones if e.nodo == Nodo.N3.value]
    assert all(e.llamadas and e.duracion_ms > 0 for e in dialogos)
    prompts = {llamada.prompt for e in dialogos for llamada in e.llamadas}
    assert {
        cargar_prompt("elicitador", "extraccion").identificador,
        cargar_prompt("elicitador", "dialogo").identificador,
    } <= prompts
    assert all(
        llamada.consumo.entrada > 0 and llamada.costo_usd > 0
        for e in dialogos
        for llamada in e.llamadas
    )
    assert sum(e.costo_usd for e in ejecuciones) == control.costo_acumulado_usd
    print(operador.traza(id_sesion))
