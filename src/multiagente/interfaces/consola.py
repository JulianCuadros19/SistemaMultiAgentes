"""Interfaz de consola: el comando `multiagente` y el bucle con que una persona opera una sesión.

La persona responde como cliente y decide en los tres puntos de control; en N17 puede revisar el
código y ejecutar pruebas propias en el entorno aislado (RF-38). Todo pasa por el `Operador`,
igual que en la web, de modo que ambas interfaces aplican las mismas reglas.

Uso:
    multiagente nueva
    multiagente continuar ID
    multiagente sesiones
    multiagente ver ID
    multiagente exportar ID CARPETA
"""

import argparse
import logging
import sys
import time
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psycopg
from pydantic import ValidationError

from multiagente.core.configuracion import ConfiguracionInterfaces
from multiagente.core.esquemas.especificacion_diseno import EspecificacionDiseno
from multiagente.core.esquemas.requerimiento import HistoriaUsuario, RequerimientoFormal
from multiagente.interfaces.documentos import (
    ErrorExportacion,
    especificacion_md,
    requerimientos_md,
)
from multiagente.interfaces.operacion import (
    ErrorOperacion,
    Operador,
    VistaSesion,
    abrir_operador,
    observaciones_de_pruebas,
)
from multiagente.orquestador.ejecucion import Avance
from multiagente.orquestador.estado import Decision, PruebasPropias, VersionCodigo
from multiagente.sandbox.ejecutor import ErrorEntornoAislado

SALIR = "/salir"
"""Lo que escribe la persona, como cliente, para dejar la sesión en pausa."""

REVISORES = {"requerimientos": "Analista", "especificacion": "Arquitecto", "final": "Revisor"}
"""Rol que decide en cada punto de control, si la persona no da su nombre."""

ACUSE_CONFIRMACION = (
    "Gracias. Con lo conversado estoy redactando los requerimientos; tarda unos segundos…"
)
"""Acuse de la respuesta que confirma el resumen: la síntesis que sigue tarda de 6 a 16 s."""

REPORTE = "REPORTE_VALIDACION.md"


# Presentación de los puntos de control ------------------------------------------------------


def mostrar_requerimientos(datos: dict[str, Any]) -> None:
    """Imprime los artefactos que la persona revisa en N6, en el formato del Anexo A."""
    print("\n=== Punto de control N6: requerimientos ===\n")
    print(
        requerimientos_md(
            [HistoriaUsuario.model_validate(historia) for historia in datos["historias"]],
            [RequerimientoFormal.model_validate(r) for r in datos["requerimientos"]],
            datos["referencias"],
        )
    )
    if datos["defectos"]:
        print("Defectos de calidad sin corregir (escalados al analista):")
        for defecto in datos["defectos"]:
            print(f"  - {defecto}")
    else:
        print("Verificación de calidad (RF-07): sin defectos.")


def mostrar_especificacion(datos: dict[str, Any]) -> None:
    """Imprime lo que la persona revisa en N9: el registro de decisión y la especificación."""
    print("\n=== Punto de control N9: especificación de diseño ===\n")
    print(datos["registro_decision"])
    print()
    print(especificacion_md(EspecificacionDiseno.model_validate(datos["especificacion"])))
    if datos["errores"]:
        print("Errores de validación (Anexo B); solo se admite el rechazo:")
        for error in datos["errores"]:
            print(f"  - {error}")
    else:
        print("Validaciones del Anexo B: sin errores.")


def mostrar_validacion(datos: dict[str, Any]) -> None:
    """Imprime lo que la persona revisa en N17: los archivos del módulo y su reporte (RF-38).

    El reporte del tester ya reúne el veredicto, el dictamen por caso, la conformidad por
    módulo, los hallazgos por severidad, la ejecución y las reglas no evaluadas.
    """
    print(f"\n=== Punto de control N17: versión {datos['version']} del módulo ===\n")
    for ruta in datos["archivos"]:
        print(f"  {ruta}")
    print()
    print(datos["reporte"] or "(El tester no emitió reporte.)")
    print(
        f"Iteración {datos['iteracion']} de {datos['limite_iteraciones']} del ciclo de "
        "corrección. Si rechaza, el desarrollador corrige y la cuenta sigue; alcanzado el límite, "
        "un rechazo del tester escala la sesión a una persona."
    )


