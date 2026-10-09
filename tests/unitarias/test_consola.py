"""Presentación en consola de los tres puntos de control, con los datos reales de cada pausa."""

from langgraph.checkpoint.memory import InMemorySaver

from multiagente.core.configuracion import ConfiguracionOrquestador
from multiagente.interfaces.consola import (
    mostrar_especificacion,
    mostrar_requerimientos,
    mostrar_validacion,
)
from multiagente.orquestador.ejecucion import avanzar, iniciar_sesion
from multiagente.orquestador.grafo import construir_grafo
from multiagente.orquestador.simulacion import ServiciosSimulados, guion_completo
from multiagente.persistencia.puntos_control import serializador

PRESENTACION = {
    "requerimientos": mostrar_requerimientos,
    "especificacion": mostrar_especificacion,
    "final": mostrar_validacion,
}


def test_presenta_cada_punto_de_control_con_los_datos_de_su_pausa(capsys):
    # Recorre la sesión simulada completa y presenta cada pausa humana con su función: si los
    # datos de una pausa cambian de forma, la presentación falla aquí y no frente a la persona.
    servicios = ServiciosSimulados(fallos_veredicto=0).como_servicios()
    app = construir_grafo(servicios, ConfiguracionOrquestador(_env_file=None)).compile(
        checkpointer=InMemorySaver(serde=serializador())
    )
    guion = guion_completo()
    id_sesion, avance = iniciar_sesion(app, "Cliente", guion.proyecto, guion.necesidad)
    presentados = []
    while avance.pausa is not None:
        punto = avance.pausa.punto
        if punto in PRESENTACION:
            PRESENTACION[punto](avance.pausa.datos)
            presentados.append(punto)
        avance = avanzar(app, id_sesion, guion.responder(punto))

    salida = capsys.readouterr().out
    assert set(presentados) == set(PRESENTACION)
    assert "=== Punto de control N6: requerimientos ===" in salida
    assert "=== Punto de control N9: especificación de diseño ===" in salida
    assert "=== Punto de control N17: versión 1 del módulo ===" in salida
    assert "Validaciones del Anexo B: sin errores." in salida
