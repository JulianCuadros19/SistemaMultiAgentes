"""Evalúa al tester real sobre el corpus de defectos inyectados (paso 10).

Somete cada variante del corpus (`evaluacion/defectos/`) a N11–N14:
- N11 ejecuta en el entorno aislado;
- N12 analiza;
- N13 recupera los criterios con BGE-M3;
- N14 dictamina con el juez indicado.

N11, N12 y N13 son determinísticos y se calculan una vez por variante; el juez se repite en cada
corrida.

Una variante con defecto se detecta si el veredicto coincide con el esperado y aparece cada
regla esperada. Un control acierta si sale aprobado sin hallazgos. El juez se mide además por
caso: cada caso que marca fuera de los esperados (`casos_juez`) es un rechazo falso, aunque el
veredicto de la variante no cambie. El script imprime la matriz de confusión por variante, los
aciertos del juez por caso, sus errores con la justificación y el costo. Cada llamada al modelo se
agrega a la traza (por defecto docs/mediciones/paso-10-tester.jsonl; otra con `--traza`), sin el
contenido de los mensajes.

Requiere `docker compose up -d --wait`, la imagen del entorno aislado, el corpus ingerido y el
archivo .env. Tiene costo.

Uso:
    python scripts/evaluar_tester.py --modelo-juez gpt-6-luna --corridas 3 --solo-juez
    python scripts/evaluar_tester.py --corridas 1
"""

import argparse
import logging
import statistics
import time
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import psycopg

from multiagente.agentes.tester.servicio import crear_agente_tester
from multiagente.core.configuracion import (
    ConfiguracionAzureOpenAI,
    ConfiguracionBaseDatos,
    ConfiguracionModelos,
)
from multiagente.core.esquemas.especificacion_diseno import EspecificacionDiseno
from multiagente.interfaces.defectos import CorpusDefectos, Variante, cargar_corpus_de_defectos
from multiagente.llm.cliente import crear_cliente
from multiagente.llm.traza import RegistroJsonl
from multiagente.orquestador.estado import (
    CasoPrueba,
    Contexto,
    Requerimientos,
    Validacion,
    Veredicto,
    VersionCodigo,
)
from multiagente.orquestador.servicios import Dictamen

RAIZ = Path(__file__).resolve().parents[1]
ARCHIVO_MEDICIONES = RAIZ / "docs" / "mediciones" / "paso-10-tester.jsonl"


@dataclass
class Preparada:
    """Variante con su validación de N11 y N12 y los criterios de N13, listos para N14."""

    variante: Variante
    plan: tuple[CasoPrueba, ...]
    validacion: Validacion
    contexto: Contexto
    version: VersionCodigo
    especificacion: EspecificacionDiseno


def plan_de(requerimientos: Requerimientos) -> tuple[CasoPrueba, ...]:
    """Plan de pruebas de aceptación como lo deriva N16: un caso por escenario."""
    return tuple(
        CasoPrueba(
            id=f"CP-{r.id_requerimiento}-{e.id}",
            id_requerimiento=r.id_requerimiento,
            id_escenario=e.id,
            dado_que=e.dado_que,
            cuando=e.cuando,
            entonces=e.entonces,
        )
        for r in requerimientos.requerimientos
        for e in r.criterios_aceptacion
    )


def preparar(tester: object, corpus: CorpusDefectos, variante: Variante) -> Preparada:
    """Corre N11, N12 y N13 sobre una variante."""
    caso = corpus.caso
    requerimientos = Requerimientos(
        historias=caso.sintesis.historias, requerimientos=caso.sintesis.requerimientos
    )
    version = VersionCodigo(numero=1, archivos=variante.archivos)
    plan = plan_de(requerimientos)
    ejecucion = tester.ejecutar(version, caso.especificacion)
    analisis = tester.analizar(version, caso.especificacion, requerimientos)
    validacion = Validacion(
        plan_pruebas=plan,
        ejecucion=ejecucion,
        hallazgos=analisis.hallazgos,
        conformidad=analisis.conformidad,
        no_evaluadas=analisis.no_evaluadas,
    )
    contexto = tester.recuperar_criterios(validacion)
    return Preparada(variante, plan, validacion, contexto, version, caso.especificacion)


def casos_marcados_por_el_juez(dictamen: Dictamen) -> tuple[set[str], int]:
    """Casos que el juez marcó como incumplidos y cuántos casos juzgó.

    El juez solo recibe los casos cuyas pruebas pasaron; su evidencia empieza con «… pasan.».
    """
    juzgados = [v for v in dictamen.veredictos if " pasan. " in v.evidencia]
    return {v.id_caso for v in juzgados if not v.cumple}, len(juzgados)


def acierta(variante: Variante, dictamen: Dictamen) -> bool:
    """Indica si el dictamen es el esperado para la variante."""
    reglas = {h.regla for h in dictamen.hallazgos}
    if variante.es_control:
        return dictamen.veredicto is Veredicto.APROBADO and not dictamen.hallazgos
    return (
        dictamen.veredicto is variante.esperado.veredicto
        and set(variante.esperado.reglas) <= reglas
    )


