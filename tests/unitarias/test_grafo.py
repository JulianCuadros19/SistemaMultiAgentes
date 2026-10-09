"""Condición de terminado del paso 5 sin base de datos: recorrido, ciclos, retornos y caídas."""

import logging
from collections import Counter

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from multiagente.core.configuracion import ConfiguracionOrquestador
from multiagente.orquestador.ejecucion import (
    avanzar,
    configuracion_hilo,
    iniciar_sesion,
    validaciones,
)
from multiagente.orquestador.estado import (
    Contexto,
    Conversacion,
    Decision,
    Emisor,
    Fase,
    PuntoControl,
    Requerimientos,
    Veredicto,
)
from multiagente.orquestador.grafo import Nodo, construir_grafo
from multiagente.orquestador.servicios import Servicios
from multiagente.orquestador.simulacion import (
    ElicitadorFijo,
    ErrorSimulado,
    Guion,
    ServiciosSimulados,
    aprobar,
    continuar,
    guion_completo,
    rechazar,
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
    simulacion: ServiciosSimulados | Servicios,
    iteraciones: int = 3,
    turnos: int = 15,
    correcciones: int = 2,
    correcciones_diseno: int = 2,
):
    configuracion = ConfiguracionOrquestador(
        _env_file=None,
        max_iteraciones_correccion=iteraciones,
        max_turnos_elicitacion=turnos,
        max_correcciones_calidad=correcciones,
        max_correcciones_diseno=correcciones_diseno,
    )
    servicios = simulacion if isinstance(simulacion, Servicios) else simulacion.como_servicios()
    grafo = construir_grafo(servicios, configuracion)
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


def test_respuesta_humana_invalida_vuelve_a_pausar_sin_bloquear_la_sesion():
    app = compilar(ServiciosSimulados())
    id_sesion, _ = iniciar_sesion(app, "Realtix", "Catastro", NECESIDAD)
    for respuesta in RESPUESTAS:
        avanzar(app, id_sesion, respuesta)
    # Un rechazo sin observaciones no se acepta: la sesión sigue en N6 con el motivo.
    avance = avanzar(app, id_sesion, {"decision": "rechazado", "revisor": "A"})
    assert avance.pausa.punto == "requerimientos"
    assert "observaciones" in avance.pausa.datos["aviso"]
    # Y una respuesta válida posterior sí se lee: el flujo continúa.
    avance = avanzar(app, id_sesion, aprobar())
    assert Nodo.N7 in avance.nodos
    aprobaciones = app.get_state(configuracion_hilo(id_sesion)).values["sesion"].aprobaciones
    assert [a.decision for a in aprobaciones] == [Decision.APROBADO]


def test_respuesta_vacia_del_cliente_vuelve_a_preguntar():
    app = compilar(ServiciosSimulados())
    id_sesion, _ = iniciar_sesion(app, "Realtix", "Catastro", NECESIDAD)
    avance = avanzar(app, id_sesion, "   ")
    assert avance.pausa.punto == "dialogo"
    assert avance.pausa.datos["aviso"] == "La respuesta no puede estar vacía."
    avance = avanzar(app, id_sesion, "Analista")
    conversacion = app.get_state(configuracion_hilo(id_sesion)).values["conversacion"]
    assert conversacion.registro.rol == "Analista"
    assert avance.pausa.datos["aviso"] is None


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


def test_defectos_que_requieren_al_cliente_escalan_sin_corregir():
    simulacion = ServiciosSimulados(defectos_calidad=99, defectos_requieren_cliente=True)
    app = compilar(simulacion)
    id_sesion, avance = iniciar_sesion(app, "Realtix", "Catastro", NECESIDAD)
    for respuesta in RESPUESTAS:
        avance = avanzar(app, id_sesion, respuesta)
    assert simulacion.llamadas["sintetizar"] == 1
    assert avance.pausa.punto == "requerimientos"
    assert avance.pausa.datos["defectos"] == ["Defecto simulado: la regla de negocio es ambigua"]


def hasta_la_especificacion(app, id_sesion: str):
    """Responde el diálogo y aprueba los requerimientos hasta la primera pausa de N9."""
    for respuesta in RESPUESTAS:
        avanzar(app, id_sesion, respuesta)
    return avanzar(app, id_sesion, aprobar())


def test_errores_de_diseno_persistentes_escalan_sin_poder_aprobarse():
    simulacion = ServiciosSimulados(errores_validacion=99)
    app = compilar(simulacion, correcciones_diseno=2)
    id_sesion, _ = iniciar_sesion(app, "Realtix", "Catastro", NECESIDAD)
    avance = hasta_la_especificacion(app, id_sesion)

    # Un diseño y dos correcciones automáticas; después, la persona ve los errores.
    assert Counter(avance.nodos)[Nodo.N8] == 3
    assert avance.pausa.punto == "especificacion"
    error = "Error simulado: un requerimiento aprobado no tiene módulo asignado"
    assert avance.pausa.datos["errores"] == [error]

    # Aprobar con errores queda bloqueado (Anexo B): la sesión sigue en la pausa con el aviso.
    avance = avanzar(app, id_sesion, aprobar())
    assert avance.pausa.punto == "especificacion"
    assert "Anexo B" in avance.pausa.datos["aviso"]

    # El rechazo vuelve a N8 con las observaciones y el contador reiniciado.
    avance = avanzar(app, id_sesion, rechazar("Asignar el RF-01 a un módulo"))
    assert Counter(avance.nodos)[Nodo.N8] == 3
    arquitectura = app.get_state(configuracion_hilo(id_sesion)).values["arquitectura"]
    assert arquitectura.observaciones_revisor == ("Asignar el RF-01 a un módulo",)
    assert arquitectura.disenos == 6
    assert arquitectura.especificacion.version == "0.6"