PRESENTACION: dict[str, Callable[[dict[str, Any]], None]] = {
    "requerimientos": mostrar_requerimientos,
    "especificacion": mostrar_especificacion,
    "final": mostrar_validacion,
}


def mostrar_pruebas_propias(pruebas: PruebasPropias) -> None:
    """Imprime el resultado de las pruebas propias de la persona en N17."""
    ejecucion = pruebas.ejecucion
    print(f"\nPruebas propias en el entorno aislado ({ejecucion.duracion_ms} ms):")
    for prueba in ejecucion.pruebas:
        detalle = prueba.mensaje.strip().splitlines()[-1] if prueba.mensaje.strip() else ""
        print(f"  {prueba.resultado:7} {prueba.identificador}{f' · {detalle}' if detalle else ''}")
    for error in ejecucion.errores_recoleccion:
        print(f"  sin recolectar: {error.splitlines()[0]}")
    if not ejecucion.pruebas and not ejecucion.errores_recoleccion:
        print("  No se encontró ninguna prueba: las funciones deben llamarse test_*.")


def escribir_version(carpeta: Path, version: VersionCodigo, reporte: str | None) -> Path:
    """Escribe los archivos de una versión y su reporte de validación en `carpeta/v<n>/`.

    Args:
        carpeta: Carpeta de la sesión.
        version: Versión del módulo.
        reporte: Reporte de validación de la versión, si lo hay.

    Returns:
        La carpeta de la versión.
    """
    destino = carpeta / f"v{version.numero}"
    for ruta, contenido in version.archivos.items():
        archivo = destino / ruta
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text(contenido, encoding="utf-8")
    if reporte:
        (destino / REPORTE).write_text(reporte, encoding="utf-8")
    return destino


def recorrido(avance: Avance) -> str:
    """Nodos ejecutados en un avance, abreviados como N10 → N11."""
    return " → ".join(nodo.split("_")[0].upper() for nodo in avance.nodos)


# Bucle de operación ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DecisionHumana:
    """Decisión de una persona en un punto de control."""

    decision: Decision
    revisor: str
    observaciones: str | None = None
    pruebas_propias: PruebasPropias | None = None


RespondeCliente = Callable[[Operador, VistaSesion], str | None]
"""Da la respuesta del cliente a la pregunta pendiente, o None para dejar la sesión en pausa."""

DecideRevisor = Callable[[Operador, VistaSesion], DecisionHumana | None]
"""Da la decisión en el punto de control pendiente, o None para dejar la sesión en pausa."""

ConfirmaReanudar = Callable[[VistaSesion], bool]
"""Indica si se reanuda una sesión detenida por una falla."""


@dataclass
class Tiempos:
    """Tiempo del sistema en este proceso, sin la espera humana ni el cliente simulado.

    Attributes:
        sistema: Duración total de los avances del grafo.
        turnos: Respuestas del cliente que terminan en la siguiente pregunta (RNF-01).
        cierres: Respuestas que cierran la elicitación: incluyen la síntesis y su verificación
            (N5 y N6), no una pregunta.
    """

    sistema: float = 0.0
    turnos: list[float] = field(default_factory=list)
    cierres: list[float] = field(default_factory=list)

    def anotar(self, segundos: float, tras_responder: VistaSesion | None = None) -> None:
        """Suma un avance del sistema y, si respondía al cliente, lo clasifica.

        Args:
            segundos: Duración del avance.
            tras_responder: Vista de la sesión después de una respuesta del cliente: si espera
                otra respuesta, fue un turno; si no, el cierre de la elicitación.
        """
        self.sistema += segundos
        if tras_responder is not None:
            pausa = tras_responder.pausa
            otra_pregunta = pausa is not None and pausa.punto == "dialogo"
            (self.turnos if otra_pregunta else self.cierres).append(segundos)


def _avanzar(
    operador: Operador,
    id_sesion: str,
    accion: Callable[[], object],
    tiempos: Tiempos,
    del_cliente: bool = False,
) -> object | None:
    """Ejecuta un avance, mide su duración y muestra una falla sin interrumpir la consola.

    Una falla de un nodo deja la sesión detenida: el bucle la muestra y ofrece reanudarla.
    """
    inicio = time.perf_counter()
    try:
        resultado = accion()
    except ErrorOperacion as error:
        print(f"(No se pudo: {error})")
        return None
    except Exception as error:
        # Un nodo falló: la sesión queda detenida y el bucle ofrece reanudarla.
        print(f"\n(El sistema se detuvo por un error: {type(error).__name__}: {error})")
        resultado = None
    segundos = time.perf_counter() - inicio
    try:
        tras = operador.vista(id_sesion) if del_cliente else None
    except ErrorOperacion:
        tras = None
    tiempos.anotar(segundos, tras)
    return resultado


