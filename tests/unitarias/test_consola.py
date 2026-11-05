"""Interfaz de consola: presentación, bucle de operación y subcomandos, con entradas guionizadas."""

import argparse
from decimal import Decimal

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from multiagente.core.configuracion import ConfiguracionInterfaces, ConfiguracionOrquestador
from multiagente.interfaces.consola import (
    _parser,
    ejecutar,
    mostrar_especificacion,
    mostrar_requerimientos,
    mostrar_validacion,
)
from multiagente.interfaces.operacion import ACUSE_CONFIRMACION, Operador
from multiagente.orquestador.ejecucion import avanzar, iniciar_sesion
from multiagente.orquestador.estado import Decision, Destino, Fase, PuntoControl, ResultadoPrueba
from multiagente.orquestador.grafo import construir_grafo
from multiagente.orquestador.simulacion import ServiciosSimulados, guion_completo
from multiagente.orquestador.traza import TrazaEnMemoria
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
    assert "Validaciones del Anexo B y de los escenarios: sin errores." in salida
    assert "## Recorridos de los escenarios" in salida
    assert "| RF-01 ESC-01 | — | ejecutar | ejecutar |" in salida
    assert "El tester lo aprobó en la iteración 1 de 3 del ciclo de corrección." in salida


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
    assert (
        "fallo   tests/test_radicado.py::test_radicado_falla · "
        "AssertionError: falta el año assert 2025 == 2026"
    ) in salida
    assert "test_radicado.py:3: AssertionError" not in salida
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


def test_no_ofrece_reanudar_ni_cerrar_una_sesion_en_curso(tmp_path, capsys, entorno_falso):
    guion = guion_completo()
    op = operador(ServiciosSimulados(fallos_veredicto=0, fallos_ejecucion=1), entorno_falso)
    teclado = Teclado(
        "Oficina", guion.proyecto, guion.necesidad, *guion.respuestas_cliente[:7], *["a", ""] * 2
    )
    teclado.entradas.append("s")  # Tras la falla de N11, no reanuda todavía.
    assert ejecutar(op, comando("nueva"), configuracion(tmp_path), teclado) == 0
    [vista] = op.sesiones()
    capsys.readouterr()

    # Otro proceso la está reanudando: la consola avisa sin pedir nada.
    with op.bloqueos.exclusivo(vista.id_sesion):
        continuar = comando(f"continuar {vista.id_sesion}")
        assert ejecutar(op, continuar, configuracion(tmp_path), Teclado()) == 0
        cerrar = comando(f"cerrar {vista.id_sesion}")
        assert ejecutar(op, cerrar, configuracion(tmp_path), Teclado()) == 1
    salida = capsys.readouterr().out
    assert "En curso: N11 · ejecución en el entorno aislado. Otro proceso" in salida
    assert "está en curso en otro proceso; ciérrela cuando termine" in salida
    assert op.vista(vista.id_sesion).detenida


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


def test_presenta_las_pausas_sin_artefactos(capsys):
    # N6 sin requerimientos, N9 sin especificación y N17 escalado sin versión: la persona ve qué
    # falló en lugar de un error de la consola.
    mostrar_requerimientos(
        {
            "historias": [],
            "requerimientos": [],
            "referencias": {},
            "defectos": ["La síntesis falló: salida inválida"],
        }
    )
    mostrar_especificacion(
        {
            "registro_decision": None,
            "especificacion": None,
            "errores": ["El diseño falló: salida inválida"],
            "capacidades_no_cubiertas": ["Leer hojas de cálculo Excel"],
        }
    )
    mostrar_validacion(
        {
            "escalado": True,
            "iteracion": 3,
            "limite_iteraciones": 3,
            "version": None,
            "archivos": [],
            "reporte": "# La generación del módulo falló",
        }
    )
    salida = capsys.readouterr().out
    assert "La síntesis falló: salida inválida" in salida
    assert "No hay especificación de diseño" in salida
    assert "  - Leer hojas de cálculo Excel" in salida
    assert "=== Punto de control N17: sin versión válida del módulo ===" in salida
    assert "La sesión escaló: tras 3 iteraciones" in salida


