"""Interfaz de consola: presentación, bucle de operación y subcomandos, con entradas guionizadas."""

import argparse

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from multiagente.core.configuracion import ConfiguracionInterfaces, ConfiguracionOrquestador
from multiagente.interfaces.consola import (
    ACUSE_CONFIRMACION,
    _parser,
    ejecutar,
    mostrar_especificacion,
    mostrar_requerimientos,
    mostrar_validacion,
)
from multiagente.interfaces.operacion import Operador
from multiagente.orquestador.ejecucion import avanzar, iniciar_sesion
from multiagente.orquestador.estado import Decision, Fase, PuntoControl, ResultadoPrueba
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
    assert "Iteración 1 de 3 del ciclo de corrección." in salida


class Teclado:
    """Entradas guionizadas de la persona; falla si se pide una de más."""

    def __init__(self, *entradas: str) -> None:
        self.entradas = list(entradas)
        self.indicaciones: list[str] = []

    def __call__(self, indicacion: str = "") -> str:
        self.indicaciones.append(indicacion)
        if not self.entradas:
            raise AssertionError(f"La consola pidió una entrada de más: {indicacion!r}")
        return self.entradas.pop(0)


def operador(simulacion: ServiciosSimulados, entorno) -> Operador:
    app = construir_grafo(
        simulacion.como_servicios(), ConfiguracionOrquestador(_env_file=None)
    ).compile(checkpointer=InMemorySaver(serde=serializador()))
    return Operador(app, entorno)


def comando(texto: str) -> argparse.Namespace:
    return _parser().parse_args(texto.split())


def configuracion(tmp_path) -> ConfiguracionInterfaces:
    return ConfiguracionInterfaces(
        _env_file=None,
        traza_llamadas=tmp_path / "traza.jsonl",
        carpeta_trabajo=tmp_path / "trabajo",
    )


def test_una_persona_opera_el_flujo_completo_por_consola(tmp_path, capsys, entorno_falso):
    prueba_que_falla = tmp_path / "radicado.py"
    prueba_que_falla.write_text("def test_radicado_falla():\n    assert False\n")
    prueba_que_pasa = tmp_path / "test_radicado.py"
    prueba_que_pasa.write_text("def test_radicado_con_anio():\n    assert True\n")
    guion = guion_completo()
    respuestas = guion.respuestas_cliente
    teclado = Teclado(
        "Oficina de catastro",
        guion.proyecto,
        guion.necesidad,
        *respuestas[:7],
        # N6: rechazo con observaciones; el diálogo vuelve con dos respuestas más; aprobación.
        "r",
        "Falta la regla sobre la fecha del documento",
        "Laura",
        *respuestas[7:],
        "a",
        "",
        # N9: rechazo y aprobación.
        "r",
        "Separar la validación en su propio módulo",
        "",
        "a",
        "",
        # N17: escribe el código, prueba con un archivo propio que falla y rechaza con las
        # observaciones sugeridas; en la versión 2 prueba de nuevo y aprueba.
        "c",
        "p",
        str(prueba_que_falla),
        "r",
        "",
        "",
        "p",
        str(prueba_que_pasa),
        "a",
        "Julián",
    )
    op = operador(ServiciosSimulados(fallos_veredicto=0), entorno_falso)
    assert ejecutar(op, comando("nueva"), configuracion(tmp_path), teclado) == 0

    salida = capsys.readouterr().out
    assert ACUSE_CONFIRMACION in salida
    assert "Observaciones sugeridas por sus pruebas:" in salida
    assert "fallo   tests/test_radicado.py::test_radicado_falla" in salida
    assert "Módulo validado." in salida
    [vista] = op.sesiones()
    assert vista.fase is Fase.VALIDADO
    assert (tmp_path / "trabajo" / vista.id_sesion / "v1" / "src/simulado/modulo.py").exists()

    finales = [
        a
        for a in op.estado(vista.id_sesion)["sesion"].aprobaciones
        if a.punto is PuntoControl.FINAL
    ]
    rechazo, aprobacion = finales
    assert rechazo.decision is Decision.RECHAZADO
    assert "test_radicado_falla no pasa (fallo)" in rechazo.observaciones
    assert rechazo.pruebas_propias.ejecucion.pruebas[0].resultado is ResultadoPrueba.FALLO
    assert (aprobacion.revisor, aprobacion.pruebas_propias.archivos) == (
        "Julián",
        {"tests/test_radicado.py": prueba_que_pasa.read_text()},
    )

    # Subcomandos de consulta y exportación.
    assert ejecutar(op, comando("sesiones"), configuracion(tmp_path)) == 0
    assert ejecutar(op, comando(f"ver {vista.id_sesion}"), configuracion(tmp_path)) == 0
    destino = tmp_path / "exportado"
    exportar = comando(f"exportar {vista.id_sesion} {destino}")
    assert ejecutar(op, exportar, configuracion(tmp_path)) == 0
    assert (destino / "requerimientos.json").exists()
    assert (destino / "codigo" / "src/simulado/modulo.py").exists()
    assert ejecutar(op, exportar, configuracion(tmp_path)) == 1
    salida = capsys.readouterr().out
    assert f"{vista.id_sesion}  " in salida and "Módulo validado" in salida
    assert f"# Trazabilidad de la sesión {vista.id_sesion}" in salida
    assert "no está vacía" in salida