def abrir_sesion(
    operador: Operador,
    cliente: str,
    proyecto: str,
    necesidad: str,
    tiempos: Tiempos | None = None,
) -> str:
    """Abre una sesión con la necesidad del cliente y la lleva hasta la primera pregunta.

    Args:
        operador: Operador del sistema.
        cliente: Nombre del cliente.
        proyecto: Proyecto de los requerimientos.
        necesidad: Primera intervención del cliente.
        tiempos: Dónde sumar la duración; la apertura cuenta como el primer turno.

    Returns:
        El identificador de la sesión, aunque un nodo haya fallado al abrirla.

    Raises:
        ErrorOperacion: Si falta algún dato.
    """
    if not all(texto.strip() for texto in (cliente, proyecto, necesidad)):
        raise ErrorOperacion("El cliente, el proyecto y la necesidad son obligatorios.")
    id_sesion = str(uuid.uuid4())
    print(f"Sesión {id_sesion}\nCliente> {necesidad}")
    _avanzar(
        operador,
        id_sesion,
        lambda: operador.iniciar(cliente, proyecto, necesidad, id_sesion),
        tiempos or Tiempos(),
        del_cliente=True,
    )
    return id_sesion


def operar(
    operador: Operador,
    id_sesion: str,
    responder_cliente: RespondeCliente,
    decidir: DecideRevisor,
    reanudar: ConfirmaReanudar,
    tiempos: Tiempos | None = None,
) -> VistaSesion | None:
    """Atiende cada pausa de la sesión hasta que termina o la persona la deja en pausa.

    Args:
        operador: Operador del sistema.
        id_sesion: Identificador de la sesión.
        responder_cliente: Quién responde como cliente.
        decidir: Quién decide en los puntos de control.
        reanudar: Si se reanuda una sesión detenida por una falla.
        tiempos: Dónde sumar la duración de cada avance.

    Returns:
        La vista final de la sesión, o None si la sesión no existe.
    """
    tiempos = tiempos or Tiempos()
    continuar = f"multiagente continuar {id_sesion}"
    while True:
        try:
            vista = operador.vista(id_sesion)
        except ErrorOperacion as error:
            print(error)
            return None
        if vista.detenida:
            print(f"\n{vista.describir()}.")
            if vista.error:
                print(f"Error: {vista.error}")
            if not reanudar(vista):
                print(f"Sesión detenida. Reanúdela con: {continuar}")
                return vista
            print("(Reanudando…)")
            _avanzar(operador, id_sesion, lambda: operador.reanudar(id_sesion), tiempos)
            continue
        if vista.pausa is None:
            print(f"\nSesión {id_sesion}: {vista.describir()}.")
            return vista

        pausa = vista.pausa
        if pausa.datos.get("aviso"):
            print(f"(Aviso: {pausa.datos['aviso']})")
        if pausa.punto == "dialogo":
            for observacion in pausa.datos["observaciones_revisor"]:
                print(f"(Observación del revisor: {observacion})")
            ultimo = f"   [{tiempos.turnos[-1]:.1f} s]" if tiempos.turnos else ""
            print(f"Elicitador> {pausa.datos['pregunta']}{ultimo}")
            respuesta = responder_cliente(operador, vista)
            if respuesta is None:
                print(f"Sesión en pausa. Reanúdela con: {continuar}")
                return vista
            if vista.confirma_resumen:
                print(ACUSE_CONFIRMACION)
            _avanzar(
                operador,
                id_sesion,
                lambda r=respuesta: operador.responder(id_sesion, r),
                tiempos,
                del_cliente=True,
            )
            continue

        PRESENTACION[pausa.punto](pausa.datos)
        decision = decidir(operador, vista)
        if decision is None:
            print(f"Sesión en pausa: {vista.describir().lower()}. Reanúdela con: {continuar}")
            return vista
        print("(Procesando…)")
        avance = _avanzar(
            operador,
            id_sesion,
            lambda d=decision: operador.decidir(
                id_sesion, d.decision, d.revisor, d.observaciones, d.pruebas_propias
            ),
            tiempos,
        )
        if isinstance(avance, Avance):
            print(f"{recorrido(avance)} · fase {avance.fase}")


