"""Produce un módulo con los cuatro agentes reales, de la necesidad a la aprobación final (paso 11).

Una persona conversa con el elicitador como cliente y decide en los tres puntos de control: los
requerimientos (N6), la especificación de diseño (N9) y el módulo que aprobó el tester (N17). Cada
rechazo vuelve al agente anterior con sus observaciones. Trabajan los cuatro agentes reales:
- elicitador: BGE-M3 en N2 y Azure OpenAI en N3 y N5;
- arquitecto: BGE-M3 en N7 y Azure OpenAI en N8;
- desarrollador: Azure OpenAI en N10, sin recuperación;
- tester: entorno aislado en N11, análisis en N12, BGE-M3 en N13 y el juez en N14.

La sesión se guarda en PostgreSQL: `/salir` la deja en pausa y --sesion la reanuda en otro
proceso, también tras una falla (RF-28). Con --salida, cada versión del módulo y su reporte se
escriben en `<salida>/<sesión>/v<n>/`, para revisar el código antes de decidir en N17.

Con --simulado, un modelo hace de cliente a partir de un caso sintético. --aprobar aprueba donde
se admite, y --rechazar PUNTO OBSERVACION rechaza una vez en ese punto (requerimientos,
especificacion o final). Sin decisión, la sesión queda en pausa en el punto de control.

Cada llamada al modelo se agrega a docs/mediciones/paso-11-extremo-a-extremo.jsonl, sin el
contenido de los mensajes. Requiere `docker compose up -d --wait`, el corpus ingerido, la imagen
del entorno aislado y el archivo .env. Tiene costo.

Uso:
    python scripts/producir_modulo.py --salida evaluacion/resultados
    python scripts/producir_modulo.py --sesion ID --salida evaluacion/resultados
    python scripts/producir_modulo.py --simulado evaluacion/casos/elicitacion-mutacion.md --aprobar
    python scripts/producir_modulo.py --simulado CASO --rechazar final "…" --aprobar
"""

import argparse
import json
import logging
import statistics
import time
import uuid
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg
from langgraph.graph.state import CompiledStateGraph

from multiagente.agentes.servicios import crear_servicios
from multiagente.core.configuracion import (
    ConfiguracionAzureOpenAI,
    ConfiguracionBaseDatos,
    ConfiguracionModelos,
)
from multiagente.interfaces.cliente_simulado import ClienteSimulado, cargar_caso
from multiagente.interfaces.consola import (
    mostrar_especificacion,
    mostrar_requerimientos,
    mostrar_validacion,
)
from multiagente.llm.cliente import crear_cliente
from multiagente.llm.traza import RegistroJsonl, RegistroLlamada
from multiagente.orquestador.ejecucion import (
    Avance,
    avanzar,
    configuracion_hilo,
    iniciar_sesion,
    pausa_pendiente,
    validaciones,
)
from multiagente.orquestador.estado import Severidad, VersionCodigo
from multiagente.orquestador.grafo import construir_grafo
from multiagente.orquestador.simulacion import aprobar, rechazar
from multiagente.persistencia.puntos_control import abrir_checkpointer

RAIZ = Path(__file__).resolve().parents[1]
ARCHIVO_MEDICIONES = RAIZ / "docs" / "mediciones" / "paso-11-extremo-a-extremo.jsonl"
SALIR = "/salir"
REVISORES = {"requerimientos": "Analista", "especificacion": "Arquitecto", "final": "Revisor"}
PRESENTACION = {
    "requerimientos": mostrar_requerimientos,
    "especificacion": mostrar_especificacion,
    "final": mostrar_validacion,
}
REPORTE = "REPORTE_VALIDACION.md"


@dataclass
class Guion:
    """Decisiones automáticas del modo simulado."""

    rechazos: dict[str, str]
    aprobar: bool = False


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

    def medir(self, accion: Callable[[], Avance], turno: bool = False) -> Avance:
        """Ejecuta un avance del grafo, suma su duración y, si responde al cliente, la registra."""
        inicio = time.perf_counter()
        avance = accion()
        segundos = time.perf_counter() - inicio
        self.sistema += segundos
        if turno:
            pregunta = avance.pausa is not None and avance.pausa.punto == "dialogo"
            (self.turnos if pregunta else self.cierres).append(segundos)
        return avance


def decidir(punto: str, datos: dict[str, Any], guion: Guion | None) -> dict[str, str] | None:
    """Pide la decisión a la persona o la toma del guion; None deja la sesión en pausa."""
    revisor = REVISORES[punto]
    if guion is not None:
        if punto in guion.rechazos:
            observaciones = guion.rechazos.pop(punto)
            print(f"\nDecisión simulada ({revisor}): rechazar · {observaciones}")
            return rechazar(observaciones, revisor)
        if guion.aprobar and not (datos.get("defectos") or datos.get("errores")):
            print(f"\nDecisión simulada ({revisor}): aprobar")
            return aprobar(revisor)
        return None
    eleccion = input("\n[a]probar, [r]echazar o [s]alir: ").strip().lower()
    if not eleccion.startswith(("a", "r")):
        return None
    nombre = input(f"Revisor [{revisor}]: ").strip() or revisor
    if eleccion.startswith("a"):
        return aprobar(nombre)
    return rechazar(input("Observaciones: ").strip(), nombre)


