"""Conversa con el agente elicitador real, desde la necesidad hasta la aprobación de N6 (paso 7).

El elicitador usa BGE-M3 en N2 y Azure OpenAI en N3 y N5; los demás agentes son simulados. La
sesión se guarda en PostgreSQL y puede reanudarse con --sesion en otro proceso (RF-28). Cada
llamada al modelo se agrega a docs/mediciones/paso-07-elicitador.jsonl, sin el contenido de los
mensajes. Requiere `docker compose up -d --wait`, el corpus ingerido y el archivo .env. Tiene
costo: cada llamada se cobra.

Con --simulado, un modelo hace de cliente. Para reproducir el camino humano sin intervenir:
--pausar-tras N deja la sesión en pausa tras N respuestas (para reanudarla con --sesion en otro
proceso), --rechazar rechaza una vez en N6 con esa observación y --aprobar aprueba en N6.

Uso:
    python scripts/conversar_elicitador.py
    python scripts/conversar_elicitador.py --sesion ID
    python scripts/conversar_elicitador.py --simulado evaluacion/casos/elicitacion-mutacion.md
    python scripts/conversar_elicitador.py --simulado CASO --pausar-tras 2
    python scripts/conversar_elicitador.py --simulado CASO --sesion ID --rechazar "…" --aprobar
"""

import argparse
import logging
import statistics
import time
import uuid
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg
from langgraph.graph.state import CompiledStateGraph

from multiagente.agentes.elicitador.servicio import crear_agente_elicitador
from multiagente.core.configuracion import (
    ConfiguracionAzureOpenAI,
    ConfiguracionBaseDatos,
    ConfiguracionModelos,
)
from multiagente.interfaces.cliente_simulado import ClienteSimulado, cargar_caso
from multiagente.llm.cliente import crear_cliente
from multiagente.llm.traza import RegistroJsonl
from multiagente.orquestador.ejecucion import (
    Avance,
    avanzar,
    configuracion_hilo,
    iniciar_sesion,
    pausa_pendiente,
)
from multiagente.orquestador.grafo import construir_grafo
from multiagente.orquestador.servicios import Servicios
from multiagente.orquestador.simulacion import ServiciosSimulados
from multiagente.persistencia.puntos_control import abrir_checkpointer

RAIZ = Path(__file__).resolve().parents[1]
ARCHIVO_MEDICIONES = RAIZ / "docs" / "mediciones" / "paso-07-elicitador.jsonl"
SALIR = "/salir"


def medir(accion: Callable[[], Avance]) -> tuple[Avance, float]:
    """Ejecuta un avance del grafo y mide su duración en segundos."""
    inicio = time.perf_counter()
    avance = accion()
    return avance, time.perf_counter() - inicio


def mostrar_requerimientos(datos: dict[str, Any]) -> None:
    """Imprime los artefactos que la persona revisa en N6."""
    print("\n=== Punto de control N6: requerimientos ===")
    for historia in datos["historias"]:
        enunciado = historia["enunciado"]
        print(
            f"\n{historia['id']} · Como {enunciado['como']}, quiero {enunciado['quiero']}, "
            f"para {enunciado['para']} (prioridad {historia['prioridad']})"
        )
        for supuesto in historia["supuestos"]:
            print(f"  Supuesto: {supuesto}")
        for pregunta in historia["preguntas_abiertas"]:
            print(f"  Pregunta abierta: {pregunta}")
    for requerimiento in datos["requerimientos"]:
        descripcion = requerimiento["descripcion"]
        print(
            f"\n{requerimiento['id_requerimiento']} v{requerimiento['version']} · "
            f"módulo {requerimiento['modulo']} · impacto {requerimiento['impacto']}"
        )
        print(f"  Precondición: {descripcion['precondicion']}")
        print(f"  Regla de negocio: {descripcion['regla_negocio']}")
        for dato in descripcion["datos_entrada"]:
            obligatorio = "obligatorio" if dato["obligatorio"] else "opcional"
            restriccion = f", {dato['restriccion']}" if dato["restriccion"] else ""
            print(f"  Entrada: {dato['nombre']} ({dato['tipo']}, {obligatorio}{restriccion})")
        for dato in descripcion["datos_salida"]:
            formato = f", {dato['formato']}" if dato["formato"] else ""
            print(f"  Salida: {dato['nombre']} ({dato['tipo']}{formato})")
        for escenario in requerimiento["criterios_aceptacion"]:
            print(
                f"  {escenario['id']} · {escenario['nombre']}: DADO QUE {escenario['dado_que']}, "
                f"CUANDO {escenario['cuando']}, ENTONCES {escenario['entonces']}"
            )
        for referencia in datos["referencias"].get(requerimiento["id_requerimiento"], []):
            print(f"  Fuente: {referencia}")
    if datos["defectos"]:
        print("\nDefectos de calidad sin corregir (escalados al analista):")
        for defecto in datos["defectos"]:
            print(f"  - {defecto}")
    else:
        print("\nVerificación de calidad (RF-07): sin defectos.")