# La persona por teclado ---------------------------------------------------------------------


def cliente_por_teclado(leer: Callable[[str], str] = input) -> RespondeCliente:
    """Respuestas del cliente escritas en la consola; `/salir` deja la sesión en pausa."""

    def responder(operador: Operador, vista: VistaSesion) -> str | None:
        texto = leer("Cliente> ").strip()
        while not texto:
            texto = leer("Cliente> ").strip()
        return None if texto == SALIR else texto

    return responder


def reanudar_por_teclado(leer: Callable[[str], str] = input) -> ConfirmaReanudar:
    """Pregunta a la persona si reanuda una sesión detenida."""
    return lambda vista: leer("[r]eanudar o [s]alir: ").strip().lower().startswith("r")


class RevisorPorTeclado:
    """Decisiones de la persona en los puntos de control, escritas en la consola."""

    def __init__(self, carpeta_trabajo: Path, leer: Callable[[str], str] = input) -> None:
        """Prepara el revisor.

        Args:
            carpeta_trabajo: Donde se escribe el código de cada versión para revisarlo.
            leer: Lectura de la consola; las pruebas la reemplazan.
        """
        self.carpeta_trabajo = carpeta_trabajo
        self.leer = leer

    def __call__(self, operador: Operador, vista: VistaSesion) -> DecisionHumana | None:
        """Ofrece las opciones del punto de control hasta que la persona decide o sale."""
        punto = vista.pausa.punto
        revisor = REVISORES[punto]
        bloqueada = bool(vista.pausa.datos.get("errores"))
        pruebas: PruebasPropias | None = None
        opciones = ("" if bloqueada else "[a]probar, ") + "[r]echazar"
        if punto == "final":
            opciones += ", [p]robar con un archivo propio, [c]ódigo"
        while True:
            eleccion = self.leer(f"\n{opciones} o [s]alir: ").strip().lower()[:1]
            if eleccion == "a" and not bloqueada:
                return DecisionHumana(Decision.APROBADO, self._nombre(revisor), None, pruebas)
            if eleccion == "r":
                sugeridas = observaciones_de_pruebas(pruebas) if pruebas else ""
                if sugeridas:
                    print(f"Observaciones sugeridas por sus pruebas:\n{sugeridas}")
                indicacion = " (Enter: usar las sugeridas)" if sugeridas else ""
                observaciones = (
                    self.leer(
                        f"Observaciones para el agente (qué debe cambiar){indicacion}: "
                    ).strip()
                    or sugeridas
                )
                return DecisionHumana(
                    Decision.RECHAZADO, self._nombre(revisor), observaciones or None, pruebas
                )
            if eleccion == "p" and punto == "final":
                pruebas = self._probar(operador, vista) or pruebas
            elif eleccion == "c" and punto == "final":
                self._escribir_codigo(operador, vista)
            elif eleccion == "s":
                return None
            else:
                print("Opción no válida.")

    def _nombre(self, revisor: str) -> str:
        return self.leer(f"Su nombre, como revisor (Enter: «{revisor}»): ").strip() or revisor

    def _probar(self, operador: Operador, vista: VistaSesion) -> PruebasPropias | None:
        ruta = Path(self.leer("Archivo de pruebas propio (ruta local): ").strip()).expanduser()
        try:
            contenido = ruta.read_text(encoding="utf-8")
        except OSError as error:
            print(f"No se pudo leer {ruta}: {error}")
            return None
        nombre = ruta.name if ruta.name.startswith("test_") else f"test_{ruta.name}"
        try:
            pruebas = operador.probar_propias(vista.id_sesion, {f"tests/{nombre}": contenido})
        except (ErrorOperacion, ErrorEntornoAislado) as error:
            print(f"No se pudieron ejecutar: {error}")
            return None
        mostrar_pruebas_propias(pruebas)
        return pruebas

    def _escribir_codigo(self, operador: Operador, vista: VistaSesion) -> None:
        estado = operador.estado(vista.id_sesion)
        version = estado["codigo"].vigente
        destino = escribir_version(
            self.carpeta_trabajo / vista.id_sesion, version, estado["validacion"].reporte
        )
        print(f"Código de la versión {version.numero} escrito en {destino}")