def guardar(carpeta: Path, version: VersionCodigo, reporte: str | None) -> Path:
    """Escribe los archivos de una versión y su reporte de validación en `carpeta/v<n>/`."""
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


def operar(
    app: CompiledStateGraph,
    id_sesion: str,
    avance: Avance,
    simulado: ClienteSimulado | None,
    guion: Guion | None,
    tiempos: Tiempos,
    salida: Path | None,
) -> None:
    """Responde cada pausa hasta que la sesión termina o la persona la deja en pausa."""
    while avance.pausa is not None:
        pausa = avance.pausa
        if pausa.datos.get("aviso"):
            print(f"(Aviso: {pausa.datos['aviso']})")
        if pausa.punto == "dialogo":
            for observacion in pausa.datos["observaciones_revisor"]:
                print(f"(Observación del revisor: {observacion})")
            ultimo = f"   [{tiempos.turnos[-1]:.1f} s]" if tiempos.turnos else ""
            print(f"Elicitador> {pausa.datos['pregunta']}{ultimo}")
            if simulado:
                estado = app.get_state(configuracion_hilo(id_sesion)).values
                respuesta = simulado.responder(estado["conversacion"], pausa.datos["pregunta"])
                print(f"Cliente> {respuesta}")
            else:
                respuesta = input("Cliente> ").strip()
            if respuesta == SALIR:
                print(f"Sesión en pausa. Reanúdala con --sesion {id_sesion}")
                return
            avance = tiempos.medir(lambda r=respuesta: avanzar(app, id_sesion, r), turno=True)
            continue

        PRESENTACION[pausa.punto](pausa.datos)
        if pausa.punto == "final" and salida:
            estado = app.get_state(configuracion_hilo(id_sesion)).values
            destino = guardar(salida, estado["codigo"].vigente, estado["validacion"].reporte)
            print(f"\nCódigo y reporte escritos en {destino}")
        decision = decidir(pausa.punto, pausa.datos, guion)
        if decision is None:
            print(f"Sesión en pausa en «{pausa.punto}». Reanúdala con --sesion {id_sesion}")
            return
        print("(Procesando…)")
        avance = tiempos.medir(lambda d=decision: avanzar(app, id_sesion, d))
        print(f"{recorrido(avance)} · fase {avance.fase}")


def llamadas_de_la_sesion(id_sesion: str) -> list[RegistroLlamada]:
    """Llamadas de la sesión en la traza, también las de procesos anteriores si se reanudó."""
    if not ARCHIVO_MEDICIONES.exists():
        return []
    llamadas = []
    for linea in ARCHIVO_MEDICIONES.read_text(encoding="utf-8").splitlines():
        datos = json.loads(linea)
        if datos.get("sesion") == id_sesion:
            llamadas.append(RegistroLlamada.model_validate(datos))
    return llamadas


def resumir(app: CompiledStateGraph, id_sesion: str, tiempos: Tiempos, salida: Path | None) -> None:
    """Imprime versiones, iteraciones, tiempo y costo por nodo del módulo."""
    estado = app.get_state(configuracion_hilo(id_sesion)).values
    print(f"\n=== Resumen de la sesión {id_sesion} ===")
    for version, validacion in validaciones(app, id_sesion):
        por_severidad = Counter(h.severidad for h in validacion.hallazgos)
        bloqueantes = Counter(
            h.regla for h in validacion.hallazgos if h.severidad is not Severidad.BAJA
        )
        cumplidos = sum(v.cumple for v in validacion.veredictos)
        alta, media, baja = (por_severidad[s] for s in Severidad)
        print(
            f"Versión {version.numero}: {validacion.veredicto} · {cumplidos} de "
            f"{len(validacion.plan_pruebas)} casos · hallazgos alta {alta}, media {media}, "
            f"baja {baja}{' · ' + str(dict(bloqueantes)) if bloqueantes else ''}"
        )
        if salida:
            guardar(salida, version, validacion.reporte)
    if "sesion" in estado:
        print(
            f"Fase: {estado['sesion'].fase} · versiones {len(estado['codigo'].versiones)} · "
            f"iteraciones {estado['control'].iteracion} de {estado['control'].limite_iteraciones}"
        )
    if tiempos.turnos:
        print(
            f"Turnos de diálogo: {len(tiempos.turnos)} · media "
            f"{statistics.mean(tiempos.turnos):.1f} s · máxima {max(tiempos.turnos):.1f} s "
            "(RNF-01: menos de 15 s)"
        )
    if tiempos.cierres:
        print(
            "Cierre de la elicitación (síntesis y verificación): "
            + ", ".join(f"{segundos:.1f} s" for segundos in tiempos.cierres)
        )
    print(
        f"Tiempo del sistema en este proceso: {tiempos.sistema / 60:.1f} min "
        "(RNF-01: 20 min por módulo)"
    )

    por_nodo: dict[str, list[RegistroLlamada]] = defaultdict(list)
    llamadas = llamadas_de_la_sesion(id_sesion)
    for llamada in llamadas:
        por_nodo[llamada.nodo].append(llamada)
    for nodo, del_nodo in sorted(por_nodo.items()):
        latencias = [llamada.latencia_ms / 1000 for llamada in del_nodo]
        costo = sum((llamada.costo_usd for llamada in del_nodo), Decimal(0))
        salida_tokens = sum(llamada.consumo.salida for llamada in del_nodo)
        razonamiento = sum(llamada.consumo.razonamiento for llamada in del_nodo)
        errores = sum(1 for llamada in del_nodo if llamada.error)
        print(
            f"  {nodo:17} {len(del_nodo):3} llamadas · media {statistics.mean(latencias):5.1f} s"
            f" · máx {max(latencias):5.1f} s · salida {salida_tokens:6} (razonamiento "
            f"{razonamiento}) · USD {costo:.4f}{f' · {errores} con error' if errores else ''}"
        )
    sistema = sum(
        (llamada.costo_usd for llamada in llamadas if llamada.nodo != "cliente_simulado"),
        Decimal(0),
    )
    print(f"Costo del sistema: USD {sistema:.4f} · {ARCHIVO_MEDICIONES.relative_to(RAIZ)}")


