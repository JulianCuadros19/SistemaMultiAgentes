"""Diseña con el agente arquitecto real a partir de requerimientos aprobados (paso 8).

Los requerimientos salen de un caso de `evaluacion/casos/diseno-*.json`: un elicitador fijo los
entrega y el analista los aprueba en N6 sin conversar. El arquitecto usa BGE-M3 en N7 y Azure
OpenAI en N8; N9 valida la especificación con el Anexo B y la persona decide. Los demás agentes
son simulados. Cada llamada al modelo se agrega a docs/mediciones/paso-08-arquitecto.jsonl, sin
el contenido de los mensajes. Requiere `docker compose up -d --wait`, el corpus ingerido y el
archivo .env. Tiene costo.

Con `--exportar`, el diseño aprobado se guarda como caso de desarrollo para el paso 9.

Uso:
    python scripts/disenar_arquitectura.py --requerimientos evaluacion/casos/diseno-avaluo.json
    python scripts/disenar_arquitectura.py --requerimientos CASO --rechazar "…" --aprobar
    python scripts/disenar_arquitectura.py --requerimientos CASO --aprobar \
        --exportar evaluacion/casos/desarrollo-avaluo.json
"""

import argparse
import logging
import statistics
import time
import uuid
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

import psycopg

from multiagente.agentes.arquitecto.servicio import crear_agente_arquitecto
from multiagente.core.configuracion import ConfiguracionAzureOpenAI, ConfiguracionBaseDatos
from multiagente.interfaces.casos import cargar_caso_diseno, exportar_caso_desarrollo
from multiagente.interfaces.consola import mostrar_especificacion
from multiagente.llm.cliente import crear_cliente
from multiagente.llm.traza import RegistroJsonl
from multiagente.orquestador.ejecucion import avanzar, configuracion_hilo, iniciar_sesion
from multiagente.orquestador.grafo import construir_grafo
from multiagente.orquestador.servicios import Diseno, Servicios
from multiagente.orquestador.simulacion import ElicitadorFijo, ServiciosSimulados
from multiagente.persistencia.puntos_control import abrir_checkpointer

RAIZ = Path(__file__).resolve().parents[1]
ARCHIVO_MEDICIONES = RAIZ / "docs" / "mediciones" / "paso-08-arquitecto.jsonl"


def resumir(registro: RegistroJsonl, segundos: float) -> None:
    """Imprime el consumo por nodo y el tiempo total del diseño."""
    por_nodo = defaultdict(list)
    for llamada in registro.llamadas:
        por_nodo[(llamada.nodo, llamada.prompt)].append(llamada)
    print(f"\nTiempo total: {segundos:.1f} s")
    for (nodo, prompt), llamadas in por_nodo.items():
        latencias = [llamada.latencia_ms for llamada in llamadas]
        costo = sum((llamada.costo_usd for llamada in llamadas), Decimal(0))
        salida = sum(llamada.consumo.salida for llamada in llamadas)
        razonamiento = sum(llamada.consumo.razonamiento for llamada in llamadas)
        print(
            f"{nodo} {prompt:34} {len(llamadas)} llamadas · media "
            f"{statistics.mean(latencias) / 1000:5.1f} s · salida {salida:6} (razonamiento "
            f"{razonamiento}) · USD {costo:.5f}"
        )
    print(f"Costo total: USD {registro.costo_total_usd:.5f} · {registro.ruta.relative_to(RAIZ)}")


def main() -> None:
    """Ejecuta el diseño hasta la decisión de la persona en N9."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--requerimientos", type=Path, required=True, help="Caso de diseño.")
    parser.add_argument("--rechazar", help="Rechaza una vez en N9 con esta observación.")
    parser.add_argument("--aprobar", action="store_true", help="Aprueba en N9 sin preguntar.")
    parser.add_argument(
        "--exportar", type=Path, help="Guarda el diseño aprobado como caso de desarrollo."
    )
    argumentos = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format="(aviso) %(message)s")

    caso = cargar_caso_diseno(argumentos.requerimientos)
    id_sesion = str(uuid.uuid4())
    registro = RegistroJsonl(ARCHIVO_MEDICIONES, sesion=id_sesion)
    rechazo = argumentos.rechazar
    cadena = ConfiguracionBaseDatos().cadena_conexion()
    with psycopg.connect(cadena, autocommit=True) as conexion, abrir_checkpointer() as puntos:
        simulados = ServiciosSimulados(fallos_veredicto=0)
        servicios = Servicios(
            elicitador=ElicitadorFijo(caso.sintesis),
            arquitecto=crear_agente_arquitecto(
                conexion, registro, crear_cliente(ConfiguracionAzureOpenAI())
            ),
            desarrollador=simulados,
            tester=simulados,
        )
        app = construir_grafo(servicios).compile(checkpointer=puntos)
        print(f"Sesión {id_sesion} · caso {caso.id}: {caso.titulo}")
        print(f"Candidatas según arq-003: {caso.candidatas} ({caso.criterio})")
        inicio = time.perf_counter()
        _, avance = iniciar_sesion(app, caso.cliente, caso.proyecto, caso.necesidad, id_sesion)
        avance = avanzar(app, id_sesion, {"decision": "aprobado", "revisor": "Analista"})
        while avance.pausa is not None and avance.pausa.punto == "especificacion":
            if avance.pausa.datos.get("aviso"):
                print(f"(Aviso: {avance.pausa.datos['aviso']})")
            mostrar_especificacion(avance.pausa.datos)
            if rechazo:
                decision, observaciones, rechazo = "r", rechazo, None
                print(f"\nDecisión del arquitecto humano: rechazar · {observaciones}")
            elif argumentos.aprobar:
                decision, observaciones = "a", None
                print("\nDecisión del arquitecto humano: aprobar")
            else:
                decision = input("\n[a]probar, [r]echazar o [s]alir: ").strip().lower()
                observaciones = (
                    input("Observaciones: ").strip() if decision.startswith("r") else None
                )
            if decision.startswith("a"):
                avance = avanzar(app, id_sesion, {"decision": "aprobado", "revisor": "Arquitecto"})
                if avance.pausa is not None and avance.pausa.punto == "especificacion":
                    continue
                print("Especificación aprobada; la generación sigue con el desarrollador simulado.")
                if argumentos.exportar:
                    arquitectura = app.get_state(configuracion_hilo(id_sesion)).values[
                        "arquitectura"
                    ]
                    diseno = Diseno(
                        registro_decision=arquitectura.registro_decision,
                        especificacion=arquitectura.especificacion,
                    )
                    exportado = exportar_caso_desarrollo(caso, diseno, argumentos.exportar)
                    print(f"Caso de desarrollo guardado: {argumentos.exportar} ({exportado.id})")
                break
            if decision.startswith("r"):
                avance = avanzar(
                    app,
                    id_sesion,
                    {
                        "decision": "rechazado",
                        "revisor": "Arquitecto",
                        "observaciones": observaciones,
                    },
                )
                continue
            print(f"Sesión en pausa en N9 ({id_sesion}).")
            break
        resumir(registro, time.perf_counter() - inicio)


if __name__ == "__main__":
    main()
