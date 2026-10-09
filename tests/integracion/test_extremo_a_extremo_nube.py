"""Condición de terminado del paso 11: un módulo completo sale aprobado por el tester.

Para cada caso de `evaluacion/casos/elicitacion-*.md`, una sesión recorre el flujo completo con
los cuatro agentes reales, desde la necesidad del cliente:
- el elicitador conversa con un cliente simulado y sintetiza los requerimientos (N2 a N6);
- el arquitecto diseña (N7 a N9);
- el desarrollador genera el módulo (N10);
- el tester lo valida (N11 a N14) en el ciclo de corrección, hasta la aprobación final (N17).

Las personas de los tres puntos de control deciden como lo haría el equipo:
- en N6, si llegan defectos escalados, como una pregunta abierta para el cliente, el analista
  rechaza una vez con ellos como observaciones y el diálogo los resuelve (RNF-09); si vuelven, la
  corrida falla;
- en N9 se aprueba una especificación sin errores del Anexo B;
- en N17 se aprueba el módulo que aprobó el tester.

El módulo debe salir aprobado dentro del límite de iteraciones y en 20 minutos o menos de tiempo
del sistema (RNF-01).

Cuesta dinero (de 0,15 a 0,55 USD por caso) y requiere el archivo .env, los servicios `db` y
`embeddings` y la imagen del entorno aislado:
`pytest -m "nube and embeddings and sandbox" tests/integracion/test_extremo_a_extremo_nube.py`.
"""

import logging
import time
from collections import Counter, defaultdict
from decimal import Decimal

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from multiagente.agentes.servicios import crear_servicios
from multiagente.core.configuracion import (
    ConfiguracionAzureOpenAI,
    ConfiguracionModelos,
    ConfiguracionOrquestador,
)
from multiagente.interfaces.cliente_simulado import RAIZ_EVALUACION, ClienteSimulado, cargar_caso
from multiagente.llm.cliente import crear_cliente
from multiagente.llm.traza import RegistroEnMemoria
from multiagente.orquestador.ejecucion import (
    avanzar,
    configuracion_hilo,
    iniciar_sesion,
    validaciones,
)
from multiagente.orquestador.estado import Decision, Fase, PuntoControl, Severidad
from multiagente.orquestador.grafo import construir_grafo
from multiagente.orquestador.simulacion import aprobar, rechazar
from multiagente.persistencia.puntos_control import serializador

pytestmark = [pytest.mark.nube, pytest.mark.embeddings, pytest.mark.sandbox]

CASOS = sorted((RAIZ_EVALUACION / "casos").glob("elicitacion-*.md"))
TIEMPO_MAXIMO_MODULO_S = 20 * 60
"""RNF-01: el ciclo completo de un módulo no excede los 20 minutos."""
RECHAZOS_N6 = 1
"""Rechazos del analista en N6 por defectos escalados antes de dar la corrida por fallida."""


def observaciones_del_analista(datos: dict) -> str:
    """Observaciones con que el analista devuelve al diálogo lo pendiente con el cliente."""
    preguntas = [p for historia in datos["historias"] for p in historia["preguntas_abiertas"]]
    return "Resolver con el cliente antes de aprobar: " + "; ".join(
        [*datos["defectos"], *preguntas]
    )


