"""Presupuesto de la sesión y traza por nodo, con servicios simulados (paso 13, ADR-0016)."""

from decimal import Decimal

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from multiagente.core.configuracion import ConfiguracionOrquestador
from multiagente.interfaces.operacion import Operador
from multiagente.orquestador.ejecucion import avanzar, configuracion_hilo, iniciar_sesion
from multiagente.orquestador.estado import PAUSA_PRESUPUESTO, Control, Fase
from multiagente.orquestador.grafo import NODOS_CON_MODELO, Nodo, construir_grafo
from multiagente.orquestador.simulacion import (
    ErrorSimulado,
    Guion,
    ServiciosSimulados,
    aprobar,
    continuar,
    recorrer,
)
from multiagente.orquestador.traza import TrazaEnMemoria
from multiagente.persistencia.puntos_control import serializador

CENTAVO = Decimal("0.01")
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
TRABAJOS_CON_MODELO = ("dialogar", "sintetizar", "enmendar", "disenar", "generar", "dictaminar")


def compilar(simulacion, presupuesto=Decimal("1.50"), observador=None):
    configuracion = ConfiguracionOrquestador(
        _env_file=None, presupuesto_maximo_por_modulo_usd=presupuesto
    )
    grafo = construir_grafo(simulacion.como_servicios(), configuracion, observador)
    return grafo.compile(checkpointer=InMemorySaver(serde=serializador()))


def guion() -> Guion:
    return Guion(
        necesidad=NECESIDAD,
        respuestas_cliente=list(RESPUESTAS),
        decisiones={punto: [aprobar()] for punto in ("requerimientos", "especificacion", "final")},
    )


def control(app, id_sesion: str) -> Control:
    return app.get_state(configuracion_hilo(id_sesion)).values["control"]


def test_el_costo_de_la_sesion_suma_solo_las_llamadas_de_los_nodos_con_modelo():
    simulacion = ServiciosSimulados(fallos_veredicto=0, costo_por_llamada=CENTAVO)
    traza = TrazaEnMemoria()
    app = compilar(simulacion, observador=traza)
    recorrido = recorrer(app, guion())

    assert recorrido.final.fase is Fase.VALIDADO
    trabajos = sum(simulacion.llamadas[trabajo] for trabajo in TRABAJOS_CON_MODELO)
    final = control(app, recorrido.id_sesion)
    assert final.costo_acumulado_usd == CENTAVO * trabajos
    assert final.presupuesto_usd == Decimal("1.50") and final.ampliaciones == ()

    # La traza tiene cada nodo, con su tiempo; solo los nodos con modelo tienen llamadas.
    ejecuciones = traza.consultar(recorrido.id_sesion)
    assert {ejecucion.nodo for ejecucion in ejecuciones} == {nodo.value for nodo in Nodo}
    assert all(ejecucion.error is None and ejecucion.duracion_ms >= 0 for ejecucion in ejecuciones)
    assert all(not e.llamadas for e in ejecuciones if e.nodo not in NODOS_CON_MODELO)
    assert sum(e.costo_usd for e in ejecuciones) == final.costo_acumulado_usd
    n3 = [e for e in ejecuciones if e.nodo == Nodo.N3]
    assert len(n3) == simulacion.llamadas["dialogar"]
    assert all(e.llamadas[0].nodo == "N3" for e in n3)


def test_al_alcanzar_el_presupuesto_la_sesion_pausa_antes_del_siguiente_nodo_con_modelo():
    simulacion = ServiciosSimulados(fallos_veredicto=0, costo_por_llamada=CENTAVO)
    app = compilar(simulacion, presupuesto=Decimal("0.05"))
    id_sesion, avance = iniciar_sesion(app, "Cliente", "Catastro", NECESIDAD)
    for respuesta in RESPUESTAS[:4]:
        avance = avanzar(app, id_sesion, respuesta)

    # Cinco turnos de N3 gastaron el presupuesto: el sexto no corre.
    assert simulacion.llamadas["dialogar"] == 5
    assert avance.pausa.punto == PAUSA_PRESUPUESTO
    assert avance.pausa.datos == {
        "gastado_usd": "0.05",
        "presupuesto_usd": "0.05",
        "nodo": Nodo.N3.value,
        "aviso": None,
    }

    # Un presupuesto que no supera lo gastado, o una respuesta sin revisor, vuelven a pausar.
    avance = avanzar(app, id_sesion, {"revisor": "Laura", "presupuesto_usd": "0.05"})
    assert avance.pausa.punto == PAUSA_PRESUPUESTO
    assert "debe superar lo gastado, 0.05 USD" in avance.pausa.datos["aviso"]
    avance = avanzar(app, id_sesion, {"presupuesto_usd": "0.20"})
    assert "Respuesta inválida" in avance.pausa.datos["aviso"]
    assert simulacion.llamadas["dialogar"] == 5

    # Ampliado, N3 sigue: pide la respuesta pendiente al cliente y la procesa.
    ampliar = {"revisor": "Laura", "presupuesto_usd": "0.20", "motivo": "Falta cerrar el diálogo"}
    avance = avanzar(app, id_sesion, ampliar)
    assert avance.pausa.punto == "dialogo"
    avance = avanzar(app, id_sesion, RESPUESTAS[4])
    assert simulacion.llamadas["dialogar"] == 6
    actual = control(app, id_sesion)
    assert actual.presupuesto_usd == Decimal("0.20")
    assert actual.costo_acumulado_usd == Decimal("0.06")
    (ampliacion,) = actual.ampliaciones
    assert (ampliacion.revisor, ampliacion.anterior, ampliacion.nuevo, ampliacion.gastado) == (
        "Laura",
        Decimal("0.05"),
        Decimal("0.20"),
        Decimal("0.05"),
    )
    assert ampliacion.motivo == "Falta cerrar el diálogo"

    # El resto del flujo cabe en el presupuesto ampliado.
    restantes = Guion(
        necesidad=NECESIDAD,
        respuestas_cliente=list(RESPUESTAS[5:]),
        decisiones=guion().decisiones,
    )
    assert continuar(app, id_sesion, restantes, avance).final.fase is Fase.VALIDADO


