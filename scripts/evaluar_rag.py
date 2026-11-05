"""Métricas RAGs sobre las sesiones guardadas de una corrida (paso 15, ADR-0019).

**Qué hace.** Lee el estado final de cada sesión en PostgreSQL, sin ejecutar ningún nodo. Arma una
muestra por agente que consultó una base de conocimiento:
- la consulta;
- los fragmentos recuperados, por colección;
- las demás entradas;
- el artefacto.

**Juez y métricas.** Un juez externo al sistema juzga cada muestra: el despliegue de N10, con
esfuerzo bajo y el prompt de `evaluacion/juez_rag.md`. Con su juicio se calculan la fidelidad, la
relevancia de la respuesta (con BGE-M3) y la relevancia del contexto por colección.

**Sesiones.** Salen de los resultados de `scripts/evaluar_extremo_a_extremo.py` (`--resultados
DIR`), del campo `sesion` de cada caso. Primero van los casos impares (01, 03… 19), que cubren las
seis arquitecturas, y después los pares. Si el presupuesto no alcanza para todas, las evaluadas
siguen cubriendo el catálogo.

**Resultados.** Cada muestra queda en `<salida>/<sesión>-<agente>.json`; una con resultado se salta.

**Costo.** Antes de cada muestra se suma lo gastado en la traza
(`docs/mediciones/paso-15-rag.jsonl`). Si con una muestra más se pasaría del presupuesto, se
detiene. Cada muestra cuesta unos 0,055 USD: trae de 8 a 28 fragmentos.

**Revisión humana.** `--revision N` escribe en `<salida>/revision.md` N juicios, elegidos al azar
con semilla fija, con lo que el juez recibió.

Requiere `docker compose up -d --wait db embeddings` y el archivo .env.

Uso:
    python scripts/evaluar_rag.py --resultados DIR --presupuesto 1
    python scripts/evaluar_rag.py --resumen
    python scripts/evaluar_rag.py --revision 5
"""

import argparse
import json
import logging
import random
import re
from decimal import Decimal
from pathlib import Path

from multiagente.core.configuracion import (
    ConfiguracionAzureOpenAI,
    ConfiguracionModelos,
    ConfiguracionOrquestador,
)
from multiagente.evaluacion.rag import (
    NODO_JUEZ,
    RUTA_PROMPT,
    MetricasRag,
    evaluar_muestra,
    muestras_de_sesion,
    resumen_por_coleccion,
)
from multiagente.evaluacion.traza import gastado_en_traza
from multiagente.interfaces.cliente_simulado import RAIZ_EVALUACION
from multiagente.interfaces.operacion import Operador
from multiagente.llm.cliente import crear_cliente
from multiagente.llm.invocador import InvocadorNodo, ParametrosNodo
from multiagente.llm.prompts import leer_prompt
from multiagente.llm.traza import RegistroJsonl
from multiagente.orquestador.grafo import construir_grafo
from multiagente.orquestador.simulacion import ServiciosSimulados
from multiagente.persistencia.puntos_control import abrir_checkpointer
from multiagente.rag.embeddings import VectorizadorTEI

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ_EVALUACION / "resultados" / "paso-15" / "rag"
TRAZA = RAIZ / "docs" / "mediciones" / "paso-15-rag.jsonl"
COSTO_ESTIMADO_POR_MUESTRA = Decimal("0.08")
"""Margen que se reserva antes de juzgar una muestra, para no pasar del presupuesto."""
MAX_TOKENS_JUEZ = 8000
PRIMEROS = 2000
"""Caracteres de cada parte que se guardan junto al juicio, para la revisión humana."""


def sesiones_de_resultados(carpeta: Path) -> list[tuple[str, str]]:
    """Caso y sesión de cada resultado, primero los casos impares y después los pares."""
    pares = []
    for archivo in carpeta.glob("caso-*.json"):
        resultado = json.loads(archivo.read_text(encoding="utf-8"))
        if resultado.get("sesion"):
            pares.append((resultado["caso"], resultado["sesion"]))

    def orden(par: tuple[str, str]) -> tuple[int, str]:
        numero = re.search(r"(\d+)$", par[0])
        return ((int(numero.group(1)) + 1) % 2 if numero else 2, par[0])

    return sorted(pares, key=orden)