def resumir(registro: RegistroJsonl, turnos: list[float]) -> None:
    """Imprime la latencia por turno y el consumo por nodo de la sesión."""
    if turnos:
        print(
            f"\nTurnos de diálogo: {len(turnos)} · duración media {statistics.mean(turnos):.1f} s"
            f" · máxima {max(turnos):.1f} s (RNF-01: menos de 15 s)"
        )
    por_nodo = defaultdict(list)
    for llamada in registro.llamadas:
        por_nodo[llamada.nodo].append(llamada)
    for nodo, llamadas in por_nodo.items():
        latencias = [llamada.latencia_ms for llamada in llamadas]
        costo = sum((llamada.costo_usd for llamada in llamadas), Decimal(0))
        entrada = sum(llamada.consumo.entrada for llamada in llamadas)
        cacheada = sum(llamada.consumo.entrada_cacheada for llamada in llamadas)
        salida = sum(llamada.consumo.salida for llamada in llamadas)
        razonamiento = sum(llamada.consumo.razonamiento for llamada in llamadas)
        print(
            f"{nodo:17} {len(llamadas):2} llamadas · latencia media "
            f"{statistics.mean(latencias):6.0f} ms · máx {max(latencias):6} ms · entrada "
            f"{entrada:6} (caché {cacheada}) · salida {salida:6} (razonamiento {razonamiento})"
            f" · USD {costo:.6f}"
        )
    sistema = sum(
        (llamada.costo_usd for llamada in registro.llamadas if llamada.nodo != "cliente_simulado"),
        Decimal(0),
    )
    print(f"Costo del sistema: USD {sistema:.6f} · registrado en {registro.ruta.relative_to(RAIZ)}")


@dataclass
class Guion:
    """Decisiones automáticas para el modo simulado."""

    pausar_tras: int | None = None
    rechazo: str | None = None
    aprobar: bool = False