def main() -> None:
    """Evalúa al tester y muestra la matriz de confusión por corrida y en total."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--modelo-juez", help="Despliegue del juez; por defecto, el de .env.")
    parser.add_argument("--corridas", type=int, default=1, help="Corridas del juez.")
    parser.add_argument(
        "--traza",
        type=Path,
        default=ARCHIVO_MEDICIONES,
        help="Archivo JSONL de la traza; por defecto, el del paso 10.",
    )
    parser.add_argument(
        "--solo-juez",
        action="store_true",
        help="Solo los controles y los defectos que detecta el juez (selección del modelo).",
    )
    argumentos = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format="(aviso) %(message)s")

    modelo = argumentos.modelo_juez or ConfiguracionModelos().n14_veredicto
    registro = RegistroJsonl(
        argumentos.traza.resolve(), sesion=f"tester-{modelo}-{int(time.time())}"
    )
    variantes = [
        (corpus, variante)
        for corpus in cargar_corpus_de_defectos()
        for variante in corpus.variantes()
        if not argumentos.solo_juez or variante.es_control or variante.defecto.solo_juez
    ]
    print(f"Juez: {modelo} · {len(variantes)} variantes · {argumentos.corridas} corridas")
    cadena = ConfiguracionBaseDatos().cadena_conexion()
    with psycopg.connect(cadena, autocommit=True) as conexion:
        tester = crear_agente_tester(
            conexion,
            registro,
            crear_cliente(ConfiguracionAzureOpenAI()),
            despliegue_juez=modelo,
        )
        inicio = time.perf_counter()
        preparadas = [preparar(tester, corpus, variante) for corpus, variante in variantes]
        print(f"N11–N13 preparados en {time.perf_counter() - inicio:.1f} s")

        totales: Counter[str] = Counter()
        juez: Counter[str] = Counter()
        for corrida in range(1, argumentos.corridas + 1):
            matriz: Counter[str] = Counter()
            for preparada in preparadas:
                variante = preparada.variante
                dictamen = tester.dictaminar(
                    preparada.plan,
                    preparada.validacion,
                    preparada.contexto,
                    preparada.version,
                    preparada.especificacion,
                )
                bien = acierta(variante, dictamen)
                clave = (
                    ("TN" if bien else "FP") if variante.es_control else ("TP" if bien else "FN")
                )
                matriz[clave] += 1
                reglas = sorted({h.regla for h in dictamen.hallazgos})
                marca = "ok   " if bien else "ERROR"
                print(
                    f"  [{corrida}] {marca} {variante.id:16} {dictamen.veredicto.value:9} {reglas}"
                )
                marcados, juzgados = casos_marcados_por_el_juez(dictamen)
                esperados = set(variante.esperado.casos_juez)
                juez["juzgados"] += juzgados
                juez["aciertos"] += len(marcados & esperados)
                juez["rechazos_falsos"] += len(marcados - esperados)
                juez["omisiones"] += len(esperados - marcados)
                errores_juez = (marcados - esperados) | (esperados - marcados)
                if not bien or errores_juez:
                    for veredicto in dictamen.veredictos:
                        if not veredicto.cumple or veredicto.id_caso in errores_juez:
                            print(f"        {veredicto.id_caso}: {veredicto.evidencia[:300]}")
            totales.update(matriz)
            print(f"Corrida {corrida}: {dict(matriz)}")

    llamadas = registro.llamadas
    costo = sum((llamada.costo_usd for llamada in llamadas), Decimal(0))
    tp, fn, tn, fp = (totales[clave] for clave in ("TP", "FN", "TN", "FP"))
    total = tp + fn + tn + fp
    print(f"\nTotal: TP {tp} · FN {fn} · TN {tn} · FP {fp}")
    if total:
        exactitud = (tp + tn) / total
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        print(
            f"Exactitud {exactitud:.3f} · precisión {precision:.3f} · recall {recall:.3f} · "
            f"F1 {f1:.3f}"
        )
    print(
        f"Juez por caso: {juez['juzgados']} casos juzgados · {juez['aciertos']} defectos "
        f"marcados · {juez['rechazos_falsos']} rechazos falsos · {juez['omisiones']} omisiones"
    )
    if llamadas:
        latencias = [llamada.latencia_ms / 1000 for llamada in llamadas]
        errores = sum(1 for llamada in llamadas if llamada.error)
        print(
            f"Juez: {len(llamadas)} llamadas ({errores} con error) · latencia media "
            f"{statistics.mean(latencias):.1f} s, máxima {max(latencias):.1f} s · "
            f"USD {costo:.5f} · {registro.ruta.relative_to(RAIZ)}"
        )


if __name__ == "__main__":
    main()