# Comando multiagente -------------------------------------------------------------------------


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="multiagente",
        description="Opera el sistema multiagente: de la conversación con el cliente al módulo.",
    )
    comandos = parser.add_subparsers(dest="comando", required=True)
    comandos.add_parser("nueva", help="Abre una sesión: la persona conversa como cliente.")
    continuar = comandos.add_parser("continuar", help="Reanuda una sesión en pausa o detenida.")
    continuar.add_argument("sesion")
    comandos.add_parser("sesiones", help="Lista las sesiones guardadas.")
    ver = comandos.add_parser("ver", help="Muestra la trazabilidad de una sesión (RF-33).")
    ver.add_argument("sesion")
    exportar = comandos.add_parser("exportar", help="Exporta el módulo validado (RF-35).")
    exportar.add_argument("sesion")
    exportar.add_argument("carpeta", type=Path)
    return parser


def _listar(operador: Operador) -> None:
    sesiones = operador.sesiones()
    if not sesiones:
        print("No hay sesiones guardadas.")
    for vista in sesiones:
        print(
            f"{vista.id_sesion}  {vista.creada:%Y-%m-%d %H:%M}  {vista.cliente} · "
            f"{vista.proyecto}\n    {vista.describir()}"
        )


def _exportar(operador: Operador, id_sesion: str, carpeta: Path) -> None:
    paquete = operador.exportar(id_sesion)
    if carpeta.exists() and any(carpeta.iterdir()):
        raise ErrorExportacion(f"La carpeta {carpeta} no está vacía; elija otra.")
    for ruta, contenido in paquete.items():
        archivo = carpeta / ruta
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text(contenido, encoding="utf-8")
    print(f"Módulo exportado en {carpeta}: {len(paquete)} archivos.")


def ejecutar(
    operador: Operador,
    argumentos: argparse.Namespace,
    configuracion: ConfiguracionInterfaces,
    leer: Callable[[str], str] = input,
) -> int:
    """Ejecuta un subcomando de consola sobre un operador ya abierto.

    Args:
        operador: Operador del sistema.
        argumentos: Subcomando y sus argumentos.
        configuracion: Carpeta de trabajo de la consola.
        leer: Lectura de la consola; las pruebas la reemplazan.

    Returns:
        Código de salida del proceso: 0 si terminó bien, 1 si la operación no correspondía.
    """
    revisor = RevisorPorTeclado(configuracion.carpeta_trabajo, leer)
    cliente = cliente_por_teclado(leer)
    reanudar = reanudar_por_teclado(leer)
    try:
        if argumentos.comando == "sesiones":
            _listar(operador)
        elif argumentos.comando == "ver":
            print(operador.trazabilidad(argumentos.sesion))
        elif argumentos.comando == "exportar":
            _exportar(operador, argumentos.sesion, argumentos.carpeta)
        elif argumentos.comando == "nueva":
            print(
                "Escriba /salir en cualquier respuesta del cliente para dejar la sesión en pausa."
            )
            id_sesion = abrir_sesion(
                operador,
                leer("Cliente: ").strip(),
                leer("Proyecto: ").strip(),
                leer("¿Qué necesita? ").strip(),
            )
            operar(operador, id_sesion, cliente, revisor, reanudar)
        elif argumentos.comando == "continuar":
            operar(operador, argumentos.sesion, cliente, revisor, reanudar)
    except (ErrorOperacion, ErrorExportacion) as error:
        print(error)
        return 1
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Punto de entrada del comando `multiagente`.

    Args:
        argv: Argumentos; si se omiten, los de la línea de comandos.

    Returns:
        Código de salida del proceso.
    """
    argumentos = _parser().parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="(aviso) %(message)s")
    configuracion = ConfiguracionInterfaces()
    try:
        with abrir_operador(configuracion) as operador:
            return ejecutar(operador, argumentos, configuracion)
    except (psycopg.OperationalError, ValidationError) as error:
        print(
            f"No se pudo abrir el sistema: {error}\n"
            "Revise que los servicios estén arriba (docker compose up -d --wait) y que exista el "
            "archivo .env.",
            file=sys.stderr,
        )
        return 2
    except KeyboardInterrupt:
        print(
            "\nInterrumpido. Las sesiones quedan guardadas; reanúdelas con multiagente continuar."
        )
        return 130