def test_ofrece_reanudar_una_sesion_detenida_por_una_falla(tmp_path, capsys, entorno_falso):
    guion = guion_completo()
    op = operador(ServiciosSimulados(fallos_veredicto=0, fallos_ejecucion=1), entorno_falso)
    aprobaciones = ["a", ""]
    teclado = Teclado(
        "Oficina", guion.proyecto, guion.necesidad, *guion.respuestas_cliente[:7], *aprobaciones * 2
    )
    teclado.entradas.append("s")  # Tras la falla de N11, no reanuda todavía.
    assert ejecutar(op, comando("nueva"), configuracion(tmp_path), teclado) == 0
    salida = capsys.readouterr().out
    assert "(El sistema se detuvo por un error: ErrorSimulado" in salida
    assert "Detenida antes de N11 · ejecución en el entorno aislado" in salida

    [vista] = op.sesiones()
    continuar = comando(f"continuar {vista.id_sesion}")
    assert ejecutar(op, continuar, configuracion(tmp_path), Teclado("r", "a", "")) == 0
    assert op.vista(vista.id_sesion).fase is Fase.VALIDADO


def test_salir_deja_la_sesion_en_pausa_y_continuar_la_retoma(tmp_path, capsys, entorno_falso):
    guion = guion_completo()
    op = operador(ServiciosSimulados(), entorno_falso)
    teclado = Teclado("Oficina", guion.proyecto, guion.necesidad, guion.respuestas_cliente[0])
    teclado.entradas.append("/salir")
    assert ejecutar(op, comando("nueva"), configuracion(tmp_path), teclado) == 0
    [vista] = op.sesiones()
    assert "multiagente continuar " + vista.id_sesion in capsys.readouterr().out
    assert vista.pausa.punto == "dialogo"

    siguiente = Teclado(guion.respuestas_cliente[1], "/salir")
    continuar = comando(f"continuar {vista.id_sesion}")
    assert ejecutar(op, continuar, configuracion(tmp_path), siguiente) == 0
    assert op.estado(vista.id_sesion)["conversacion"].turnos_cliente == 3


def test_errores_de_operacion_salen_con_codigo_1(tmp_path, capsys, entorno_falso):
    op = operador(ServiciosSimulados(), entorno_falso)
    assert ejecutar(op, comando("ver no-existe"), configuracion(tmp_path)) == 1
    assert "No existe la sesión no-existe" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        _parser().parse_args(["desconocido"])
