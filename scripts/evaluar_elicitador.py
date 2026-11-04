"""Evalúa al elicitador real sobre casos sintéticos, hasta la primera pausa de N6 (paso 12).

Cada corrida abre una sesión con la necesidad de un caso de `evaluacion/casos/ampliada/` (otra
carpeta con `--carpeta`). Un modelo hace de cliente con lo que sabe el caso, y el elicitador real
conversa: BGE-M3 en N2 y Azure OpenAI en N3 y N5. Los demás agentes son simulados, y la sesión
se detiene en N6.

Por corrida informa:
- los turnos del cliente, si la sesión llegó al límite y si el cliente confirmó el resumen;
- las preguntas por casos límite, con su categoría, y los casos que el cliente definió;
- los requerimientos, sus escenarios y los defectos de calidad con que llegaron a N6;
- en los casos con reglas ocultas, cuáles quedaron en el registro y cuáles en los requerimientos,
  según los términos de cada regla y según un juez semántico (`evaluacion/juez_reglas_ocultas.md`),
  que no es parte del sistema;
- el costo del sistema y el del cliente simulado.

Al final resume los turnos, los resúmenes confirmados, las sesiones en el límite y las reglas
ocultas capturadas por caso. Con `--rejuzgar CARPETA`, en lugar de conversar, vuelve a juzgar las
sesiones guardadas en esa carpeta.

Cada corrida queda en JSON en la carpeta de salida (por defecto data/local/elicitaciones/), con la
conversación, el registro y los requerimientos. Cada llamada al modelo se agrega a la traza (por
defecto docs/mediciones/paso-12-elicitacion-3.jsonl; otra con `--traza`), sin el contenido de los
mensajes.

Requiere `docker compose up -d --wait`, el corpus ingerido y el archivo .env. Tiene costo: unos
0,10 USD por corrida, con el cliente simulado.

Uso:
    python scripts/evaluar_elicitador.py
    python scripts/evaluar_elicitador.py --carpeta evaluacion/casos/casos-limite --corridas 3
"""

import argparse
import json
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Literal

import psycopg
from langgraph.checkpoint.memory import InMemorySaver
from openai import OpenAI
from pydantic import BaseModel, ConfigDict

from multiagente.agentes.elicitador.calidad import normalizar
from multiagente.agentes.elicitador.servicio import crear_agente_elicitador
from multiagente.core.configuracion import (
    ConfiguracionAzureOpenAI,
    ConfiguracionBaseDatos,
    ConfiguracionModelos,
    ConfiguracionOrquestador,
)
from multiagente.core.esquemas.requerimiento import RequerimientoFormal
from multiagente.interfaces.cliente_simulado import (
    RAIZ_EVALUACION,
    CasoElicitacion,
    ClienteSimulado,
    cargar_caso,
)
from multiagente.llm.cliente import crear_cliente
from multiagente.llm.invocador import InvocadorNodo, ParametrosNodo
from multiagente.llm.prompts import leer_prompt
from multiagente.llm.traza import RegistradorLlamadas, RegistroJsonl
from multiagente.orquestador.ejecucion import avanzar, configuracion_hilo, iniciar_sesion
from multiagente.orquestador.estado import RegistroCaptura
from multiagente.orquestador.grafo import construir_grafo
from multiagente.orquestador.servicios import Servicios
from multiagente.orquestador.simulacion import ServiciosSimulados
from multiagente.persistencia.puntos_control import serializador

RAIZ = Path(__file__).resolve().parents[1]
CARPETA = RAIZ / "evaluacion" / "casos" / "ampliada"
ARCHIVO_MEDICIONES = RAIZ / "docs" / "mediciones" / "paso-12-elicitacion-3.jsonl"
SALIDA = RAIZ / "data" / "local" / "elicitaciones"
CLIENTE = "cliente_simulado"
JUEZ = "juez_evaluacion"


class JuicioRegla(BaseModel):
    """Juicio sobre una regla oculta del caso."""

    model_config = ConfigDict(extra="forbid")

    id: str
    en_registro: Literal["si", "parcial", "no"]
    en_requerimientos: Literal["si", "parcial", "no"]
    evidencia: str


class SalidaJuez(BaseModel):
    """Salida del juez de la evaluación: un juicio por regla oculta."""

    model_config = ConfigDict(extra="forbid")

    reglas: list[JuicioRegla]