def main() -> None:
    """Opera la sesión desde la necesidad hasta la aprobación final del módulo."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sesion", help="Reanuda la sesión con este identificador.")
    parser.add_argument("--simulado", type=Path, help="Caso sintético; un modelo hace de cliente.")
    parser.add_argument(
        "--aprobar", action="store_true", help="Con --simulado, aprueba donde se admite."
    )
    parser.add_argument(
        "--rechazar",
        nargs=2,
        action="append",
        metavar=("PUNTO", "OBSERVACION"),
        help="Con --simulado, rechaza una vez en ese punto de control.",
    )
    parser.add_argument("--salida", type=Path, help="Carpeta donde escribir cada versión.")
    argumentos = parser.parse_args()
    if (argumentos.aprobar or argumentos.rechazar) and not argumentos.simulado:
        parser.error("--aprobar y --rechazar solo se usan con --simulado")
    rechazos = dict(argumentos.rechazar or [])
    if ajenos := sorted(set(rechazos) - set(REVISORES)):
        parser.error(f"Puntos de control desconocidos: {ajenos}; use {sorted(REVISORES)}")
    logging.basicConfig(level=logging.WARNING, format="(aviso) %(message)s")

    id_sesion = argumentos.sesion or str(uuid.uuid4())
    registro = RegistroJsonl(ARCHIVO_MEDICIONES, sesion=id_sesion)
    cliente_modelo = crear_cliente(ConfiguracionAzureOpenAI())
    caso = cargar_caso(argumentos.simulado) if argumentos.simulado else None
    simulado = (
        ClienteSimulado(
            cliente_modelo, ConfiguracionModelos().despliegue_cliente_simulado, caso, registro
        )
        if caso
        else None
    )
    guion = Guion(rechazos, argumentos.aprobar) if caso else None
    salida = argumentos.salida / id_sesion if argumentos.salida else None
    tiempos = Tiempos()
    cadena = ConfiguracionBaseDatos().cadena_conexion()
    with psycopg.connect(cadena, autocommit=True) as conexion, abrir_checkpointer() as puntos:
        servicios = crear_servicios(conexion, registro, cliente_modelo)
        app = construir_grafo(servicios).compile(checkpointer=puntos)

        if argumentos.sesion:
            pausa = pausa_pendiente(app, id_sesion)
            pendientes = app.get_state(configuracion_hilo(id_sesion)).next
            if pausa is not None:
                avance = Avance(nodos=(), pausa=pausa, fase=None)
                print(f"Sesión {id_sesion} reanudada en «{pausa.punto}».")
            elif pendientes:
                print(f"Sesión {id_sesion} reanudada tras una falla en {pendientes}.")
                avance = tiempos.medir(lambda: avanzar(app, id_sesion))
            else:
                print(f"La sesión {id_sesion} terminó o no existe.")
                resumir(app, id_sesion, tiempos, salida)
                return
        else:
            if caso:
                cliente, proyecto, necesidad = caso.cliente, caso.proyecto, caso.necesidad
            else:
                cliente = input("Cliente: ").strip()
                proyecto = input("Proyecto: ").strip()
                necesidad = input("¿Qué necesita? ").strip()
            print(f"Sesión {id_sesion}\nCliente> {necesidad}")
            avance = tiempos.medir(
                lambda: iniciar_sesion(app, cliente, proyecto, necesidad, id_sesion)[1], turno=True
            )

        try:
            operar(app, id_sesion, avance, simulado, guion, tiempos, salida)
        except Exception:
            pendientes = app.get_state(configuracion_hilo(id_sesion)).next
            print(f"\nFallo en {pendientes}. Reanuda la sesión con --sesion {id_sesion}")
            raise
        finally:
            resumir(app, id_sesion, tiempos, salida)


if __name__ == "__main__":
    main()