@pytest.mark.parametrize("archivo", CASOS, ids=[caso.stem for caso in CASOS])
def test_un_modulo_completo_sale_aprobado_por_el_tester(
    base_real, vectorizador, entorno_aislado, archivo, caplog
):
    caplog.set_level(logging.WARNING, logger="multiagente.llm.invocador")
    caso = cargar_caso(archivo)
    registro = RegistroEnMemoria()
    cliente_modelo = crear_cliente(ConfiguracionAzureOpenAI())
    servicios = crear_servicios(base_real, registro, cliente_modelo, vectorizador, entorno_aislado)
    simulado = ClienteSimulado(
        cliente_modelo, ConfiguracionModelos().despliegue_cliente_simulado, caso, registro
    )
    configuracion = ConfiguracionOrquestador(_env_file=None)
    app = construir_grafo(servicios, configuracion).compile(
        checkpointer=InMemorySaver(serde=serializador())
    )

    # Solo cuenta el tiempo del sistema: el cliente simulado responde fuera de `avanzar`.
    inicio = time.perf_counter()
    id_sesion, avance = iniciar_sesion(app, caso.cliente, caso.proyecto, caso.necesidad)
    sistema_s = time.perf_counter() - inicio
    # Duración de cada respuesta al cliente: hasta la siguiente pregunta o hasta N6.
    turnos = [sistema_s]
    cierres: list[float] = []
    pausas: list[str] = []
    rechazos_n6: list[str] = []
    final = None
    while avance.pausa is not None:
        pausa = avance.pausa
        pausas.append(pausa.punto)
        if pausa.punto == "dialogo":
            conversacion = app.get_state(configuracion_hilo(id_sesion)).values["conversacion"]
            respuesta = simulado.responder(conversacion, pausa.datos["pregunta"])
        elif pausa.punto == "requerimientos" and pausa.datos["defectos"]:
            assert len(rechazos_n6) < RECHAZOS_N6, (pausa.datos["defectos"], rechazos_n6)
            rechazos_n6.append(observaciones_del_analista(pausa.datos))
            respuesta = rechazar(rechazos_n6[-1], "Analista")
        elif pausa.punto == "requerimientos":
            respuesta = aprobar("Analista")
        elif pausa.punto == "especificacion":
            assert pausa.datos["errores"] == [], pausa.datos["errores"]
            respuesta = aprobar("Arquitecto")
        else:
            final = pausa.datos
            respuesta = aprobar("Revisor")
        inicio = time.perf_counter()
        avance = avanzar(app, id_sesion, respuesta)
        segundos = time.perf_counter() - inicio
        sistema_s += segundos
        if pausa.punto == "dialogo":
            pregunta = avance.pausa is not None and avance.pausa.punto == "dialogo"
            (turnos if pregunta else cierres).append(segundos)

    estado = app.get_state(configuracion_hilo(id_sesion)).values
    historial = validaciones(app, id_sesion)
    imprimir_resumen(caso.id, estado, historial, registro, caplog.messages, sistema_s)
    print(
        f"  Turnos de diálogo: {len(turnos)} · máximo {max(turnos):.1f} s · cierre de la "
        f"elicitación: {[round(segundos, 1) for segundos in cierres]} s"
    )
    for observaciones in rechazos_n6:
        print(f"  Rechazo en N6: {observaciones}")

    # El módulo llega a N17 aprobado por el tester, sin escalar por el límite de iteraciones.
    assert estado["sesion"].fase is not Fase.REQUIERE_INTERVENCION, historial[-1][1].reporte
    assert final is not None and pausas.count("final") == 1
    assert final["veredicto"] == "aprobado", final["reporte"]
    assert estado["control"].iteracion <= configuracion.max_iteraciones_correccion

    # Cada escenario aprobado tiene su caso en el plan de N16, y cada caso cumple con su prueba
    # como evidencia (RF-21).
    validacion = estado["validacion"]
    escenarios = [
        f"CP-{r.id_requerimiento}-{e.id}"
        for r in estado["requerimientos"].requerimientos
        for e in r.criterios_aceptacion
    ]
    assert [caso_prueba.id for caso_prueba in validacion.plan_pruebas] == escenarios
    assert {v.id_caso for v in validacion.veredictos} == set(escenarios)
    assert all(v.cumple and v.pruebas for v in validacion.veredictos), validacion.reporte

    # Con el umbral 0, no queda ningún hallazgo de severidad alta ni media (cal-sv).
    bloqueantes = [h for h in validacion.hallazgos if h.severidad is not Severidad.BAJA]
    assert bloqueantes == [], validacion.reporte

    # La persona aprueba en N17 y el flujo cierra con las tres aprobaciones (RF-38, RNF-09).
    assert estado["sesion"].fase is Fase.VALIDADO
    aprobaciones = [(a.punto, a.decision) for a in estado["sesion"].aprobaciones]
    assert aprobaciones == [
        *[(PuntoControl.REQUERIMIENTOS, Decision.RECHAZADO)] * len(rechazos_n6),
        (PuntoControl.REQUERIMIENTOS, Decision.APROBADO),
        (PuntoControl.ESPECIFICACION, Decision.APROBADO),
        (PuntoControl.FINAL, Decision.APROBADO),
    ]

    # RNF-01: el ciclo completo del módulo cabe en 20 minutos de tiempo del sistema.
    assert sistema_s <= TIEMPO_MAXIMO_MODULO_S, f"{sistema_s / 60:.1f} min"


def imprimir_resumen(id_caso, estado, historial, registro, reintentos, sistema_s):
    """Imprime lo que se mide en el paso 11: versiones, iteraciones, tiempo y costo por nodo."""
    especificacion = estado["arquitectura"].especificacion
    if especificacion is not None:
        print(
            f"\n{id_caso}: {especificacion.arquitectura_base} · {len(especificacion.modulos)} "
            f"módulos · {len(estado['requerimientos'].requerimientos)} RF · "
            f"{len(estado['validacion'].plan_pruebas)} casos"
        )
    for version, validacion in historial:
        severidades = Counter(h.severidad.value for h in validacion.hallazgos)
        reglas = Counter(h.regla for h in validacion.hallazgos if h.severidad is not Severidad.BAJA)
        incumplidos = [v.id_caso for v in validacion.veredictos if not v.cumple]
        print(
            f"  v{version.numero}: {validacion.veredicto} · hallazgos {dict(severidades)} · "
            f"bloqueantes {dict(reglas)} · casos incumplidos {incumplidos}"
        )
    print(
        f"  Fase {estado['sesion'].fase} · iteraciones {estado['control'].iteracion} · "
        f"tiempo del sistema {sistema_s / 60:.1f} min"
    )
    por_nodo = defaultdict(list)
    for llamada in registro.llamadas:
        por_nodo[llamada.nodo].append(llamada)
    for nodo, llamadas in sorted(por_nodo.items()):
        costo = sum((llamada.costo_usd for llamada in llamadas), Decimal(0))
        latencia = sum(llamada.latencia_ms for llamada in llamadas) / 1000
        print(f"  {nodo:17} {len(llamadas):3} llamadas · {latencia:6.1f} s · USD {costo:.4f}")
    sistema = sum(
        (llamada.costo_usd for llamada in registro.llamadas if llamada.nodo != "cliente_simulado"),
        Decimal(0),
    )
    print(f"  Costo del sistema: USD {sistema:.4f}")
    for reintento in reintentos:
        print(f"  Reintento: {reintento[:300]}")