def juzgar(
    cliente: OpenAI,
    registrador: RegistradorLlamadas,
    caso: CasoElicitacion,
    registro: dict,
    requerimientos: list[dict],
) -> list[JuicioRegla]:
    """Pide al juez de la evaluación si la sesión recogió cada regla oculta del caso."""
    invocador = InvocadorNodo(
        cliente,
        ParametrosNodo(
            nodo=JUEZ,
            despliegue=ConfiguracionModelos().despliegue_cliente_simulado,
            esfuerzo="low",
            max_tokens_salida=6000,
        ),
        leer_prompt(RAIZ_EVALUACION / "juez_reglas_ocultas.md"),
        registrador,
    )
    datos = {
        "reglas": [{"id": r.id, "descripcion": r.descripcion} for r in caso.reglas_ocultas],
        "registro": {
            clave: registro.get(clave, [])
            for clave in ("reglas_negocio", "excepciones", "casos_limite")
        },
        "requerimientos": [
            {
                "regla_negocio": r["descripcion"]["regla_negocio"],
                "escenarios": [
                    f"{e.get('nombre') or ''}: DADO QUE {e['dado_que']} CUANDO {e['cuando']} "
                    f"ENTONCES {e['entonces']}"
                    for e in r["criterios_aceptacion"]
                ],
            }
            for r in requerimientos
        ],
    }
    mensaje = json.dumps(datos, ensure_ascii=False)
    return invocador.invocar([{"role": "user", "content": mensaje}], SalidaJuez).reglas


def recogidas(juicios: list[JuicioRegla], campo: str) -> tuple[str, ...]:
    """Reglas que el juez dio por recogidas del todo en el campo indicado."""
    return tuple(juicio.id for juicio in juicios if getattr(juicio, campo) == "si")


@dataclass(frozen=True)
class Corrida:
    """Resultado de una elicitación sobre un caso, hasta la primera pausa de N6."""

    caso: str
    numero: int
    turnos: int
    en_limite: bool
    confirmado: bool
    categorias: tuple[str, ...]
    casos_limite: int
    requerimientos: int
    escenarios: int
    defectos: int
    ocultas_registro: tuple[str, ...]
    ocultas_requerimientos: tuple[str, ...]
    juez_registro: tuple[str, ...]
    juez_requerimientos: tuple[str, ...]
    costo_sistema: Decimal
    costo_cliente: Decimal
    segundos: float


def _contiene(texto: str, terminos: tuple[str, ...]) -> bool:
    normalizado = normalizar(texto)
    return all(normalizar(termino) in normalizado for termino in terminos)


def texto_del_registro(registro: RegistroCaptura) -> str:
    """Reglas, casos de error y casos especiales del registro, en un solo texto."""
    return " ".join((*registro.reglas_negocio, *registro.excepciones, *registro.casos_limite))


def texto_del_requerimiento(requerimiento: RequerimientoFormal) -> str:
    """Precondición, regla y escenarios de un requerimiento, en un solo texto."""
    descripcion = requerimiento.descripcion
    escenarios = " ".join(
        f"{e.nombre or ''} {e.dado_que} {e.cuando} {e.entonces}"
        for e in requerimiento.criterios_aceptacion
    )
    return f"{descripcion.precondicion} {descripcion.regla_negocio} {escenarios}"