def test_en_n17_escalado_no_se_aprueba_y_se_devuelve_al_arquitecto(tmp_path, capsys, entorno_falso):
    guion = guion_completo()
    teclado = Teclado(
        "Oficina",
        guion.proyecto,
        guion.necesidad,
        *guion.respuestas_cliente[:7],
        *["a", ""] * 2,
        # N17 escalado: aprobar no es una opción; devuelve al arquitecto.
        "a",
        "d",
        "Usar una arquitectura más simple",
        "Laura",
        # N9 de nuevo y N17 con la versión que aprobó el tester.
        *["a", ""] * 2,
    )
    op = operador(ServiciosSimulados(fallos_veredicto=3), entorno_falso)
    assert ejecutar(op, comando("nueva"), configuracion(tmp_path), teclado) == 0

    salida = capsys.readouterr().out
    assert "El tester no aprobó el módulo y no puede aprobarse" in salida
    assert "Opción no válida." in salida
    menus = [i for i in teclado.indicaciones if "[x] cerrar la sesión" in i]
    escalado = next(i for i in menus if "[d]iseño" in i)
    assert "[a]probar" not in escalado and "[p]robar" in escalado
    [vista] = op.sesiones()
    assert vista.fase is Fase.VALIDADO
    finales = [
        a
        for a in op.estado(vista.id_sesion)["sesion"].aprobaciones
        if a.punto is PuntoControl.FINAL
    ]
    assert [(a.decision, a.destino) for a in finales] == [
        (Decision.RECHAZADO, Destino.ARQUITECTO),
        (Decision.APROBADO, None),
    ]


def test_en_n17_se_enmiendan_los_requerimientos_y_el_analista_ve_la_enmienda(
    tmp_path, capsys, entorno_falso
):
    guion = guion_completo()
    regla = "El radicado debe incluir el año de la solicitud"
    teclado = Teclado(
        "Oficina",
        guion.proyecto,
        guion.necesidad,
        *guion.respuestas_cliente[:7],
        *["a", ""] * 2,
        # N17: pide una enmienda con la regla nueva.
        "e",
        regla,
        "Laura",
        # N6 con la enmienda, sin pasar por N9, y N17 con la versión corregida.
        *["a", ""] * 2,
    )
    op = operador(ServiciosSimulados(fallos_veredicto=0), entorno_falso)
    assert ejecutar(op, comando("nueva"), configuracion(tmp_path), teclado) == 0

    salida = capsys.readouterr().out
    menu_final = next(i for i in teclado.indicaciones if "[d]iseño" in i)
    assert "[e]nmendar los requerimientos" in menu_final
    assert any(i.startswith("Regla nueva para los requerimientos") for i in teclado.indicaciones)
    assert "Enmienda pedida en la aprobación final por Laura el " in salida
    assert "Requerimientos enmendados: RF-01 v0.2." in salida
    assert "## RF-01 · versión 0.2\n\n- v0.2 · enmendado desde N17 por Laura el " in salida
    assert salida.count("=== Punto de control N9") == 1
    [vista] = op.sesiones()
    assert vista.fase is Fase.VALIDADO
    finales = [
        a
        for a in op.estado(vista.id_sesion)["sesion"].aprobaciones
        if a.punto is PuntoControl.FINAL
    ]
    assert [(a.decision, a.destino) for a in finales] == [
        (Decision.RECHAZADO, Destino.REQUERIMIENTOS),
        (Decision.APROBADO, None),
    ]