def conversar(
    app: CompiledStateGraph,
    id_sesion: str,
    avance: Avance,
    simulado: ClienteSimulado | None,
    turnos: list[float],
    guion: Guion,
) -> None:
    """Responde cada pausa del diálogo y decide en N6, hasta salir del alcance del paso 7."""
    respuestas = 0
    while avance.pausa is not None:
        pausa = avance.pausa
        if pausa.datos.get("aviso"):
            print(f"(Aviso: {pausa.datos['aviso']})")
        if pausa.punto == "dialogo":
            for observacion in pausa.datos["observaciones_revisor"]:
                print(f"(Observación del revisor: {observacion})")
            pregunta = pausa.datos["pregunta"]
            print(f"Elicitador> {pregunta}   [{turnos[-1]:.1f} s]" if turnos else pregunta)
            if simulado and guion.pausar_tras is not None and respuestas >= guion.pausar_tras:
                respuesta = SALIR
            elif simulado:
                estado = app.get_state(configuracion_hilo(id_sesion)).values
                respuesta = simulado.responder(estado["conversacion"], pregunta)
                print(f"Cliente> {respuesta}")
            else:
                respuesta = input("Cliente> ").strip()
            respuestas += 1
            if respuesta == SALIR:
                print(f"Sesión en pausa. Reanúdala con --sesion {id_sesion}")
                return
            avance, segundos = medir(lambda r=respuesta: avanzar(app, id_sesion, r))
            turnos.append(segundos)
        elif pausa.punto == "requerimientos":
            mostrar_requerimientos(pausa.datos)
            if simulado:
                if guion.rechazo:
                    decision, observaciones, guion.rechazo = "r", guion.rechazo, None
                elif guion.aprobar:
                    decision, observaciones = "a", None
                else:
                    print(f"\nLa sesión queda en N6. Reanúdala con --sesion {id_sesion}")
                    return
                print(f"\nDecisión del analista: {decision} {observaciones or ''}")
            else:
                decision = input("\n[a]probar, [r]echazar o [s]alir: ").strip().lower()
                observaciones = None
            if decision.startswith("a"):
                revisor = "Analista" if simulado else input("Revisor: ").strip() or "Analista"
                avanzar(app, id_sesion, {"decision": "aprobado", "revisor": revisor})
                print("Requerimientos aprobados; el diseño sigue con el arquitecto simulado.")
                return
            if not decision.startswith("r"):
                print(f"Sesión en pausa. Reanúdala con --sesion {id_sesion}")
                return
            rechazo = {
                "decision": "rechazado",
                "revisor": "Analista" if simulado else input("Revisor: ").strip() or "Analista",
                "observaciones": observaciones or input("Observaciones: ").strip(),
            }
            avance, segundos = medir(lambda r=rechazo: avanzar(app, id_sesion, r))
            turnos.append(segundos)
        else:
            print(f"Pausa en «{pausa.punto}», fuera del alcance de este script.")
            return


def main() -> None:
    """Ejecuta la conversación hasta el punto de control N6."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sesion", help="Reanuda la sesión con este identificador.")
    parser.add_argument(
        "--simulado",
        type=Path,
        help="Caso sintético; un modelo hace de cliente y la sesión se detiene en N6.",
    )
    parser.add_argument("--pausar-tras", type=int, help="Con --simulado, pausa tras N respuestas.")
    parser.add_argument("--rechazar", help="Con --simulado, rechaza una vez en N6 con esto.")
    parser.add_argument("--aprobar", action="store_true", help="Con --simulado, aprueba en N6.")
    argumentos = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format="(aviso) %(message)s")
    guion = Guion(argumentos.pausar_tras, argumentos.rechazar, argumentos.aprobar)

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
    cadena = ConfiguracionBaseDatos().cadena_conexion()
    with psycopg.connect(cadena, autocommit=True) as conexion, abrir_checkpointer() as puntos:
        elicitador = crear_agente_elicitador(conexion, registro, cliente_modelo)
        simulados = ServiciosSimulados(fallos_veredicto=0)
        servicios = Servicios(
            elicitador=elicitador,
            arquitecto=simulados,
            desarrollador=simulados,
            tester=simulados,
        )
        app = construir_grafo(servicios).compile(checkpointer=puntos)

        turnos: list[float] = []
        if argumentos.sesion:
            pausa = pausa_pendiente(app, id_sesion)
            if pausa is None:
                print(f"La sesión {id_sesion} no está detenida en ninguna pausa.")
                return
            avance = Avance(nodos=(), pausa=pausa, fase=None)
            print(f"Sesión {id_sesion} reanudada en «{pausa.punto}».")
        else:
            if caso:
                cliente, proyecto, necesidad = caso.cliente, caso.proyecto, caso.necesidad
            else:
                cliente = input("Cliente: ").strip()
                proyecto = input("Proyecto: ").strip()
                necesidad = input("¿Qué necesita? ").strip()
            print(f"Sesión {id_sesion}\nCliente> {necesidad}")
            avance, segundos = medir(
                lambda: iniciar_sesion(app, cliente, proyecto, necesidad, id_sesion)[1]
            )
            turnos.append(segundos)

        try:
            conversar(app, id_sesion, avance, simulado, turnos, guion)
        except Exception:
            # Con un modelo estocástico, el registro del fallo ayuda a diagnosticarlo.
            estado = app.get_state(configuracion_hilo(id_sesion))
            print(f"\nFallo en {estado.next}. Registro capturado:")
            print(estado.values["conversacion"].registro.model_dump_json(indent=1))
            raise
        finally:
            resumir(registro, turnos)


if __name__ == "__main__":
    main()
