"""Evalúa al desarrollador real sobre diseños fijos, con el veredicto del tester en la v1 (paso 12).

Cada corrida entrega los requerimientos y el diseño fijos de un caso de
`evaluacion/casos/con-recorridos/desarrollo-*.json` (otra carpeta con `--carpeta`).
- El desarrollador real genera la v1 (N10).
- El tester real la dictamina (N11 a N14).
- El ciclo de corrección tiene una sola iteración, así que la sesión se detiene en N17 tras el
  primer veredicto.

Por corrida informa:
- si la verificación de N10 rechazó el primer intento, y con qué problemas;
- si la versión final pasa la verificación estructural;
- la importación y las pruebas en el entorno aislado;
- el veredicto de la v1, sus hallazgos por regla y los casos que el juez no da por cumplidos;
- el costo por nodo y la duración.

Al final resume los primeros intentos rechazados, las v1 aprobadas y las detecciones de CAL-FS-006
(pruebas que simulan) y CAL-MT-010 (nombres privados).

Cada versión queda en JSON en la carpeta de salida (por defecto
data/local/versiones-desarrollador/), con el intento rechazado si lo hubo. Cada llamada al modelo
se agrega a la traza (por defecto docs/mediciones/paso-12-desarrollador.jsonl; otra con
`--traza`), sin el contenido de los mensajes.

Requiere `docker compose up -d --wait`, la imagen del entorno aislado, el corpus ingerido y el
archivo .env. Tiene costo: unos 0,15 USD por corrida.

Uso:
    python scripts/evaluar_desarrollador.py --corridas 2
    python scripts/evaluar_desarrollador.py --casos pagos --corridas 1
"""

import argparse
import json
import logging
import statistics
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import psycopg
from langgraph.checkpoint.memory import InMemorySaver

from multiagente.agentes.desarrollador import servicio as servicio_desarrollador
from multiagente.agentes.desarrollador.generacion import mensaje_intento_rechazado
from multiagente.agentes.desarrollador.servicio import crear_agente_desarrollador
from multiagente.agentes.desarrollador.verificacion import verificar_version
from multiagente.agentes.tester.reglas import cargar_reglas_calidad, estilo_bloqueante
from multiagente.agentes.tester.servicio import crear_agente_tester
from multiagente.core.configuracion import (
    ConfiguracionAzureOpenAI,
    ConfiguracionBaseDatos,
    ConfiguracionOrquestador,
    ConfiguracionTester,
)
from multiagente.interfaces.casos import CasoDesarrollo, cargar_caso_desarrollo
from multiagente.llm.cliente import crear_cliente
from multiagente.llm.traza import RegistroJsonl
from multiagente.orquestador.ejecucion import avanzar, configuracion_hilo, iniciar_sesion
from multiagente.orquestador.estado import ResultadoPrueba
from multiagente.orquestador.grafo import construir_grafo
from multiagente.orquestador.servicios import Servicios
from multiagente.orquestador.simulacion import ArquitectoFijo, ElicitadorFijo, aprobar
from multiagente.persistencia.puntos_control import serializador
from multiagente.rag.embeddings import VectorizadorTEI
from multiagente.sandbox.ejecutor import EntornoAislado

RAIZ = Path(__file__).resolve().parents[1]
CARPETA = RAIZ / "evaluacion" / "casos" / "con-recorridos"
ARCHIVO_MEDICIONES = RAIZ / "docs" / "mediciones" / "paso-12-desarrollador.jsonl"
SALIDA = RAIZ / "data" / "local" / "versiones-desarrollador"
RECHAZO_N10 = "N10: salida rechazada en el intento 1"


RECHAZADOS: list[dict[str, object]] = []
"""Intentos que rechazó la verificación de N10 en la corrida en curso, con sus problemas."""


def _guardar_intento(archivos, problemas):  # noqa: ANN001, ANN202
    """Guarda el intento rechazado antes de armar el mensaje del reintento."""
    RECHAZADOS.append({"archivos": dict(archivos), "problemas": list(problemas)})
    return mensaje_intento_rechazado(archivos, problemas)