def evaluar(
    sesiones: list[tuple[str, str]], salida: Path, traza: Path, presupuesto: Decimal
) -> None:
    """Juzga las muestras sin resultado, mientras alcance el presupuesto."""
    azure = crear_cliente(ConfiguracionAzureOpenAI())
    despliegue = ConfiguracionModelos().n10_generacion
    prompt = leer_prompt(RUTA_PROMPT)
    vectorizador = VectorizadorTEI()
    salida.mkdir(parents=True, exist_ok=True)
    with abrir_checkpointer() as puntos:
        # Solo se leen estados guardados: el grafo no ejecuta ningún nodo.
        app = construir_grafo(
            ServiciosSimulados().como_servicios(), ConfiguracionOrquestador(_env_file=None)
        ).compile(checkpointer=puntos)
        operador = Operador(app)
        for caso, sesion in sesiones:
            for muestra in muestras_de_sesion(sesion, operador.estado(sesion)):
                destino = salida / f"{sesion}-{muestra.agente}.json"
                if destino.exists():
                    continue
                if (total := gastado_en_traza(traza)) + COSTO_ESTIMADO_POR_MUESTRA > presupuesto:
                    print(f"Presupuesto: USD {total:.4f} de {presupuesto}. Se detiene en {caso}.")
                    return
                juez = InvocadorNodo(
                    azure,
                    ParametrosNodo(NODO_JUEZ, despliegue, "low", MAX_TOKENS_JUEZ),
                    prompt,
                    RegistroJsonl(traza, sesion=sesion),
                )
                metricas = evaluar_muestra(muestra, juez, vectorizador)
                datos = {
                    "caso": caso,
                    **metricas.model_dump(mode="json"),
                    "muestra": {
                        "colecciones": muestra.colecciones,
                        "consulta": muestra.consulta[:PRIMEROS],
                        "fragmentos": [
                            {
                                "id": id_fragmento,
                                "coleccion": recuperado.coleccion,
                                "fuente": recuperado.fragmento.referencia,
                                "contenido": recuperado.fragmento.contenido[:PRIMEROS],
                            }
                            for id_fragmento, recuperado in zip(
                                muestra.identificadores, muestra.fragmentos, strict=True
                            )
                        ],
                        "artefacto": muestra.artefacto[: PRIMEROS * 3],
                    },
                }
                destino.write_text(
                    json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                print(
                    f"{caso} · {muestra.agente}: fidelidad {metricas.fidelidad:.2f}, respuesta "
                    f"{metricas.relevancia_respuesta:.2f}, contexto "
                    + ", ".join(f"{c} {v.relevancia:.2f}" for c, v in metricas.contexto.items())
                )


def leer_metricas(salida: Path) -> list[MetricasRag]:
    """Métricas guardadas en la carpeta de salida."""
    return [
        MetricasRag.model_validate(json.loads(archivo.read_text(encoding="utf-8")))
        for archivo in sorted(salida.glob("*-*.json"))
    ]


def resumir(salida: Path, traza: Path) -> None:
    """Imprime la tabla por colección y lo gastado."""
    resumen = resumen_por_coleccion(leer_metricas(salida))
    print("| Colección | Agente | Muestras | Fidelidad | Relevancia de la respuesta | Contexto |")
    print("|---|---|---|---|---|---|")

    def celda(estadisticas: dict[str, float]) -> str:
        return (
            f"{estadisticas['media']:.2f} ({estadisticas['minimo']:.2f}–"
            f"{estadisticas['maximo']:.2f})"
        )

    for coleccion, fila in resumen.items():
        print(
            f"| {coleccion} | {fila['agente']} | {fila['muestras']} | {celda(fila['fidelidad'])} | "
            f"{celda(fila['relevancia_respuesta'])} | {celda(fila['relevancia_contexto'])} |"
        )
    print(f"\nGastado en la traza: USD {gastado_en_traza(traza):.4f}")


def revision(salida: Path, cantidad: int) -> None:
    """Escribe una muestra de juicios para la revisión humana."""
    archivos = sorted(salida.glob("*-*.json"))
    elegidos = random.Random(15).sample(archivos, min(cantidad, len(archivos)))
    lineas = ["# Revisión humana del juez de RAGs (paso 15)", ""]
    for archivo in elegidos:
        datos = json.loads(archivo.read_text(encoding="utf-8"))
        muestra, juicio = datos["muestra"], datos["juicio"]
        lineas += [
            f"## {datos['caso']} · {datos['agente']}",
            "",
            f"**Consulta:** {muestra['consulta']}",
            "",
        ]
        lineas += ["**Fragmentos:**", ""]
        necesario = {f["id"]: f["necesario"] for f in juicio["fragmentos"]}
        for fragmento in muestra["fragmentos"]:
            marca = "necesario" if necesario.get(fragmento["id"]) else "no necesario"
            lineas.append(
                f"- {fragmento['id']} ({fragmento['coleccion']}, {marca}): {fragmento['fuente']}"
            )
        lineas += ["", "**Afirmaciones:**", ""]
        for afirmacion in juicio["afirmaciones"]:
            sustento = afirmacion["fuente"] if afirmacion["sustentada"] else "sin sustento"
            lineas.append(f"- [{sustento}] {afirmacion['texto']}")
        lineas += ["", "**Preguntas propuestas:** " + " · ".join(juicio["preguntas"]), ""]
        lineas += ["¿Está de acuerdo con el juicio? Anote aquí sus diferencias:", "", ""]
    (salida / "revision.md").write_text("\n".join(lineas), encoding="utf-8")
    print(f"Escrita {salida / 'revision.md'} con {len(elegidos)} juicios.")


def main() -> None:
    """Punto de entrada del guion."""
    argumentos = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    origen = argumentos.add_mutually_exclusive_group()
    origen.add_argument(
        "--resultados", type=Path, help="resultados de una corrida extremo a extremo"
    )
    origen.add_argument("--sesiones", nargs="+", metavar="ID", help="sesiones a evaluar")
    argumentos.add_argument("--presupuesto", type=Decimal, help="tope en USD de la traza")
    argumentos.add_argument("--salida", type=Path, default=SALIDA, help="carpeta de resultados")
    argumentos.add_argument("--traza", type=Path, default=TRAZA, help="traza de las llamadas")
    argumentos.add_argument("--resumen", action="store_true", help="solo imprime el resumen")
    argumentos.add_argument("--revision", type=int, metavar="N", help="muestra para revisar")
    opciones = argumentos.parse_args()
    if opciones.resumen:
        resumir(opciones.salida, opciones.traza)
        return
    if opciones.revision:
        revision(opciones.salida, opciones.revision)
        return
    if opciones.presupuesto is None or not (opciones.resultados or opciones.sesiones):
        argumentos.error("hacen falta --presupuesto y --resultados o --sesiones: tiene costo")
    logging.basicConfig(level=logging.WARNING, format="(aviso) %(message)s")
    sesiones = (
        sesiones_de_resultados(opciones.resultados)
        if opciones.resultados
        else [(sesion, sesion) for sesion in opciones.sesiones]
    )
    evaluar(sesiones, opciones.salida, opciones.traza, opciones.presupuesto)
    resumir(opciones.salida, opciones.traza)


if __name__ == "__main__":
    main()
