"""Genera un módulo con el agente desarrollador real a partir de un caso de desarrollo (paso 9).

Los requerimientos y la especificación salen de un caso de `evaluacion/casos/desarrollo-*.json`.
Un elicitador y un arquitecto fijos los entregan, y el analista y el arquitecto humano los
aprueban sin conversar. El desarrollador usa Azure OpenAI en N10; el tester es simulado.

En la aprobación final (N17), cada versión se revisa así:
- se verifica su estructura contra la especificación;
- se importan sus módulos y se corren sus pruebas en el entorno aislado;
- se analiza su estilo con Ruff, solo para informar.

Un rechazo con observaciones vuelve a N10 y ejercita la corrección (RF-19). Cada llamada al
modelo se agrega a docs/mediciones/paso-09-desarrollador.jsonl, sin el contenido de los
mensajes. Requiere Docker con la imagen del entorno aislado y el archivo .env. Tiene costo.

Uso:
    python scripts/generar_modulo.py --caso evaluacion/casos/desarrollo-avaluo.json
    python scripts/generar_modulo.py --caso CASO --rechazar "…" --aprobar --salida DIR
"""

import argparse
import logging
import statistics
import time
import uuid
from collections import Counter
from decimal import Decimal
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver

from multiagente.agentes.desarrollador.servicio import crear_agente_desarrollador
from multiagente.agentes.desarrollador.verificacion import verificar_version
from multiagente.core.configuracion import ConfiguracionAzureOpenAI
from multiagente.core.estilo import hallazgos_de_estilo
from multiagente.interfaces.casos import CasoDesarrollo, cargar_caso_desarrollo
from multiagente.llm.cliente import crear_cliente
from multiagente.llm.traza import RegistroJsonl
from multiagente.orquestador.ejecucion import avanzar, configuracion_hilo, iniciar_sesion
from multiagente.orquestador.estado import Requerimientos, VersionCodigo
from multiagente.orquestador.grafo import construir_grafo
from multiagente.orquestador.servicios import Servicios
from multiagente.orquestador.simulacion import (
    ArquitectoFijo,
    ElicitadorFijo,
    ServiciosSimulados,
    aprobar,
    rechazar,
)
from multiagente.persistencia.puntos_control import serializador
from multiagente.sandbox.ejecutor import EntornoAislado

RAIZ = Path(__file__).resolve().parents[1]
ARCHIVO_MEDICIONES = RAIZ / "docs" / "mediciones" / "paso-09-desarrollador.jsonl"


def revisar(
    version: VersionCodigo,
    caso: CasoDesarrollo,
    requerimientos: Requerimientos,
    entorno: EntornoAislado,
) -> None:
    """Imprime lo que la persona revisa en N17: verificación, importación, pruebas y estilo."""
    print(f"\n=== Punto de control N17: versión {version.numero} del módulo ===\n")
    if version.defectos_atendidos:
        print("Defectos atendidos:")
        for defecto in version.defectos_atendidos:
            print(f"  - {defecto}")
    for ruta, contenido in sorted(version.archivos.items()):
        print(f"  {ruta:55} {contenido.count(chr(10)):4} líneas")

    problemas = verificar_version(version.archivos, caso.especificacion, requerimientos)
    print(f"\nVerificación estructural (RF-15, RF-17, RF-18): {len(problemas)} problemas")
    for problema in problemas:
        print(f"  - {problema}")

    modulos = [modulo.nombre for modulo in caso.especificacion.modulos]
    importacion = entorno.importar(version.archivos, modulos)
    print(
        f"Importación en el entorno aislado: {len(modulos) - len(importacion.errores)} de "
        f"{len(modulos)} módulos ({importacion.ejecucion.duracion_ms} ms)"
    )
    for modulo, traza in importacion.errores.items():
        print(f"  - {modulo}: {traza.strip().splitlines()[-1]}")

    pruebas = entorno.probar(version.archivos, tiempo_limite_s=120)
    resultados = dict(Counter(prueba.resultado for prueba in pruebas.pruebas))
    print(
        f"Pruebas en el entorno aislado (informativo): {resultados} · "
        f"{len(pruebas.errores_recoleccion)} errores de recolección"
    )

    hallazgos = hallazgos_de_estilo(version.archivos)
    por_codigo = Counter(hallazgo.codigo for hallazgo in hallazgos)
    print(f"Estilo con Ruff (informativo): {len(hallazgos)} hallazgos {dict(por_codigo)}")


def guardar(version: VersionCodigo, carpeta: Path) -> None:
    """Escribe los archivos de la versión en `carpeta/v<n>/` para revisarlos a mano."""
    destino = carpeta / f"v{version.numero}"
    for ruta, contenido in version.archivos.items():
        archivo = destino / ruta
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text(contenido, encoding="utf-8")
    print(f"Archivos escritos en {destino}")