def test_especificacion_valida_se_aprueba_y_reinicia_el_contador():
    simulacion = ServiciosSimulados(errores_validacion=1, fallos_veredicto=0)
    app = compilar(simulacion)
    id_sesion, _ = iniciar_sesion(app, "Realtix", "Catastro", NECESIDAD)
    avance = hasta_la_especificacion(app, id_sesion)
    assert avance.pausa.datos["errores"] == []
    avance = avanzar(app, id_sesion, aprobar())
    assert Nodo.N10 in avance.nodos
    arquitectura = app.get_state(configuracion_hilo(id_sesion)).values["arquitectura"]
    assert (arquitectura.correcciones, arquitectura.errores_validacion) == (0, ())


def test_elicitador_fijo_lleva_requerimientos_dados_hasta_el_diseno():
    simulacion = ServiciosSimulados()
    sintesis = simulacion.sintetizar(Conversacion(), Contexto(), Requerimientos(), "Catastro")
    simulacion.llamadas.clear()
    servicios = Servicios(
        elicitador=ElicitadorFijo(sintesis),
        arquitecto=simulacion,
        desarrollador=simulacion,
        tester=simulacion,
    )
    app = compilar(servicios)
    id_sesion, avance = iniciar_sesion(app, "Realtix", "Catastro", NECESIDAD)
    assert avance.nodos == (Nodo.N1, Nodo.N2, Nodo.N3, Nodo.N4, Nodo.N5)
    assert avance.pausa.punto == "requerimientos"
    avance = avanzar(app, id_sesion, aprobar())
    assert avance.pausa.punto == "especificacion"
    requerimientos = app.get_state(configuracion_hilo(id_sesion)).values["requerimientos"]
    assert requerimientos.requerimientos == sintesis.requerimientos
    assert simulacion.llamadas["disenar"] == 1


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


def test_validaciones_de_cada_version_en_orden():
    # Un veredicto fallido y una corrección pedida en N17: tres versiones dictaminadas.
    app = compilar(ServiciosSimulados(fallos_veredicto=1))
    recorrido = recorrer(app, guion_completo())

    historial = validaciones(app, recorrido.id_sesion)
    assert [version.numero for version, _ in historial] == [1, 2, 3]
    assert [validacion.veredicto for _, validacion in historial] == [
        Veredicto.RECHAZADO,
        Veredicto.APROBADO,
        Veredicto.APROBADO,
    ]
    assert historial[0][1].retroalimentacion == (
        "CP-RF-01-ESC-01: no cumple",
        "CP-RF-01-ESC-02: no cumple",
    )
    assert (
        historial[-1][1]
        == app.get_state(configuracion_hilo(recorrido.id_sesion)).values["validacion"]
    )


PROPIAS = {
    "archivos": {"tests/test_propia.py": "def test_limite():\n    assert True\n"},
    "ejecucion": {
        "pruebas": [
            {"archivo": "tests/test_propia.py", "nombre": "test_limite", "resultado": "paso"}
        ]
    },
}


def avanzar_hasta(app, guion: Guion, punto: str):
    id_sesion, avance = iniciar_sesion(app, "Cliente", guion.proyecto, guion.necesidad)
    while avance.pausa.punto != punto:
        avance = avanzar(app, id_sesion, guion.responder(avance.pausa.punto))
    return id_sesion, avance


def test_n17_muestra_la_iteracion_y_registra_las_pruebas_propias():
    app = compilar(ServiciosSimulados(fallos_veredicto=0))
    id_sesion, avance = avanzar_hasta(app, guion_directo(), "final")
    assert avance.pausa.datos["iteracion"] == 1
    assert avance.pausa.datos["limite_iteraciones"] == 3

    final = avanzar(app, id_sesion, aprobar() | {"pruebas_propias": PROPIAS})
    assert final.fase is Fase.VALIDADO
    sesion = app.get_state(configuracion_hilo(id_sesion)).values["sesion"]
    registradas = sesion.ultima_aprobacion(PuntoControl.FINAL).pruebas_propias
    assert registradas.archivos == PROPIAS["archivos"]
    assert registradas.ejecucion.pruebas[0].nombre == "test_limite"


def test_las_pruebas_propias_solo_se_admiten_en_la_aprobacion_final():
    app = compilar(ServiciosSimulados(fallos_veredicto=0))
    id_sesion, _ = avanzar_hasta(app, guion_directo(), "requerimientos")
    avance = avanzar(app, id_sesion, aprobar() | {"pruebas_propias": PROPIAS})
    assert avance.pausa.punto == "requerimientos"
    assert "solo se registran en la aprobación final" in avance.pausa.datos["aviso"]