def elicitar(
    caso: CasoElicitacion,
    numero: int,
    conexion: psycopg.Connection,
    traza: Path,
    salida: Path,
) -> Corrida:
    """Conversa con el cliente simulado hasta la primera pausa de N6 y guarda la sesión."""
    id_sesion = str(uuid.uuid4())
    registro_llamadas = RegistroJsonl(traza, sesion=id_sesion)
    cliente_modelo = crear_cliente(ConfiguracionAzureOpenAI())
    simulado = ClienteSimulado(
        cliente_modelo, ConfiguracionModelos().despliegue_cliente_simulado, caso, registro_llamadas
    )
    simulados = ServiciosSimulados(fallos_veredicto=0)
    servicios = Servicios(
        elicitador=crear_agente_elicitador(conexion, registro_llamadas, cliente_modelo),
        arquitecto=simulados,
        desarrollador=simulados,
        tester=simulados,
    )
    configuracion = ConfiguracionOrquestador(_env_file=None)
    app = construir_grafo(servicios, configuracion).compile(
        checkpointer=InMemorySaver(serde=serializador())
    )
    inicio = time.perf_counter()
    _, avance = iniciar_sesion(app, caso.cliente, caso.proyecto, caso.necesidad, id_sesion)
    while avance.pausa is not None and avance.pausa.punto == "dialogo":
        conversacion = app.get_state(configuracion_hilo(id_sesion)).values["conversacion"]
        respuesta = simulado.responder(conversacion, avance.pausa.datos["pregunta"])
        avance = avanzar(app, id_sesion, respuesta)
    segundos = time.perf_counter() - inicio
    estado = app.get_state(configuracion_hilo(id_sesion)).values
    conversacion = estado["conversacion"]
    registro = conversacion.registro
    requerimientos = estado["requerimientos"].requerimientos
    defectos = avance.pausa.datos.get("defectos", []) if avance.pausa else []
    costos: dict[str, Decimal] = defaultdict(Decimal)
    for llamada in registro_llamadas.llamadas:
        costos[CLIENTE if llamada.nodo == CLIENTE else "sistema"] += llamada.costo_usd
    en_registro = tuple(
        regla.id
        for regla in caso.reglas_ocultas
        if _contiene(texto_del_registro(registro), regla.terminos)
    )
    en_requerimientos = tuple(
        regla.id
        for regla in caso.reglas_ocultas
        if any(_contiene(texto_del_requerimiento(r), regla.terminos) for r in requerimientos)
    )
    juicios = (
        juzgar(
            cliente_modelo,
            registro_llamadas,
            caso,
            registro.model_dump(mode="json"),
            [r.model_dump(mode="json") for r in requerimientos],
        )
        if caso.reglas_ocultas
        else []
    )
    salida.mkdir(parents=True, exist_ok=True)
    (salida / f"{caso.id}-{numero}.json").write_text(
        json.dumps(
            {
                "sesion": id_sesion,
                "turnos": [
                    {"emisor": turno.emisor.value, "texto": turno.texto}
                    for turno in conversacion.turnos
                ],
                "registro": registro.model_dump(mode="json"),
                "requerimientos": [r.model_dump(mode="json") for r in requerimientos],
                "defectos": list(defectos),
                "juicios": [juicio.model_dump() for juicio in juicios],
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
        turnos=conversacion.turnos_cliente,
        en_limite=conversacion.turnos_cliente >= configuracion.max_turnos_elicitacion,
        confirmado=registro.resumen_confirmado,
        categorias=tuple(registro.categorias_casos_limite),
        casos_limite=len(registro.casos_limite),
        requerimientos=len(requerimientos),
        escenarios=sum(len(r.criterios_aceptacion) for r in requerimientos),
        defectos=len(defectos),
        ocultas_registro=en_registro,
        ocultas_requerimientos=en_requerimientos,
        juez_registro=recogidas(juicios, "en_registro"),
        juez_requerimientos=recogidas(juicios, "en_requerimientos"),
        costo_sistema=costos["sistema"],
        costo_cliente=costos[CLIENTE],
        segundos=segundos,
    )


def rejuzgar(sesiones: Path, carpeta: Path, traza: Path) -> None:
    """Vuelve a juzgar las sesiones guardadas, con las reglas ocultas de sus casos."""
    casos = {caso.id: caso for caso in map(cargar_caso, carpeta.glob("elicitacion-*.md"))}
    cliente = crear_cliente(ConfiguracionAzureOpenAI())
    por_caso: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for archivo in sorted(sesiones.glob("*.json")):
        datos = json.loads(archivo.read_text(encoding="utf-8"))
        caso_id = archivo.stem.rsplit("-", 1)[0]
        caso = casos.get(caso_id)
        if caso is None or not caso.reglas_ocultas:
            continue
        juicios = juzgar(
            cliente,
            RegistroJsonl(traza, sesion=datos["sesion"]),
            caso,
            datos["registro"],
            datos["requerimientos"],
        )
        datos["juicios"] = [juicio.model_dump() for juicio in juicios]
        archivo.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", "utf-8")
        en_registro = recogidas(juicios, "en_registro")
        en_rf = recogidas(juicios, "en_requerimientos")
        por_caso[caso_id].append((len(en_registro), len(en_rf)))
        print(f"{archivo.stem}: registro {list(en_registro)} · RF {list(en_rf)}")
        for juicio in juicios:
            print(f"    {juicio.id} {juicio.en_requerimientos:7} {juicio.evidencia[:150]}")
    for caso_id, cuentas in por_caso.items():
        print(
            f"{caso_id}: en el registro {[r for r, _ in cuentas]}, en los RF "
            f"{[f for _, f in cuentas]} de {len(casos[caso_id].reglas_ocultas)}"
        )


def main() -> None:
    """Corre cada caso las veces pedidas e imprime el resumen."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--carpeta", type=Path, default=CARPETA, help="Carpeta de los casos.")
    parser.add_argument("--casos", nargs="*", default=[], help="Partes del nombre de los casos.")
    parser.add_argument("--corridas", type=int, default=1, help="Corridas por caso.")
    parser.add_argument("--traza", type=Path, default=ARCHIVO_MEDICIONES, help="Traza JSONL.")
    parser.add_argument("--salida", type=Path, default=SALIDA, help="Carpeta de las sesiones.")
    parser.add_argument(
        "--rejuzgar", type=Path, help="Vuelve a juzgar las sesiones guardadas en esta carpeta."
    )
    argumentos = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format="(aviso) %(message)s")
    if argumentos.rejuzgar:
        rejuzgar(argumentos.rejuzgar, argumentos.carpeta, argumentos.traza.resolve())
        return

    archivos = sorted(argumentos.carpeta.glob("elicitacion-*.md"))
    if argumentos.casos:
        archivos = [a for a in archivos if any(parte in a.stem for parte in argumentos.casos)]
    corridas: list[Corrida] = []
    cadena = ConfiguracionBaseDatos().cadena_conexion()
    with psycopg.connect(cadena, autocommit=True) as conexion:
        for archivo in archivos:
            caso = cargar_caso(archivo)
            for numero in range(1, argumentos.corridas + 1):
                corrida = elicitar(
                    caso, numero, conexion, argumentos.traza.resolve(), argumentos.salida
                )
                corridas.append(corrida)
                ocultas = (
                    f" · ocultas por términos: registro {list(corrida.ocultas_registro)}, RF "
                    f"{list(corrida.ocultas_requerimientos)}; por el juez: registro "
                    f"{list(corrida.juez_registro)}, RF {list(corrida.juez_requerimientos)} de "
                    f"{len(caso.reglas_ocultas)}"
                    if caso.reglas_ocultas
                    else ""
                )
                print(
                    f"{corrida.caso} #{numero}: {corrida.turnos} turnos"
                    f"{' (en el límite)' if corrida.en_limite else ''} · resumen "
                    f"{'confirmado' if corrida.confirmado else 'sin confirmar'} · casos límite "
                    f"{list(corrida.categorias)} ({corrida.casos_limite} definidos) · "
                    f"{corrida.requerimientos} RF, {corrida.escenarios} escenarios, "
                    f"{corrida.defectos} defectos{ocultas} · USD {corrida.costo_sistema:.4f} "
                    f"(cliente {corrida.costo_cliente:.4f}) · {corrida.segundos:.0f} s",
                    flush=True,
                )
    if not corridas:
        print("No hay casos que correr.")
        return
    sistema = sum((c.costo_sistema for c in corridas), Decimal(0))
    cliente = sum((c.costo_cliente for c in corridas), Decimal(0))
    print(
        f"\n{len(corridas)} corridas · turnos {sum(c.turnos for c in corridas)} · resúmenes "
        f"confirmados {sum(c.confirmado for c in corridas)} · en el límite "
        f"{sum(c.en_limite for c in corridas)} · preguntas por casos límite "
        f"{sum(len(c.categorias) for c in corridas)} · USD {sistema:.4f} del sistema y "
        f"{cliente:.4f} del cliente"
    )
    por_caso: dict[str, list[Corrida]] = defaultdict(list)
    for corrida in corridas:
        por_caso[corrida.caso].append(corrida)
    for caso_id, propias in por_caso.items():
        if any(c.juez_registro or c.juez_requerimientos for c in propias):
            print(
                f"{caso_id}: reglas ocultas según el juez, en el registro "
                f"{[len(c.juez_registro) for c in propias]} y en los RF "
                f"{[len(c.juez_requerimientos) for c in propias]}"
            )
    print(f"Traza: {argumentos.traza} · sesiones: {argumentos.salida}")


if __name__ == "__main__":
    main()
