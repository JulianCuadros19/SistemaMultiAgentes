"""Calidad estática de las implementaciones del objetivo 4 (ADR-0019), sin costo.

Mide por igual las implementaciones de `evaluacion/referencia/implementaciones.json` con las
métricas que el ADR-0019 fijó antes de calcularlas. Solo lee el código: no lo ejecuta ni llama a
ningún modelo.

Guarda el resultado de cada implementación e imprime todas las métricas, también las que salen en
contra: la media por enfoque y, frente a cada línea base, en cuántos casos el sistema queda mejor,
peor o igual.

Uso:
    python scripts/calidad_estatica.py
"""

import json
from collections import defaultdict
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path

from multiagente.evaluacion.calidad_estatica import Metricas, leer_archivos, medir
from multiagente.evaluacion.comparacion import comparar_por_caso

RAIZ = Path(__file__).resolve().parents[1]
MANIFIESTO = RAIZ / "evaluacion" / "referencia" / "implementaciones.json"
SALIDA = RAIZ / "evaluacion" / "resultados" / "paso-15" / "calidad-estatica"
ENFOQUES = ("sistema", "modelo_unico", "un_prompt")
NOMBRES = {"modelo_unico": "con diálogo", "un_prompt": "de un solo prompt"}
METRICAS = (
    ("CAL-FS-005, usos de float monetario", "usos_float_monetario", "menos"),
    ("CAL-SG-001, credenciales en el código", "credenciales", "menos"),
    ("CAL-MT-003, complejidad media por función", "complejidad_media", "menos"),
    ("CAL-MT-003, complejidad máxima", "complejidad_maxima", "menos"),
    ("CAL-MT-010, nombres privados importados", "nombres_privados", "menos"),
    ("CAL-FB-001, sentencias global", "sentencias_global", "menos"),
    ("CAL-FB-003, recursos fuera de with", "recursos_sin_with", "menos"),
    ("CAL-FB-004, usos no deterministas en pruebas", "no_deterministas", "menos"),
    ("CAL-FS-004, pruebas que esperan un rechazo", "pruebas_de_rechazo", "más"),
    ("CAL-FS-004, proporción de pruebas de rechazo", "proporcion_de_rechazo", "más"),
    ("Contexto, módulos", "modulos", None),
    ("Contexto, líneas de código", "lineas_codigo", None),
    ("Contexto, líneas de pruebas", "lineas_pruebas", None),
    ("Contexto, funciones de prueba", "funciones_de_prueba", None),
)


def _media(valores: list[float]) -> float:
    """Calcula la media de una lista no vacía."""
    return sum(valores) / len(valores)


def _por_caso(medidas: list[tuple[str, Metricas]], atributo: str) -> dict[str, Decimal]:
    """Calcula la media de una métrica en cada caso."""
    casos: dict[str, list[float]] = defaultdict(list)
    for caso, metricas in medidas:
        casos[caso].append(float(getattr(metricas, atributo)))
    return {caso: Decimal(str(_media(valores))) for caso, valores in casos.items()}


def main() -> None:
    """Punto de entrada del guion."""
    SALIDA.mkdir(parents=True, exist_ok=True)
    por_enfoque: dict[str, list[tuple[str, Metricas]]] = defaultdict(list)
    for implementacion in json.loads(MANIFIESTO.read_text(encoding="utf-8")):
        metricas = medir(leer_archivos(RAIZ / implementacion["carpeta"]))
        por_enfoque[implementacion["enfoque"]].append((implementacion["caso"], metricas))
        resultado = {**implementacion, **asdict(metricas)}
        destino = SALIDA / f"{implementacion['etiqueta']}.json"
        destino.write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")

    cantidades = " · ".join(f"{enfoque}: {len(por_enfoque[enfoque])}" for enfoque in ENFOQUES)
    print(f"**Implementaciones:** {cantidades}\n")
    print("| Métrica | Mejor | Sistema | Con diálogo | Un prompt |")
    print("|---|---|---:|---:|---:|")
    for nombre, atributo, mejor in METRICAS:
        medias = [
            _media([float(getattr(metricas, atributo)) for _, metricas in por_enfoque[enfoque]])
            for enfoque in ENFOQUES
        ]
        celdas = " | ".join(f"{media:.2f}" for media in medias)
        print(f"| {nombre} | {mejor or '—'} | {celdas} |")

    print("\n**El sistema frente a cada línea base, por caso:** mejor, peor e igual.\n")
    print("| Métrica | Frente al modelo con diálogo | Frente al de un solo prompt |")
    print("|---|---:|---:|")
    for nombre, atributo, mejor in METRICAS:
        if mejor is None:
            continue
        sistema = _por_caso(por_enfoque["sistema"], atributo)
        celdas = []
        for enfoque in ("modelo_unico", "un_prompt"):
            comparacion = comparar_por_caso(sistema, _por_caso(por_enfoque[enfoque], atributo))
            gana, pierde = (
                (comparacion.menor, comparacion.mayor)
                if mejor == "menos"
                else (comparacion.mayor, comparacion.menor)
            )
            celdas.append(f"{gana} · {pierde} · {comparacion.empates}")
        print(f"| {nombre} | {celdas[0]} | {celdas[1]} |")


if __name__ == "__main__":
    main()
