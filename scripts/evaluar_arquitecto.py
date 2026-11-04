"""Evalúa al arquitecto real sobre los casos de diseño, con varias corridas por caso (paso 12).

Cada corrida entrega los requerimientos aprobados de un caso de `evaluacion/casos/diseno-*.json`
con un elicitador fijo, y el arquitecto real diseña hasta la aprobación humana de N9: BGE-M3 en N7
y Azure OpenAI en N8. Los demás agentes son simulados.

Por corrida informa:
- la arquitectura elegida y si está entre las candidatas de arq-003;
- los módulos, las interfaces y los recorridos;
- los intentos de selección y de parametrización;
- los diseños, de modo que más de uno indica que N9 devolvió el primero, y los errores con que
  N9 devolvió cada uno;
- los errores con que llegó a la aprobación humana;
- los recorridos que solo observan lo que devuelve la interfaz del «cuando»;
- el costo y la duración.

Al final resume cuántas corridas llegaron a N9 sin errores en el primer diseño.

Cada diseño queda en JSON en la carpeta de salida (por defecto
data/local/disenos-arquitecto/) para revisarlo. Cada llamada al modelo se agrega a la traza (por
defecto docs/mediciones/paso-12-arquitecto.jsonl; otra con `--traza`), sin el contenido de los
mensajes.

Requiere `docker compose up -d --wait`, el corpus ingerido y el archivo .env. Tiene costo: unos
0,10 USD por corrida.

Uso:
    python scripts/evaluar_arquitecto.py --corridas 3
    python scripts/evaluar_arquitecto.py --casos pagos --corridas 1
"""

import argparse
import json
import logging
import statistics
import time
import uuid
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import psycopg
from langgraph.checkpoint.memory import InMemorySaver

from multiagente.agentes.arquitecto.servicio import crear_agente_arquitecto
from multiagente.core.configuracion import (
    ConfiguracionAzureOpenAI,
    ConfiguracionBaseDatos,
    ConfiguracionOrquestador,
)
from multiagente.interfaces.casos import CasoDiseno, cargar_caso_diseno
from multiagente.llm.cliente import crear_cliente
from multiagente.llm.traza import RegistroJsonl
from multiagente.orquestador.ejecucion import avanzar, configuracion_hilo, iniciar_sesion
from multiagente.orquestador.grafo import construir_grafo
from multiagente.orquestador.servicios import Servicios
from multiagente.orquestador.simulacion import ElicitadorFijo, ServiciosSimulados, aprobar
from multiagente.persistencia.puntos_control import serializador

RAIZ = Path(__file__).resolve().parents[1]
ARCHIVO_MEDICIONES = RAIZ / "docs" / "mediciones" / "paso-12-arquitecto.jsonl"
SALIDA = RAIZ / "data" / "local" / "disenos-arquitecto"


@dataclass(frozen=True)
class Corrida:
    """Resultado de una corrida del arquitecto sobre un caso."""

    caso: str
    numero: int
    elegida: str
    candidata: bool
    modulos: int
    interfaces: int
    recorridos: int
    escenarios: int
    selecciones: int
    parametrizaciones: int
    disenos: int
    devoluciones: tuple[tuple[str, ...], ...]
    errores: tuple[str, ...]
    solo_resultado: int
    costo: Decimal
    segundos: float

    @property
    def primer_diseno_valido(self) -> bool:
        """Si llegó a N9 sin errores con el primer diseño."""
        return not self.errores and self.disenos == 1 and self.candidata


