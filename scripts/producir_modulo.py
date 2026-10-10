"""Produce un módulo con los cuatro agentes reales, de la necesidad a la aprobación final (paso 11).

Una persona conversa con el elicitador como cliente y decide en los tres puntos de control: los
requerimientos (N6), la especificación de diseño (N9) y el módulo que aprobó el tester (N17). Cada
rechazo vuelve al agente anterior con sus observaciones. Trabajan los cuatro agentes reales:
- elicitador: BGE-M3 en N2 y Azure OpenAI en N3 y N5;
- arquitecto: BGE-M3 en N7 y Azure OpenAI en N8;
- desarrollador: Azure OpenAI en N10, sin recuperación;
- tester: entorno aislado en N11, análisis en N12, BGE-M3 en N13 y el juez en N14.

El bucle es el de la consola del sistema (`multiagente`, paso 12); este script agrega el cliente
simulado, las decisiones guionizadas y la medición. La sesión se guarda en PostgreSQL: `/salir`
la deja en pausa y --sesion la reanuda en otro proceso, también tras una falla (RF-28). Con
--salida, cada versión del módulo y su reporte se escriben en `<salida>/<sesión>/v<n>/`.

Con --simulado, un modelo hace de cliente a partir de un caso sintético. --aprobar aprueba donde
se admite, y --rechazar PUNTO OBSERVACION rechaza una vez en ese punto (requerimientos,
especificacion o final). Sin decisión, la sesión queda en pausa en el punto de control. Una
sesión escalada también queda en pausa en N17: la reabre o la cierra una persona, con
`multiagente continuar ID` o `multiagente cerrar ID`.

Cada llamada al modelo se agrega a docs/mediciones/paso-11-extremo-a-extremo.jsonl con su sesión,
sin el contenido de los mensajes. Requiere `docker compose up -d --wait`, el corpus ingerido, la
imagen del entorno aislado y el archivo .env. Tiene costo.

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
from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from multiagente.core.configuracion import (
    ConfiguracionAzureOpenAI,
    ConfiguracionInterfaces,
    ConfiguracionModelos,
)
from multiagente.interfaces.cliente_simulado import ClienteSimulado, cargar_caso
from multiagente.interfaces.consola import (
    REVISORES,
    DecideRevisor,
    DecisionHumana,
    RespondeCliente,
    RevisorPorTeclado,
    Tiempos,
    abrir_sesion,
    cliente_por_teclado,
    escribir_version,
    operar,
    reanudar_por_teclado,
)
from multiagente.interfaces.operacion import ErrorOperacion, Operador, VistaSesion, abrir_operador
from multiagente.llm.cliente import crear_cliente
from multiagente.llm.traza import RegistroLlamada, RegistroPorSesion
from multiagente.orquestador.estado import Decision, Severidad

RAIZ = Path(__file__).resolve().parents[1]
ARCHIVO_MEDICIONES = RAIZ / "docs" / "mediciones" / "paso-11-extremo-a-extremo.jsonl"


@dataclass
class Guion:
    """Decisiones automáticas del modo simulado."""

    rechazos: dict[str, str]
    aprobar: bool = False


def responder_simulado(simulado: ClienteSimulado, registro: RegistroPorSesion) -> RespondeCliente:
    """El cliente simulado responde la pregunta pendiente; su llamada queda con la sesión."""

    def responder(operador: Operador, vista: VistaSesion) -> str:
        conversacion = operador.estado(vista.id_sesion)["conversacion"]
        with registro.en_sesion(vista.id_sesion):
            respuesta = simulado.responder(conversacion, vista.pausa.datos["pregunta"])
        print(f"Cliente> {respuesta}")
        return respuesta

    return responder


def revisor_simulado(guion: Guion, salida: Path | None) -> DecideRevisor:
    """Decide con el guion; en N17 escribe antes la versión si se pidió --salida."""

    def decidir(operador: Operador, vista: VistaSesion) -> DecisionHumana | None:
        punto, datos = vista.pausa.punto, vista.pausa.datos
        revisor = REVISORES[punto]
        if punto == "final" and salida:
            estado = operador.estado(vista.id_sesion)
            if (version := estado["codigo"].vigente) is not None:
                destino = escribir_version(
                    salida / vista.id_sesion, version, estado["validacion"].reporte
                )
                print(f"\nCódigo y reporte escritos en {destino}")
        if datos.get("escalado"):
            print(
                "\nLa sesión escaló sin módulo aprobado: queda en pausa en N17 para que una "
                "persona la devuelva a un agente o la cierre."
            )
            return None
        if punto in guion.rechazos:
            observaciones = guion.rechazos.pop(punto)
            print(f"\nDecisión simulada ({revisor}): rechazar · {observaciones}")
            return DecisionHumana(Decision.RECHAZADO, revisor, observaciones)
        if guion.aprobar and not (datos.get("bloqueo") or datos.get("defectos")):
            print(f"\nDecisión simulada ({revisor}): aprobar")
            return DecisionHumana(Decision.APROBADO, revisor)
        return None

    return decidir


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


def resumir(operador: Operador, id_sesion: str, tiempos: Tiempos, salida: Path | None) -> None:
    """Imprime versiones, iteraciones, tiempo y costo por nodo del módulo."""
    print(f"\n=== Resumen de la sesión {id_sesion} ===")
    try:
        estado = operador.estado(id_sesion)
        historial = operador.historial(id_sesion)
    except ErrorOperacion:
        estado, historial = None, []
    for version, validacion in historial:
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
            escribir_version(salida / id_sesion, version, validacion.reporte)
    if estado is not None:
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

    configuracion = ConfiguracionInterfaces(traza_llamadas=ARCHIVO_MEDICIONES)
    if argumentos.salida:
        configuracion = configuracion.model_copy(update={"carpeta_trabajo": argumentos.salida})
    caso = cargar_caso(argumentos.simulado) if argumentos.simulado else None
    tiempos = Tiempos()
    with abrir_operador(configuracion) as operador:
        if caso:
            simulado = ClienteSimulado(
                crear_cliente(ConfiguracionAzureOpenAI()),
                ConfiguracionModelos().despliegue_cliente_simulado,
                caso,
                operador.registro,
            )
            responder = responder_simulado(simulado, operador.registro)
            decidir = revisor_simulado(Guion(rechazos, argumentos.aprobar), argumentos.salida)
            reanudar = reanudar_por_teclado(lambda indicacion: "s")
        else:
            responder = cliente_por_teclado()
            decidir = RevisorPorTeclado(configuracion.carpeta_trabajo)
            reanudar = reanudar_por_teclado()

        if argumentos.sesion:
            id_sesion = argumentos.sesion
            print(f"Sesión {id_sesion} reanudada.")
        else:
            if caso:
                cliente, proyecto, necesidad = caso.cliente, caso.proyecto, caso.necesidad
            else:
                cliente = input("Cliente: ").strip()
                proyecto = input("Proyecto: ").strip()
                necesidad = input("¿Qué necesita? ").strip()
            id_sesion = abrir_sesion(operador, cliente, proyecto, necesidad, tiempos)
        try:
            operar(operador, id_sesion, responder, decidir, reanudar, tiempos)
        finally:
            resumir(operador, id_sesion, tiempos, argumentos.salida)


if __name__ == "__main__":
    main()
