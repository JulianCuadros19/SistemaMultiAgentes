"""Condición de terminado del paso 5 sin base de datos: recorrido, ciclos, retornos y caídas."""

import logging
from collections import Counter

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from multiagente.core.configuracion import ConfiguracionOrquestador
from multiagente.orquestador.ejecucion import avanzar, iniciar_sesion
from multiagente.orquestador.estado import Decision, Fase, PuntoControl
from multiagente.orquestador.grafo import Nodo, construir_grafo
from multiagente.orquestador.simulacion import (
    ErrorSimulado,
    Guion,
    ServiciosSimulados,
    aprobar,
    continuar,
    guion_completo,
    recorrer,
)
from multiagente.persistencia.puntos_control import serializador

RESPUESTAS = ["Analista", "Registrar mutaciones", "Ahorrar tiempo", "El predio debe existir"]


def compilar(simulacion: ServiciosSimulados, iteraciones: int = 3, turnos: int = 15):
    configuracion = ConfiguracionOrquestador(
        _env_file=None, max_iteraciones_correccion=iteraciones, max_turnos_elicitacion=turnos
    )
    grafo = construir_grafo(simulacion.como_servicios(), configuracion)
    return grafo.compile(checkpointer=InMemorySaver(serde=serializador()))


def guion_directo() -> Guion:
    """Guion sin rechazos humanos."""
    return Guion(
        respuestas_cliente=list(RESPUESTAS),
        decisiones={punto: [aprobar()] for punto in ("requerimientos", "especificacion", "final")},
    )


def test_recorrido_completo_con_ciclos_y_retornos(caplog):
    app = compilar(ServiciosSimulados(fallos_veredicto=1))
    with caplog.at_level(logging.WARNING, logger="langgraph"):
        recorrido = recorrer(app, guion_completo(), cliente="Realtix")

    visitas = Counter(recorrido.nodos)
    assert set(visitas) == {nodo.value for nodo in Nodo}
    # Ciclo conversacional: varias vueltas N3-N4 y salida a N5.
    assert visitas[Nodo.N3] == visitas[Nodo.N4] == 5
    # Ciclo de corrección: un veredicto fallido y una corrección pedida en N17.
    assert visitas[Nodo.N10] == visitas[Nodo.N15] == 3
    # Retornos de los tres puntos de control.
    assert visitas[Nodo.N5] == visitas[Nodo.N6] == 2
    assert visitas[Nodo.N8] == visitas[Nodo.N9] == 2
    assert visitas[Nodo.N17] == 2

    estado = app.get_state({"configurable": {"thread_id": recorrido.id_sesion}}).values
    assert recorrido.final.pausa is None
    assert estado["sesion"].fase is Fase.VALIDADO
    decisiones = [(a.punto, a.decision) for a in estado["sesion"].aprobaciones]
    assert decisiones == [
        (PuntoControl.REQUERIMIENTOS, Decision.RECHAZADO),
        (PuntoControl.REQUERIMIENTOS, Decision.APROBADO),
        (PuntoControl.ESPECIFICACION, Decision.RECHAZADO),
        (PuntoControl.ESPECIFICACION, Decision.APROBADO),
        (PuntoControl.FINAL, Decision.RECHAZADO),
        (PuntoControl.FINAL, Decision.APROBADO),
    ]
    assert estado["control"].iteracion == 3
    assert len(estado["codigo"].versiones) == 3
    assert estado["codigo"].versiones[-1].defectos_atendidos == ("El radicado debe incluir el año",)
    assert [c.id for c in estado["validacion"].plan_pruebas] == [
        "CP-RF-01-ESC-01",
        "CP-RF-01-ESC-02",
    ]
    assert set(estado["contexto"].fragmentos) == {
        "elicitacion",
        "dominio_negocio",
        "arquitecturas_referencia",
        "criterios_calidad",
    }
    assert not caplog.records, [registro.getMessage() for registro in caplog.records]