def disenar(
    caso: CasoDiseno, numero: int, conexion: psycopg.Connection, traza: Path, salida: Path
) -> Corrida:
    """Corre el arquitecto real sobre un caso hasta la pausa de N9 y guarda el diseño."""
    id_sesion = str(uuid.uuid4())
    registro = RegistroJsonl(traza, sesion=id_sesion)
    simulados = ServiciosSimulados(fallos_veredicto=0)
    servicios = Servicios(
        elicitador=ElicitadorFijo(caso.sintesis),
        arquitecto=crear_agente_arquitecto(
            conexion, registro, crear_cliente(ConfiguracionAzureOpenAI())
        ),
        desarrollador=simulados,
        tester=simulados,
    )
    app = construir_grafo(servicios, ConfiguracionOrquestador(_env_file=None)).compile(
        checkpointer=InMemorySaver(serde=serializador())
    )
    inicio = time.perf_counter()
    iniciar_sesion(app, caso.cliente, caso.proyecto, caso.necesidad, id_sesion)
    avance = avanzar(app, id_sesion, aprobar())
    segundos = time.perf_counter() - inicio
    configuracion = configuracion_hilo(id_sesion)
    estado = app.get_state(configuracion).values
    arquitectura = estado["arquitectura"]
    # Errores con que N9 devolvió cada diseño a N8, en orden, desde el historial de la sesión.
    devoluciones: list[tuple[str, ...]] = []
    for instantanea in reversed(list(app.get_state_history(configuracion))):
        previa = instantanea.values.get("arquitectura")
        errores_n9 = previa.errores_validacion if previa is not None else ()
        if errores_n9 and errores_n9 not in devoluciones:
            devoluciones.append(errores_n9)
    especificacion = arquitectura.especificacion
    errores = tuple(avance.pausa.datos["errores"]) if avance.pausa else ("Sin pausa en N9",)
    escenarios = sum(len(r.criterios_aceptacion) for r in estado["requerimientos"].requerimientos)
    prompts = [llamada.prompt for llamada in registro.llamadas]
    salida.mkdir(parents=True, exist_ok=True)
    (salida / f"{caso.id}-{numero}.json").write_text(
        json.dumps(
            {
                "sesion": id_sesion,
                "registro_decision": arquitectura.registro_decision,
                "especificacion": especificacion.model_dump(mode="json")
                if especificacion
                else None,
                "recorridos": [r.model_dump(mode="json") for r in arquitectura.recorridos],
                "capacidades_no_cubiertas": list(arquitectura.capacidades_no_cubiertas),
                "devoluciones": [list(d) for d in devoluciones],
                "errores": list(errores),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return Corrida(
        caso=caso.id,
        numero=numero,
        elegida=especificacion.arquitectura_base if especificacion else "—",
        candidata=bool(especificacion) and especificacion.arquitectura_base in caso.candidatas,
        modulos=len(especificacion.modulos) if especificacion else 0,
        interfaces=sum(len(m.interfaces_publicas) for m in especificacion.modulos)
        if especificacion
        else 0,
        recorridos=len(arquitectura.recorridos),
        escenarios=escenarios,
        selecciones=sum("seleccion" in prompt for prompt in prompts),
        parametrizaciones=sum("parametrizacion" in prompt for prompt in prompts),
        disenos=arquitectura.disenos,
        devoluciones=tuple(devoluciones),
        errores=errores,
        solo_resultado=sum(set(r.observar) == {r.ejecutar} for r in arquitectura.recorridos),
        costo=registro.costo_total_usd,
        segundos=segundos,
    )


def main() -> None:
    """Corre cada caso las veces pedidas e imprime el resumen."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--corridas", type=int, default=1, help="Corridas por caso.")
    parser.add_argument(
        "--casos", nargs="*", default=[], help="Partes del nombre de los casos a correr."
    )
    parser.add_argument("--traza", type=Path, default=ARCHIVO_MEDICIONES, help="Traza JSONL.")
    parser.add_argument("--salida", type=Path, default=SALIDA, help="Carpeta de los diseños.")
    argumentos = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format="(aviso) %(message)s")

    archivos = sorted((RAIZ / "evaluacion" / "casos").glob("diseno-*.json"))
    if argumentos.casos:
        archivos = [a for a in archivos if any(parte in a.stem for parte in argumentos.casos)]
    corridas: list[Corrida] = []
    cadena = ConfiguracionBaseDatos().cadena_conexion()
    with psycopg.connect(cadena, autocommit=True) as conexion:
        for archivo in archivos:
            caso = cargar_caso_diseno(archivo)
            for numero in range(1, argumentos.corridas + 1):
                corrida = disenar(
                    caso, numero, conexion, argumentos.traza.resolve(), argumentos.salida
                )
                corridas.append(corrida)
                print(
                    f"{corrida.caso} #{numero}: {corrida.elegida}"
                    f"{'' if corrida.candidata else ' (fuera de las candidatas)'} · "
                    f"{corrida.modulos} módulos · {corrida.interfaces} interfaces · "
                    f"{corrida.recorridos}/{corrida.escenarios} recorridos "
                    f"({corrida.solo_resultado} solo con el resultado) · "
                    f"selección {corrida.selecciones} · parametrización "
                    f"{corrida.parametrizaciones} · diseños {corrida.disenos} · "
                    f"{len(corrida.errores)} errores · USD {corrida.costo:.4f} · "
                    f"{corrida.segundos:.0f} s",
                    flush=True,
                )
                for numero_devolucion, devolucion in enumerate(corrida.devoluciones, 1):
                    print(f"    N9 devolvió el diseño {numero_devolucion}:")
                    for error in devolucion:
                        print(f"      - {error}")
                for error in corrida.errores:
                    print(f"    - {error}")
    if not corridas:
        print("No hay casos que correr.")
        return
    validas = sum(corrida.primer_diseno_valido for corrida in corridas)
    reintentos = sum(c.parametrizaciones > c.disenos for c in corridas)
    costo = sum((c.costo for c in corridas), Decimal(0))
    print(
        f"\nPrimer diseño válido: {validas} de {len(corridas)} · con reintento de la "
        f"parametrización: {reintentos} · costo USD {costo:.4f} (media "
        f"{costo / len(corridas):.4f}) · duración media "
        f"{statistics.mean(c.segundos for c in corridas):.0f} s"
    )
    print(f"Traza: {argumentos.traza} · diseños: {argumentos.salida}")


if __name__ == "__main__":
    main()