# El servicio del desarrollador arma el reintento con esta función: se envuelve para guardar el
# intento rechazado, que el flujo no conserva.
servicio_desarrollador.mensaje_intento_rechazado = _guardar_intento


class Avisos(logging.Handler):
    """Guarda los avisos del invocador: el rechazo del primer intento de N10 y sus problemas."""

    def __init__(self) -> None:
        """Crea el registro vacío."""
        super().__init__(level=logging.WARNING)
        self.mensajes: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        """Guarda el mensaje del aviso."""
        self.mensajes.append(record.getMessage())


@dataclass(frozen=True)
class Corrida:
    """Resultado de una corrida del desarrollador y del tester sobre un caso."""

    caso: str
    numero: int
    primer_intento: tuple[str, ...]
    verificacion: tuple[str, ...]
    errores_importacion: int
    pruebas: dict[str, int]
    veredicto: str
    hallazgos: dict[str, int]
    casos_no_cumplidos: tuple[str, ...]
    costo: dict[str, Decimal]
    segundos: float

    @property
    def primer_intento_rechazado(self) -> bool:
        """Si la verificación de N10 rechazó el primer intento."""
        return bool(self.primer_intento)


def problemas_del_primer_intento(avisos: list[str]) -> tuple[str, ...]:
    """Problemas con que la verificación de N10 rechazó el primer intento, si lo rechazó."""
    for aviso in avisos:
        if aviso.startswith(RECHAZO_N10):
            return tuple(aviso.split("): ", 1)[-1].split("; "))
    return ()


