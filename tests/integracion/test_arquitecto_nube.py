"""Condición de terminado del paso 8: la especificación generada pasa las validaciones del Anexo B.

Para cada caso sintético de `evaluacion/casos/diseno-*.json`, un elicitador fijo entrega los
requerimientos aprobados y el arquitecto real (BGE-M3 en N7, Azure OpenAI en N8) diseña hasta la
aprobación humana de N9. Cuesta dinero (unos 0,08 USD por caso con esfuerzo `low`) y requiere los
servicios `db` y `embeddings` de docker compose y el archivo .env:
`pytest -m "nube and embeddings" tests/integracion/test_arquitecto_nube.py`.
"""

import re
from decimal import Decimal

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from multiagente.agentes.arquitecto.servicio import crear_agente_arquitecto
from multiagente.core.configuracion import ConfiguracionAzureOpenAI, ConfiguracionOrquestador
from multiagente.interfaces.casos import cargar_caso_diseno
from multiagente.interfaces.cliente_simulado import RAIZ_EVALUACION
from multiagente.llm.cliente import crear_cliente
from multiagente.llm.traza import RegistroEnMemoria
from multiagente.orquestador.ejecucion import avanzar, configuracion_hilo, iniciar_sesion
from multiagente.orquestador.grafo import construir_grafo
from multiagente.orquestador.servicios import Servicios
from multiagente.orquestador.simulacion import ElicitadorFijo, ServiciosSimulados, aprobar
from multiagente.persistencia.puntos_control import serializador

pytestmark = [pytest.mark.nube, pytest.mark.embeddings]

CASOS = sorted((RAIZ_EVALUACION / "casos").glob("diseno-*.json"))


@pytest.mark.parametrize("archivo", CASOS, ids=[caso.stem for caso in CASOS])
def test_la_especificacion_generada_pasa_el_anexo_b(base_real, vectorizador, archivo):
    caso = cargar_caso_diseno(archivo)
    registro = RegistroEnMemoria()
    arquitecto = crear_agente_arquitecto(
        base_real, registro, crear_cliente(ConfiguracionAzureOpenAI()), vectorizador
    )
    simulados = ServiciosSimulados()
    servicios = Servicios(
        elicitador=ElicitadorFijo(caso.sintesis),
        arquitecto=arquitecto,
        desarrollador=simulados,
        tester=simulados,
    )
    app = construir_grafo(servicios, ConfiguracionOrquestador(_env_file=None)).compile(
        checkpointer=InMemorySaver(serde=serializador())
    )
    id_sesion, _ = iniciar_sesion(app, caso.cliente, caso.proyecto, caso.necesidad)
    avance = avanzar(app, id_sesion, aprobar())

    arquitectura = app.get_state(configuracion_hilo(id_sesion)).values["arquitectura"]
    especificacion = arquitectura.especificacion
    for llamada in registro.llamadas:
        print(
            f"{llamada.prompt:34} {llamada.latencia_ms / 1000:6.1f} s · salida "
            f"{llamada.consumo.salida:5} (razonamiento {llamada.consumo.razonamiento}) · "
            f"USD {llamada.costo_usd:.5f}"
        )
    costo = sum((llamada.costo_usd for llamada in registro.llamadas), Decimal(0))
    print(
        f"{caso.id}: {especificacion.arquitectura_base} (candidatas {caso.candidatas}) · "
        f"{len(especificacion.modulos)} módulos · {arquitectura.disenos} diseños · USD {costo:.5f}"
    )

    # Llega a la aprobación humana sin errores: pasa las tres validaciones del Anexo B.
    assert avance.pausa is not None and avance.pausa.punto == "especificacion"
    assert avance.pausa.datos["errores"] == []
    assert arquitecto.validar(especificacion, caso_requerimientos(app, id_sesion)) == []

    # La elección respeta los criterios de selección del catálogo (arq-003).
    assert especificacion.arquitectura_base in caso.candidatas
    registro_decision = arquitectura.registro_decision
    assert f"Opción elegida: «{especificacion.arquitectura_base}" in registro_decision
    assert not re.search(r"\bF\d+\b", registro_decision)


def caso_requerimientos(app, id_sesion):
    return app.get_state(configuracion_hilo(id_sesion)).values["requerimientos"]
