"""Condición de terminado del paso 5 sin base de datos: recorrido, ciclos, retornos y caídas."""

import logging
from collections import Counter

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from multiagente.core.configuracion import ConfiguracionOrquestador
from multiagente.orquestador.ejecucion import avanzar, configuracion_hilo, iniciar_sesion
from multiagente.orquestador.estado import Decision, Emisor, Fase, PuntoControl
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

NECESIDAD = "Registrar mutaciones"
RESPUESTAS = [
    "Analista",
    "Ahorrar tiempo",
    "El predio debe existir",
    "Número predial",
    "Radicado",
    "Si el predio no existe, se rechaza",
    "Sí, es correcto",
]


def compilar(
    simulacion: ServiciosSimulados, iteraciones: int = 3, turnos: int = 15, correcciones: int = 2
):
    configuracion = ConfiguracionOrquestador(
        _env_file=None,
        max_iteraciones_correccion=iteraciones,
        max_turnos_elicitacion=turnos,
        max_correcciones_calidad=correcciones,
    )
    grafo = construir_grafo(simulacion.como_servicios(), configuracion)
    return grafo.compile(checkpointer=InMemorySaver(serde=serializador()))


def guion_directo() -> Guion:
    """Guion sin rechazos humanos."""
    return Guion(
        necesidad=NECESIDAD,
        respuestas_cliente=list(RESPUESTAS),
        decisiones={punto: [aprobar()] for punto in ("requerimientos", "especificacion", "final")},
    )


def test_recorrido_completo_con_ciclos_y_retornos(caplog):
    app = compilar(ServiciosSimulados(fallos_veredicto=1))
    with caplog.at_level(logging.WARNING, logger="langgraph"):
        recorrido = recorrer(app, guion_completo(), cliente="Realtix")

    visitas = Counter(recorrido.nodos)
    assert set(visitas) == {nodo.value for nodo in Nodo}
    # Ciclo conversacional: la necesidad y siete respuestas; tras el rechazo, una pregunta sin
    # esperar y dos respuestas más.
    assert visitas[Nodo.N3] == visitas[Nodo.N4] == 11
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
    requerimientos = estado["requerimientos"]
    assert requerimientos.sintesis == 2
    assert requerimientos.requerimientos[0].version == "0.2"
    assert requerimientos.requerimientos[0].proyecto == "Proyecto simulado"
    assert requerimientos.referencias["RF-01"] == (
        "eli-006 v1.0 · Guía de preguntas (simulada)",
        "dom-001 v1.0 · Glosario catastral (simulado)",
    )
    assert "El documento soporte no puede tener fecha posterior a la radicación" in (
        estado["conversacion"].registro.reglas_negocio
    )
    assert not caplog.records, [registro.getMessage() for registro in caplog.records]


def test_la_necesidad_abre_la_sesion_y_n3_no_espera_al_inicio():
    simulacion = ServiciosSimulados()
    app = compilar(simulacion)
    id_sesion, avance = iniciar_sesion(app, "Realtix", "Catastro", NECESIDAD)
    assert avance.nodos == (Nodo.N1, Nodo.N2, Nodo.N3, Nodo.N4)
    assert avance.pausa.punto == "dialogo"
    assert avance.pausa.datos["turno"] == 2
    estado = app.get_state(configuracion_hilo(id_sesion)).values
    conversacion = estado["conversacion"]
    assert [turno.emisor for turno in conversacion.turnos] == [Emisor.CLIENTE, Emisor.ELICITADOR]
    assert conversacion.necesidad == NECESIDAD
    assert conversacion.registro.funcionalidad == NECESIDAD
    assert conversacion.turnos_procesados == 2
    assert estado["sesion"].proyecto == "Catastro"
    assert estado["control"].limite_correcciones == 2
    assert simulacion.llamadas["dialogar"] == 1


