"""Matriz de confusión del tester frente al oráculo común (paso 15, ADR-0019).

Evalúa con las pruebas de referencia cada versión que el tester dictaminó en los casos de
referencia, y cruza ese resultado con su veredicto. Lo positivo es una versión con un error de
referencia; la predicción positiva, que el tester la rechace.

Una versión usa el adaptador de su corrida, el mismo de `scripts/evaluar_referencia.py`, salvo que
exista `adaptadores/<etiqueta>-v<n>.py` para esa versión. Corre en el entorno aislado, sin costo de
modelos. Cada versión queda en `<salida>/<etiqueta>-v<n>.json`; una con resultado se salta, salvo
con `--rehacer`.

Uso:
    python scripts/matriz_tester_oraculo.py
"""

import argparse
import json
from pathlib import Path

from multiagente.evaluacion.matriz import (
    VersionEvaluada,
    matriz_de_versiones,
    rechazada_por_el_tester,
)
from multiagente.evaluacion.referencia import (
    RAIZ_REFERENCIA,
    ErrorReferencia,
    cargar_caso_referencia,
    casos_de_referencia,
    evaluar_referencia,
    leer_implementacion,
)
from multiagente.sandbox.ejecutor import EntornoAislado

RAIZ = Path(__file__).resolve().parents[1]
RESULTADOS = RAIZ / "evaluacion" / "resultados" / "paso-15"
SALIDA = RESULTADOS / "matriz-oraculo"
CORRIDAS_DEL_SISTEMA = ("corrida-ampliada", "sistema-2")
REPORTE = "REPORTE_VALIDACION.md"


def sesiones_del_caso(caso: str) -> list[tuple[str, Path]]:
    """Etiqueta y carpeta de cada sesión del sistema sobre un caso de referencia."""
    numero = caso.rsplit("-", 1)[-1]
    sesiones = []
    for orden, nombre in enumerate(CORRIDAS_DEL_SISTEMA, start=1):
        resultado = RESULTADOS / nombre / f"{caso}.json"
        if resultado.exists():
            sesion = json.loads(resultado.read_text(encoding="utf-8"))["sesion"]
            sesiones.append((f"sistema-{numero}-{orden}", RESULTADOS / nombre / sesion))
    return sesiones


def _adaptador(caso: str, etiqueta: str, version: int) -> Path:
    carpeta = RAIZ_REFERENCIA / caso / "adaptadores"
    propio = carpeta / f"{etiqueta}-v{version}.py"
    return propio if propio.exists() else carpeta / f"{etiqueta}.py"


def evaluar_version(
    entorno: EntornoAislado, caso: str, etiqueta: str, carpeta: Path, salida: Path, rehacer: bool
) -> VersionEvaluada | None:
    """Evalúa una versión con el oráculo y lee el veredicto del tester.

    Returns:
        La versión evaluada, o None si no hay reporte, adaptador o el adaptador no se admite.
    """
    numero = int(carpeta.name[1:])
    destino = salida / f"{etiqueta}-v{numero}.json"
    if not (carpeta / REPORTE).exists():
        return None
    rechazada = rechazada_por_el_tester((carpeta / REPORTE).read_text(encoding="utf-8"))
    if destino.exists() and not rehacer:
        datos = json.loads(destino.read_text(encoding="utf-8"))
        return VersionEvaluada(caso, etiqueta, numero, rechazada, datos["pasan"], datos["total"])
    adaptador = _adaptador(caso, etiqueta, numero)
    if not adaptador.exists():
        print(f"{etiqueta} v{numero}: sin adaptador todavía")
        return None
    try:
        resultado = evaluar_referencia(
            entorno,
            cargar_caso_referencia(caso),
            adaptador.read_text(encoding="utf-8"),
            leer_implementacion(carpeta),
        )
    except ErrorReferencia as error:
        print(f"{etiqueta} v{numero}: {error}")
        return None
    destino.write_text(
        json.dumps(
            {
                "caso": caso,
                "etiqueta": etiqueta,
                "version": numero,
                "rechazada": rechazada,
                "pasan": resultado.cuenta("paso"),
                "total": resultado.total,
                "referencia": resultado.model_dump(mode="json"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return VersionEvaluada(
        caso, etiqueta, numero, rechazada, resultado.cuenta("paso"), resultado.total
    )


def _metrica(valor: float | None) -> str:
    return "no aplica" if valor is None else f"{valor:.2f}".replace(".", ",")


def main() -> None:
    """Evalúa las versiones e imprime la tabla y la matriz en Markdown."""
    argumentos = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    argumentos.add_argument("--salida", type=Path, default=SALIDA, help="carpeta de resultados")
    argumentos.add_argument("--rehacer", action="store_true", help="evalúa también las evaluadas")
    opciones = argumentos.parse_args()
    opciones.salida.mkdir(parents=True, exist_ok=True)
    entorno = EntornoAislado()
    versiones = []
    for caso in casos_de_referencia():
        for etiqueta, sesion in sesiones_del_caso(caso):
            carpetas = sorted(
                (p for p in sesion.glob("v*") if p.is_dir() and p.name[1:].isdigit()),
                key=lambda p: int(p.name[1:]),
            )
            for carpeta in carpetas:
                evaluada = evaluar_version(
                    entorno, caso, etiqueta, carpeta, opciones.salida, opciones.rehacer
                )
                if evaluada is not None:
                    versiones.append(evaluada)
    print("| Corrida | Versión | Tester | Referencia | Celda |")
    print("|---|---|---|---|---|")
    for v in versiones:
        celda = {
            (True, True): "VP",
            (False, True): "FP",
            (True, False): "FN",
            (False, False): "VN",
        }[(v.tiene_error, v.rechazada)]
        print(
            f"| {v.etiqueta} | v{v.version} | {'rechaza' if v.rechazada else 'aprueba'} | "
            f"{v.pasan} de {v.total} | {celda} |"
        )
    m = matriz_de_versiones(versiones)
    print(f"\n**Versiones:** {m.total}")
    print("\n| | Con error de referencia | Sin error de referencia |")
    print("|---|---|---|")
    print(f"| Tester rechaza | {m.verdaderos_positivos} | {m.falsos_positivos} |")
    print(f"| Tester aprueba | {m.falsos_negativos} | {m.verdaderos_negativos} |")
    print(
        f"\n**Exactitud:** {_metrica(m.exactitud)} · **Precisión:** {_metrica(m.precision)} · "
        f"**Sensibilidad:** {_metrica(m.sensibilidad)} · **F1:** {_metrica(m.f1)}"
    )


if __name__ == "__main__":
    main()