def resumir(registro: RegistroJsonl, segundos: float) -> None:
    """Imprime el consumo de N10 y el tiempo total."""
    llamadas = registro.llamadas
    print(f"\nTiempo total: {segundos:.1f} s · {len(llamadas)} llamadas a N10")
    for llamada in llamadas:
        consumo = llamada.consumo
        print(
            f"  {llamada.modelo} · {llamada.latencia_ms / 1000:6.1f} s · entrada {consumo.entrada}"
            f" (caché {consumo.entrada_cacheada}, escrita {consumo.entrada_escrita_cache}) · "
            f"salida {consumo.salida} (razonamiento {consumo.razonamiento}) · "
            f"USD {llamada.costo_usd:.4f}{' · ' + llamada.error if llamada.error else ''}"
        )
    if llamadas:
        latencias = [llamada.latencia_ms / 1000 for llamada in llamadas]
        print(f"  Latencia media {statistics.mean(latencias):.1f} s, máxima {max(latencias):.1f} s")
    costo = sum((llamada.costo_usd for llamada in llamadas), Decimal(0))
    print(f"Costo total: USD {costo:.4f} · {registro.ruta.relative_to(RAIZ)}")


def main() -> None:
    """Genera el módulo y lo lleva hasta la decisión de la persona en N17."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--caso", type=Path, required=True, help="Caso de desarrollo.")
    parser.add_argument("--rechazar", help="Rechaza una vez en N17 con esta observación.")
    parser.add_argument("--aprobar", action="store_true", help="Aprueba en N17 sin preguntar.")
    parser.add_argument("--salida", type=Path, help="Carpeta donde escribir cada versión.")
    argumentos = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format="(aviso) %(message)s")

    caso = cargar_caso_desarrollo(argumentos.caso)
    id_sesion = str(uuid.uuid4())
    registro = RegistroJsonl(ARCHIVO_MEDICIONES, sesion=id_sesion)
    entorno = EntornoAislado()
    simulados = ServiciosSimulados(fallos_veredicto=0)
    servicios = Servicios(
        elicitador=ElicitadorFijo(caso.sintesis),
        arquitecto=ArquitectoFijo(caso.diseno),
        desarrollador=crear_agente_desarrollador(
            registro, crear_cliente(ConfiguracionAzureOpenAI())
        ),
        tester=simulados,
    )
    app = construir_grafo(servicios).compile(checkpointer=InMemorySaver(serde=serializador()))
    especificacion = caso.especificacion
    print(f"Sesión {id_sesion} · caso {caso.id}: {caso.titulo}")
    print(
        f"{especificacion.id_especificacion} v{especificacion.version} · "
        f"{especificacion.arquitectura_base} · {len(especificacion.modulos)} módulos"
    )

    inicio = time.perf_counter()
    rechazo = argumentos.rechazar
    iniciar_sesion(app, caso.cliente, caso.proyecto, caso.necesidad, id_sesion)
    avanzar(app, id_sesion, aprobar("Analista"))
    avance = avanzar(app, id_sesion, aprobar("Arquitecto"))
    while avance.pausa is not None and avance.pausa.punto == "final":
        estado = app.get_state(configuracion_hilo(id_sesion)).values
        if avance.pausa.datos["escalado"]:
            print(f"\nLa sesión escaló sin módulo aprobado:\n{estado['validacion'].reporte}")
            break
        version = estado["codigo"].vigente
        revisar(version, caso, estado["requerimientos"], entorno)
        if argumentos.salida:
            guardar(version, argumentos.salida)
        if rechazo:
            decision, observaciones, rechazo = "r", rechazo, None
            print(f"\nDecisión de la persona: rechazar · {observaciones}")
        elif argumentos.aprobar:
            decision, observaciones = "a", None
            print("\nDecisión de la persona: aprobar")
        else:
            decision = input("\n[a]probar, [r]echazar o [s]alir: ").strip().lower()
            observaciones = input("Observaciones: ").strip() if decision.startswith("r") else None
        if decision.startswith("a"):
            avance = avanzar(app, id_sesion, aprobar("Revisor"))
            print(f"Módulo validado: fase {avance.fase}.")
            break
        if decision.startswith("r") and observaciones:
            avance = avanzar(app, id_sesion, rechazar(observaciones, "Revisor"))
            continue
        print(f"Sesión en pausa en N17 ({id_sesion}).")
        break
    resumir(registro, time.perf_counter() - inicio)


if __name__ == "__main__":
    main()
