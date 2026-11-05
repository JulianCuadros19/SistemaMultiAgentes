"""Tabla comparativa del objetivo 4: el sistema y dos líneas base de un solo modelo (ADR-0019).

Se regenera sin costo desde los resultados guardados:
- las verificaciones de referencia, de `evaluacion/resultados/paso-15/referencia/`;
- el tiempo y el costo del sistema, de los resultados de cada corrida;
- los de las líneas base, de su `resultado.json`.

Imprime la tabla por caso y enfoque, y la prueba de signos por caso en costo, tiempo y errores.

Uso:
    python scripts/tabla_objetivo_4.py
"""

import json
from decimal import Decimal
from pathlib import Path

from multiagente.evaluacion.comparacion import (
    Medicion,
    Resumen,
    agrupar,
    comparar_por_caso,
)

RAIZ = Path(__file__).resolve().parents[1]
RESULTADOS = RAIZ / "evaluacion" / "resultados" / "paso-15"
CORRIDAS_DEL_SISTEMA = ("corrida-ampliada", "sistema-2")
CARPETAS_DE_LINEA_BASE = {"modelo_unico": "modelo-unico", "un_prompt": "llm-un-prompt"}
SEGUNDOS_POR_MINUTO = Decimal(60)
NOMBRES = {
    "sistema": "Sistema multiagente",
    "modelo_unico": "LLM con diálogo",
    "un_prompt": "LLM de un solo prompt",
}


def medir_sistema(referencia: dict[str, object]) -> Medicion:
    """Mide una corrida automática del sistema."""
    etiqueta = str(referencia["etiqueta"])
    orden = int(etiqueta.rsplit("-", 1)[-1])
    corrida = CORRIDAS_DEL_SISTEMA[orden - 1]
    caso = json.loads((RESULTADOS / corrida / f"{referencia['caso']}.json").read_text("utf-8"))
    return Medicion(
        caso=str(referencia["caso"]),
        enfoque="sistema",
        etiqueta=etiqueta,
        tiempo_maquina_min=Decimal(str(caso["tiempo_sistema_min"])),
        inferencia_usd=Decimal(str(caso["costo_sistema"])),
        pasan=int(referencia["pasan"]),
        total=int(referencia["total"]),
    )


def medir_linea_base(referencia: dict[str, object]) -> Medicion:
    """Mide una corrida de una línea base de un solo modelo."""
    etiqueta = str(referencia["etiqueta"])
    enfoque = str(referencia["enfoque"])
    corrida = etiqueta.rsplit("-", 1)[-1]
    datos = json.loads(
        (
            RESULTADOS
            / CARPETAS_DE_LINEA_BASE[enfoque]
            / str(referencia["caso"])
            / f"corrida-{corrida}"
            / "resultado.json"
        ).read_text("utf-8")
    )
    segundos = Decimal(str(datos["tiempo_total_s"])) - Decimal(str(datos["tiempo_cliente_s"]))
    return Medicion(
        caso=str(referencia["caso"]),
        enfoque=enfoque,
        etiqueta=etiqueta,
        tiempo_maquina_min=segundos / SEGUNDOS_POR_MINUTO,
        inferencia_usd=Decimal(str(datos["costo_modelo_usd"])),
        pasan=int(referencia["pasan"]),
        total=int(referencia["total"]),
    )


def _valores(resumenes: list[Resumen], enfoque: str, magnitud: str) -> dict[str, Decimal]:
    return {
        r.caso: getattr(r, magnitud)
        for r in resumenes
        if r.enfoque == enfoque and r.caso != "todos"
    }


def main() -> None:
    """Imprime la tabla por caso y enfoque, y las comparaciones caso a caso."""
    mediciones = []
    for archivo in sorted((RESULTADOS / "referencia").glob("*.json")):
        if archivo.name == "oraculo.json":
            continue
        referencia = json.loads(archivo.read_text("utf-8"))
        medir = medir_sistema if referencia["enfoque"] == "sistema" else medir_linea_base
        mediciones.append(medir(referencia))
    resumenes = agrupar(mediciones)
    print("| Caso | Enfoque | Corridas | Máquina (min) | Inferencia (USD) | Referencia | Errores |")
    print("|---|---|---|---|---|---|---|")
    for r in resumenes:
        print(
            f"| {r.caso.removeprefix('caso-ampliada-')} | {NOMBRES[r.enfoque]} | {r.corridas} | "
            f"{r.tiempo_maquina_min:.1f} | {r.inferencia_usd:.3f} | {r.pasan} de {r.total} | "
            f"{r.tasa_errores * 100:.1f} % |"
        )
    print("\n| Sistema frente a | Magnitud | Mayor en | Menor en | Empates | Valor p |")
    print("|---|---|---|---|---|---|")
    for enfoque in ("modelo_unico", "un_prompt"):
        for magnitud, nombre in (
            ("inferencia_usd", "Costo"),
            ("tiempo_maquina_min", "Tiempo"),
            ("tasa_errores", "Errores"),
        ):
            c = comparar_por_caso(
                _valores(resumenes, "sistema", magnitud), _valores(resumenes, enfoque, magnitud)
            )
            print(
                f"| {NOMBRES[enfoque]} | {nombre} | {c.mayor} | {c.menor} | {c.empates} | "
                f"{c.valor_p:.3f} |"
            )


if __name__ == "__main__":
    main()