def test_la_consola_amplia_el_presupuesto_y_muestra_el_gasto_y_la_traza(
    tmp_path, capsys, entorno_falso
):
    simulacion = ServiciosSimulados(fallos_veredicto=0, costo_por_llamada=Decimal("0.01"))
    configuracion_grafo = ConfiguracionOrquestador(
        _env_file=None, presupuesto_maximo_por_modulo_usd=Decimal("0.05")
    )
    traza = TrazaEnMemoria()
    app = construir_grafo(simulacion.como_servicios(), configuracion_grafo, traza).compile(
        checkpointer=InMemorySaver(serde=serializador())
    )
    op = Operador(app, entorno_falso, traza=traza)
    guion = guion_completo()
    teclado = Teclado(
        "Oficina",
        guion.proyecto,
        guion.necesidad,
        *guion.respuestas_cliente[:4],
        # Pausa por presupuesto: una cifra inválida, y luego la ampliación con su motivo.
        "a",
        "mucho",
        "a",
        "1,00",
        "Falta cerrar el diálogo",
        "Laura",
        *guion.respuestas_cliente[4:7],
        *["a", ""] * 3,
    )
    assert ejecutar(op, comando("nueva"), configuracion(tmp_path), teclado) == 0

    salida = capsys.readouterr().out
    assert "=== Pausa por presupuesto ===" in salida
    assert "La sesión gastó 0.05 USD de su presupuesto de 0.05 USD." in salida
    assert "Escriba el presupuesto como un número, por ejemplo 2.50." in salida
    [vista] = op.sesiones()
    assert vista.fase is Fase.VALIDADO
    (ampliacion,) = op.estado(vista.id_sesion)["control"].ampliaciones
    assert (ampliacion.revisor, ampliacion.nuevo) == ("Laura", Decimal("1.00"))

    assert ejecutar(op, comando("sesiones"), configuracion(tmp_path), Teclado()) == 0
    assert f"gastado {vista.costo_usd:.4f} USD, presupuesto 1.00 USD" in capsys.readouterr().out
    assert ejecutar(op, comando(f"traza {vista.id_sesion}"), configuracion(tmp_path)) == 0
    documento = capsys.readouterr().out
    assert documento.startswith(f"# Traza de la sesión {vista.id_sesion}")
    assert "  - Ampliado por Laura el " in documento and ": Falta cerrar el diálogo" in documento


def test_se_cierra_desde_un_punto_de_control(tmp_path, capsys, entorno_falso):
    guion = guion_completo()
    teclado = Teclado(
        "Oficina",
        guion.proyecto,
        guion.necesidad,
        *guion.respuestas_cliente[:7],
        # N6: cierra; la primera vez sin confirmar.
        "x",
        "El cliente desistió",
        "n",
        "x",
        "El cliente desistió",
        "s",
        "Laura",
    )
    op = operador(ServiciosSimulados(), entorno_falso)
    assert ejecutar(op, comando("nueva"), configuracion(tmp_path), teclado) == 0
    salida = capsys.readouterr().out
    assert "La sesión sigue abierta." in salida
    assert "Cerrada sin módulo validado." in salida
    [vista] = op.sesiones()
    cierre = op.estado(vista.id_sesion)["sesion"].cierre
    assert (cierre.revisor, cierre.motivo) == ("Laura", "El cliente desistió")


def test_se_cierra_una_sesion_detenida(tmp_path, capsys, entorno_falso):
    guion = guion_completo()
    teclado = Teclado(
        "Oficina",
        guion.proyecto,
        guion.necesidad,
        *guion.respuestas_cliente[:7],
        *["a", ""] * 2,
        # N11 falla: cierra en lugar de reanudar.
        "x",
        "Docker no está disponible",
        "s",
        "",
    )
    op = operador(ServiciosSimulados(fallos_ejecucion=1), entorno_falso)
    assert ejecutar(op, comando("nueva"), configuracion(tmp_path), teclado) == 0
    assert "[r]eanudar, [x] cerrar la sesión o [s]alir: " in teclado.indicaciones
    [vista] = op.sesiones()
    assert vista.fase is Fase.CERRADA
    assert op.estado(vista.id_sesion)["sesion"].cierre.revisor == "Analista"


def test_el_subcomando_cerrar_cierra_una_sesion_en_pausa(tmp_path, capsys, entorno_falso):
    guion = guion_completo()
    op = operador(ServiciosSimulados(), entorno_falso)
    teclado = Teclado("Oficina", guion.proyecto, guion.necesidad, "/salir")
    assert ejecutar(op, comando("nueva"), configuracion(tmp_path), teclado) == 0
    [vista] = op.sesiones()
    cerrar = comando(f"cerrar {vista.id_sesion}")

    assert ejecutar(op, cerrar, configuracion(tmp_path), Teclado("Sesión de prueba", "")) == 0
    assert op.vista(vista.id_sesion).pausa.punto == "dialogo"
    teclado = Teclado("Sesión de prueba", "sí", "Julián")
    assert ejecutar(op, cerrar, configuracion(tmp_path), teclado) == 0
    assert op.vista(vista.id_sesion).fase is Fase.CERRADA
    assert ejecutar(op, cerrar, configuracion(tmp_path), Teclado()) == 1
    salida = capsys.readouterr().out
    assert "multiagente cerrar " + vista.id_sesion in salida
    assert "Cerrada sin módulo validado." in salida
    assert "ya terminó" in salida