@pytest.mark.parametrize(
    ("presupuesto", "gastado", "alcanzado"),
    [
        (None, Decimal(100), False),
        (Decimal("1.50"), Decimal("1.49"), False),
        (Decimal("1.50"), Decimal("1.50"), True),
    ],
)
def test_presupuesto_alcanzado(presupuesto, gastado, alcanzado):
    # Las sesiones anteriores al paso 13 no tienen presupuesto y no se detienen.
    actual = Control(
        limite_iteraciones=3,
        limite_turnos=18,
        limite_correcciones=2,
        limite_correcciones_diseno=2,
        costo_acumulado_usd=gastado,
        presupuesto_usd=presupuesto,
    )
    assert actual.presupuesto_alcanzado is alcanzado


def test_la_traza_registra_el_error_del_nodo_que_falla_y_su_reanudacion():
    simulacion = ServiciosSimulados(fallos_veredicto=0, fallos_ejecucion=1)
    traza = TrazaEnMemoria()
    app = compilar(simulacion, observador=traza)
    with pytest.raises(ErrorSimulado):
        recorrer(app, guion(), id_sesion="sesion-caida")
    reanudado = avanzar(app, "sesion-caida")
    continuar(app, "sesion-caida", guion(), reanudado)

    n11 = [e for e in traza.consultar("sesion-caida") if e.nodo == Nodo.N11]
    assert [e.error is not None for e in n11] == [True, False]
    assert "ErrorSimulado" in n11[0].error


def test_la_traza_de_la_sesion_muestra_por_nodo_los_prompts_tokens_costos_y_tiempos():
    # Criterio del RF-34: dada una ejecución finalizada, su traza tiene los prompts, los tokens,
    # los costos y los tiempos por nodo del grafo.
    simulacion = ServiciosSimulados(fallos_veredicto=0, costo_por_llamada=CENTAVO)
    traza = TrazaEnMemoria()
    app = compilar(simulacion, observador=traza)
    recorrido = recorrer(app, guion())
    operador = Operador(app, traza=traza)

    documento = operador.traza(recorrido.id_sesion)
    trabajos = sum(simulacion.llamadas[trabajo] for trabajo in TRABAJOS_CON_MODELO)
    assert documento.startswith(f"# Traza de la sesión {recorrido.id_sesion}\n")
    assert f"- Gastado: {CENTAVO * trabajos:.4f} USD · presupuesto: 1.5000 USD" in documento
    assert f"llamadas al modelo: {trabajos} · costo registrado: {CENTAVO * trabajos:.4f} USD" in (
        documento
    )
    dialogos = simulacion.llamadas["dialogar"]
    assert f"| N3 · diálogo con el cliente | {dialogos} | " in documento
    # Cada turno simulado hace una llamada de un token de entrada y uno de salida.
    assert f"| {dialogos} | {dialogos} | {dialogos} (0) | {CENTAVO * dialogos:.4f} |" in documento
    assert "| N1 · apertura de la sesión | 1 | " in documento
    assert "| n10_generacion | simulado@0.0 | simulado | 1 (0) | 1 (0) | 0.0 | 0.0100 | stop |" in (
        documento
    )
    assert len(operador.ejecuciones(recorrido.id_sesion)) == len(traza.ejecuciones)
    # Sin traza configurada, el operador la entrega vacía.
    assert "Aún no hay nodos en la traza." in Operador(app).traza(recorrido.id_sesion)