def test_n7_y_n16_corren_en_el_mismo_paso():
    recorrido = recorrer(compilar(ServiciosSimulados(fallos_veredicto=0)), guion_directo())
    tras_aprobar = next(a for a in recorrido.avances if Nodo.N6 in a.nodos)
    assert tras_aprobar.nodos[:3] in [
        (Nodo.N6, Nodo.N7, Nodo.N16),
        (Nodo.N6, Nodo.N16, Nodo.N7),
    ]


def test_rechazo_de_requerimientos_lleva_observaciones_al_dialogo():
    app = compilar(ServiciosSimulados())
    id_sesion, avance = iniciar_sesion(app, "Realtix", "Catastro", NECESIDAD)
    for respuesta in RESPUESTAS:
        avance = avanzar(app, id_sesion, respuesta)
    assert avance.pausa.punto == "requerimientos"
    assert avance.pausa.datos["defectos"] == []
    assert avance.pausa.datos["referencias"]["RF-01"]
    avance = avanzar(
        app, id_sesion, {"decision": "rechazado", "revisor": "A", "observaciones": "X"}
    )
    # Sin esperar al cliente, el elicitador vuelve a pedir la confirmación del resumen.
    assert avance.nodos == (Nodo.N6, Nodo.N3, Nodo.N4)
    assert avance.pausa.punto == "dialogo"
    assert avance.pausa.datos["observaciones_revisor"] == ["X"]
    assert avance.pausa.datos["pregunta"] == "Le resumo lo que entendí; ¿es correcto?"
    estado = app.get_state(configuracion_hilo(id_sesion)).values
    assert estado["conversacion"].registro.pendientes == ["confirmacion"]


def test_rechazo_sin_observaciones_no_se_acepta():
    app = compilar(ServiciosSimulados())
    id_sesion, _ = iniciar_sesion(app, "Realtix", "Catastro", NECESIDAD)
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


def test_defectos_persistentes_escalan_al_analista():
    app = compilar(ServiciosSimulados(defectos_calidad=99), correcciones=2)
    id_sesion, avance = iniciar_sesion(app, "Realtix", "Catastro", NECESIDAD)
    for respuesta in RESPUESTAS:
        avance = avanzar(app, id_sesion, respuesta)

    # Una síntesis y dos correcciones automáticas; después, la persona ve los defectos.
    assert Counter(avance.nodos)[Nodo.N5] == 3
    assert avance.pausa.punto == "requerimientos"
    defecto = "Defecto simulado: la regla de negocio es ambigua"
    assert avance.pausa.datos["defectos"] == [defecto]

    avance = avanzar(app, id_sesion, aprobar())
    assert Nodo.N7 in avance.nodos
    requerimientos = app.get_state(configuracion_hilo(id_sesion)).values["requerimientos"]
    assert requerimientos.defectos == ()
    assert requerimientos.defectos_escalados == (defecto,)
    assert requerimientos.correcciones == 0


def test_errores_de_validacion_regresan_al_diseno_sin_humano():
    recorrido = recorrer(
        compilar(ServiciosSimulados(fallos_veredicto=0, errores_validacion=1)), guion_directo()
    )
    visitas = Counter(recorrido.nodos)
    assert visitas[Nodo.N8] == 2
    assert visitas[Nodo.N9] == 2
    assert recorrido.final.fase is Fase.VALIDADO


def test_limite_de_turnos_cierra_la_elicitacion():
    app = compilar(ServiciosSimulados(), turnos=3)
    id_sesion, avance = iniciar_sesion(app, "Realtix", "Catastro", NECESIDAD)
    avance = avanzar(app, id_sesion, "Analista")
    assert avance.pausa.punto == "dialogo"
    avance = avanzar(app, id_sesion, "Ahorrar tiempo")
    assert avance.pausa.punto == "requerimientos"
    estado = app.get_state(configuracion_hilo(id_sesion)).values
    assert estado["conversacion"].registro.pendientes == [
        "reglas_negocio",
        "datos_entrada",
        "datos_salida",
        "excepciones",
        "confirmacion",
    ]


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