def correr(
    caso: CasoDesarrollo,
    numero: int,
    conexion: psycopg.Connection,
    traza: Path,
    salida: Path,
    avisos: Avisos,
) -> Corrida:
    """Genera y dictamina la v1 de un caso, y guarda la versión con su validación."""
    id_sesion = str(uuid.uuid4())
    registro = RegistroJsonl(traza, sesion=id_sesion)
    cliente = crear_cliente(ConfiguracionAzureOpenAI())
    servicios = Servicios(
        elicitador=ElicitadorFijo(caso.sintesis),
        arquitecto=ArquitectoFijo(caso.diseno),
        desarrollador=crear_agente_desarrollador(
            registro,
            cliente,
            estilo_bloqueante(
                cargar_reglas_calidad(), ConfiguracionTester().umbral_hallazgos_media
            ),
        ),
        tester=crear_agente_tester(
            conexion, registro, cliente, VectorizadorTEI(), EntornoAislado()
        ),
    )
    configuracion = ConfiguracionOrquestador(_env_file=None, max_iteraciones_correccion=1)
    app = construir_grafo(servicios, configuracion).compile(
        checkpointer=InMemorySaver(serde=serializador())
    )
    avisos.mensajes.clear()
    RECHAZADOS.clear()
    inicio = time.perf_counter()
    iniciar_sesion(app, caso.cliente, caso.proyecto, caso.necesidad, id_sesion)
    avanzar(app, id_sesion, aprobar())
    avanzar(app, id_sesion, aprobar())
    segundos = time.perf_counter() - inicio
    estado = app.get_state(configuracion_hilo(id_sesion)).values
    version = estado["codigo"].vigente
    validacion = estado["validacion"]
    ejecucion = validacion.ejecucion
    costo: dict[str, Decimal] = defaultdict(Decimal)
    for llamada in registro.llamadas:
        costo[llamada.nodo] += llamada.costo_usd
    salida.mkdir(parents=True, exist_ok=True)
    (salida / f"{caso.id}-{numero}.json").write_text(
        json.dumps(
            {
                "sesion": id_sesion,
                "version": version.model_dump(mode="json") if version else None,
                "validacion": validacion.model_dump(mode="json"),
                "avisos": list(avisos.mensajes),
                "intentos_rechazados": list(RECHAZADOS),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    requerimientos = estado["requerimientos"]
    return Corrida(
        caso=caso.id,
        numero=numero,
        primer_intento=problemas_del_primer_intento(avisos.mensajes),
        verificacion=tuple(
            verificar_version(version.archivos, caso.especificacion, requerimientos)
            if version
            else ("Sin versión válida",)
        ),
        errores_importacion=len(ejecucion.errores_importacion) if ejecucion else -1,
        pruebas=dict(Counter(p.resultado.value for p in ejecucion.pruebas)) if ejecucion else {},
        veredicto=validacion.veredicto.value if validacion.veredicto else "sin veredicto",
        hallazgos=dict(Counter(hallazgo.regla for hallazgo in validacion.hallazgos)),
        casos_no_cumplidos=tuple(v.id_caso for v in validacion.veredictos if not v.cumple),
        costo=dict(costo),
        segundos=segundos,
    )


def main() -> None:
    """Corre cada caso las veces pedidas e imprime el resumen."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--corridas", type=int, default=1, help="Corridas por caso.")
    parser.add_argument(
        "--casos", nargs="*", default=[], help="Partes del nombre de los casos a correr."
    )
    parser.add_argument("--carpeta", type=Path, default=CARPETA, help="Carpeta de los casos.")
    parser.add_argument("--traza", type=Path, default=ARCHIVO_MEDICIONES, help="Traza JSONL.")
    parser.add_argument("--salida", type=Path, default=SALIDA, help="Carpeta de las versiones.")
    argumentos = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format="(aviso) %(message)s")
    avisos = Avisos()
    logging.getLogger("multiagente.llm.invocador").addHandler(avisos)

    archivos = sorted(argumentos.carpeta.glob("desarrollo-*.json"))
    if argumentos.casos:
        archivos = [a for a in archivos if any(parte in a.stem for parte in argumentos.casos)]
    corridas: list[Corrida] = []
    cadena = ConfiguracionBaseDatos().cadena_conexion()
    with psycopg.connect(cadena, autocommit=True) as conexion:
        for archivo in archivos:
            caso = cargar_caso_desarrollo(archivo)
            for numero in range(1, argumentos.corridas + 1):
                corrida = correr(
                    caso, numero, conexion, argumentos.traza.resolve(), argumentos.salida, avisos
                )
                corridas.append(corrida)
                costo = sum(corrida.costo.values(), Decimal(0))
                print(
                    f"{corrida.caso} #{numero}: primer intento "
                    f"{'rechazado' if corrida.primer_intento_rechazado else 'aceptado'} · "
                    f"verificación {'ok' if not corrida.verificacion else 'con problemas'} · "
                    f"importación {'ok' if corrida.errores_importacion == 0 else 'con errores'} · "
                    f"pruebas {corrida.pruebas} · v1 {corrida.veredicto} · hallazgos "
                    f"{corrida.hallazgos} · casos no cumplidos "
                    f"{list(corrida.casos_no_cumplidos)} · "
                    f"USD {costo:.4f} "
                    f"({', '.join(f'{n} {c:.4f}' for n, c in sorted(corrida.costo.items()))}) · "
                    f"{corrida.segundos:.0f} s",
                    flush=True,
                )
                for problema in corrida.primer_intento:
                    print(f"    primer intento: {problema[:300]}")
                for problema in corrida.verificacion:
                    print(f"    verificación: {problema[:300]}")
    if not corridas:
        print("No hay casos que correr.")
        return
    rechazados = sum(c.primer_intento_rechazado for c in corridas)
    aprobadas = sum(c.veredicto == "aprobado" for c in corridas)
    simuladas = sum(c.hallazgos.get("CAL-FS-006", 0) for c in corridas)
    privados = sum(c.hallazgos.get("CAL-MT-010", 0) for c in corridas)
    fallidas = sum(c.pruebas.get(ResultadoPrueba.FALLO.value, 0) for c in corridas)
    costo = sum((sum(c.costo.values(), Decimal(0)) for c in corridas), Decimal(0))
    print(
        f"\nPrimeros intentos rechazados: {rechazados} de {len(corridas)} · v1 aprobadas: "
        f"{aprobadas} de {len(corridas)} · CAL-FS-006: {simuladas} · CAL-MT-010: {privados} · "
        f"pruebas fallidas: {fallidas} · costo USD {costo:.4f} (media "
        f"{costo / len(corridas):.4f}) · duración media "
        f"{statistics.mean(c.segundos for c in corridas):.0f} s"
    )
    print(f"Traza: {argumentos.traza} · versiones: {argumentos.salida}")


if __name__ == "__main__":
    main()