def test_n7_y_n16_corren_en_el_mismo_paso():
    recorrido = recorrer(compilar(ServiciosSimulados(fallos_veredicto=0)), guion_directo())
    tras_aprobar = next(a for a in recorrido.avances if Nodo.N6 in a.nodos)
    assert tras_aprobar.nodos[:3] in [
        (Nodo.N6, Nodo.N7, Nodo.N16),
        (Nodo.N6, Nodo.N16, Nodo.N7),
    ]


def test_rechazo_de_requerimientos_lleva_observaciones_al_dialogo():
    app = compilar(ServiciosSimulados())
    id_sesion, avance = iniciar_sesion(app, "Realtix")
    for respuesta in RESPUESTAS:
        avance = avanzar(app, id_sesion, respuesta)
    assert avance.pausa.punto == "requerimientos"
    avance = avanzar(
        app, id_sesion, {"decision": "rechazado", "revisor": "A", "observaciones": "X"}
    )
    assert avance.pausa.punto == "dialogo"
    assert avance.pausa.datos["observaciones_revisor"] == ["X"]


def test_rechazo_sin_observaciones_no_se_acepta():
    app = compilar(ServiciosSimulados())
    id_sesion, _ = iniciar_sesion(app, "Realtix")
    for respuesta in RESPUESTAS:
        avanzar(app, id_sesion, respuesta)
    with pytest.raises(ValueError, match="observaciones"):
        avanzar(app, id_sesion, {"decision": "rechazado", "revisor": "A"})


def test_escalamiento_al_agotar_las_iteraciones():
    simulacion = ServiciosSimulados(fallos_veredicto=99)
    app = compilar(simulacion, iteraciones=3)
    recorrido = recorrer(app, guion_directo())

    visitas = Counter(recorrido.nodos)
    assert visitas[Nodo.N10] == visitas[Nodo.N15] == 3
    assert Nodo.N17 not in visitas
    assert recorrido.final.pausa is None
    assert recorrido.final.fase is Fase.REQUIERE_INTERVENCION


def test_defectos_de_calidad_regresan_a_la_sintesis_sin_humano():
    recorrido = recorrer(
        compilar(ServiciosSimulados(fallos_veredicto=0, defectos_calidad=1)), guion_directo()
    )
    visitas = Counter(recorrido.nodos)
    assert visitas[Nodo.N5] == 2
    assert visitas[Nodo.N6] == 2
    assert recorrido.final.fase is Fase.VALIDADO


def test_errores_de_validacion_regresan_al_diseno_sin_humano():
    recorrido = recorrer(
        compilar(ServiciosSimulados(fallos_veredicto=0, errores_validacion=1)), guion_directo()
    )
    visitas = Counter(recorrido.nodos)
    assert visitas[Nodo.N8] == 2
    assert visitas[Nodo.N9] == 2
    assert recorrido.final.fase is Fase.VALIDADO


def test_limite_de_turnos_cierra_la_elicitacion():
    app = compilar(ServiciosSimulados(), turnos=2)
    id_sesion, avance = iniciar_sesion(app, "Realtix")
    avance = avanzar(app, id_sesion, "Analista")
    assert avance.pausa.punto == "dialogo"
    avance = avanzar(app, id_sesion, "Registrar mutaciones")
    assert avance.pausa.punto == "requerimientos"
    estado = app.get_state({"configurable": {"thread_id": id_sesion}}).values
    assert estado["conversacion"].registro.pendientes == ["beneficio", "reglas_negocio"]


def test_reanudacion_tras_una_caida_sin_repetir_pasos():
    simulacion = ServiciosSimulados(fallos_veredicto=0, fallos_ejecucion=1)
    app = compilar(simulacion)
    guion = guion_directo()
    with pytest.raises(ErrorSimulado):
        recorrer(app, guion, id_sesion="sesion-caida")

    reanudado = avanzar(app, "sesion-caida")
    assert reanudado.nodos[0] == Nodo.N11
    assert Nodo.N10 not in reanudado.nodos
    recorrido = continuar(app, "sesion-caida", guion, reanudado)
    assert recorrido.final.fase is Fase.VALIDADO
    assert simulacion.llamadas["generar"] == 1
    assert simulacion.llamadas["sintetizar"] == 1
