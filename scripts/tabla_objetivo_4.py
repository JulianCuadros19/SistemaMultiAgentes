"""Tabla comparativa del objetivo 4: sistema, modelo único e implementación manual (ADR-0019).

Se regenera sin costo desde los resultados guardados:
- las verificaciones de referencia, de `evaluacion/resultados/paso-15/referencia/`;
- el tiempo y el costo del sistema, de los resultados de cada corrida;
- los del modelo único, de su `resultado.json`;
- las horas de la implementación manual, de `evaluacion/manual/<caso>/tiempos.csv`;
- la revisión humana, de `evaluacion/resultados/paso-15/revision-humana/tiempos.json`, con los
  segundos de reloj, del sistema y del cliente simulado de cada caso, y su costo, de la traza.

Uso:
    python scripts/tabla_objetivo_4.py
"""

import json
from decimal import Decimal
from pathlib import Path

from multiagente.evaluacion.comparacion import (
    TARIFAS_USD_POR_HORA,
    Medicion,
    agrupar,
    costo_total,
    minutos_de_tiempos,
)

RAIZ = Path(__file__).resolve().parents[1]
RESULTADOS = RAIZ / "evaluacion" / "resultados" / "paso-15"
CORRIDAS_DEL_SISTEMA = ("corrida-ampliada", "sistema-2")
TRAZA_HUMANA = RAIZ / "docs" / "mediciones" / "paso-11-extremo-a-extremo.jsonl"
SEGUNDOS_POR_HORA = Decimal(3600)
SEGUNDOS_POR_MINUTO = Decimal(60)
MINUTOS_POR_HORA = Decimal(60)


def _sin_cliente(caso: dict[str, object]) -> Decimal:
    return Decimal(str(caso["costo_sistema"]))


def medir_sistema(referencia: dict[str, object]) -> Medicion:
    """Mide una corrida automática del sistema: sin horas-persona."""
    etiqueta = str(referencia["etiqueta"])
    orden = int(etiqueta.rsplit("-", 1)[-1])
    caso = json.loads(
        (RESULTADOS / CORRIDAS_DEL_SISTEMA[orden - 1] / f"{referencia['caso']}.json").read_text(
            encoding="utf-8"
        )
    )
    return Medicion(
        caso=str(referencia["caso"]),
        enfoque="sistema",
        etiqueta=etiqueta,
        tiempo_maquina_min=Decimal(str(caso["tiempo_sistema_min"])),
        horas_persona=Decimal(0),
        inferencia_usd=_sin_cliente(caso),
        pasan=int(referencia["pasan"]),
        total=int(referencia["total"]),
    )


def medir_sistema_humano(referencia: dict[str, object]) -> Medicion:
    """Mide una corrida con revisión humana: las horas son la espera por la persona."""
    tiempos = json.loads((RESULTADOS / "revision-humana" / "tiempos.json").read_text("utf-8"))
    sesiones = json.loads((RESULTADOS / "revision-humana" / "sesiones.json").read_text("utf-8"))
    caso = str(referencia["caso"])
    medidos = tiempos[caso]
    espera = (
        Decimal(str(medidos["reloj_s"]))
        - Decimal(str(medidos["sistema_s"]))
        - Decimal(str(medidos["cliente_s"]))
    )
    inferencia = Decimal(0)
    for linea in TRAZA_HUMANA.read_text("utf-8").splitlines():
        llamada = json.loads(linea)
        if llamada.get("sesion") == sesiones[caso] and llamada["nodo"] != "cliente_simulado":
            inferencia += Decimal(llamada["costo_usd"])
    return Medicion(
        caso=caso,
        enfoque="sistema_humano",
        etiqueta=str(referencia["etiqueta"]),
        tiempo_maquina_min=Decimal(str(medidos["sistema_s"])) / SEGUNDOS_POR_MINUTO,
        horas_persona=espera / SEGUNDOS_POR_HORA,
        inferencia_usd=inferencia,
        pasan=int(referencia["pasan"]),
        total=int(referencia["total"]),
    )


def medir_modelo_unico(referencia: dict[str, object]) -> Medicion:
    """Mide una corrida del modelo único: sin horas-persona."""
    etiqueta = str(referencia["etiqueta"])
    corrida = etiqueta.rsplit("-", 1)[-1]
    datos = json.loads(
        (
            RESULTADOS
            / "modelo-unico"
            / str(referencia["caso"])
            / f"corrida-{corrida}"
            / "resultado.json"
        ).read_text("utf-8")
    )
    segundos = Decimal(str(datos["tiempo_total_s"])) - Decimal(str(datos["tiempo_cliente_s"]))
    return Medicion(
        caso=str(referencia["caso"]),
        enfoque="modelo_unico",
        etiqueta=etiqueta,
        tiempo_maquina_min=segundos / SEGUNDOS_POR_MINUTO,
        horas_persona=Decimal(0),
        inferencia_usd=Decimal(str(datos["costo_modelo_usd"])),
        pasan=int(referencia["pasan"]),
        total=int(referencia["total"]),
    )


def medir_manual(referencia: dict[str, object]) -> Medicion:
    """Mide una implementación manual: sin cómputo ni inferencia."""
    caso = str(referencia["caso"])
    tiempos = (RAIZ / "evaluacion" / "manual" / caso / "tiempos.csv").read_text("utf-8")
    return Medicion(
        caso=caso,
        enfoque="manual",
        etiqueta=str(referencia["etiqueta"]),
        tiempo_maquina_min=Decimal(0),
        horas_persona=minutos_de_tiempos(tiempos) / MINUTOS_POR_HORA,
        inferencia_usd=Decimal(0),
        pasan=int(referencia["pasan"]),
        total=int(referencia["total"]),
    )


MEDIDORES = {
    "sistema": medir_sistema,
    "sistema_humano": medir_sistema_humano,
    "modelo_unico": medir_modelo_unico,
    "manual": medir_manual,
}


def main() -> None:
    """Imprime la tabla por caso y enfoque, y la sensibilidad a la tarifa."""
    mediciones = []
    for archivo in sorted((RESULTADOS / "referencia").glob("*.json")):
        if archivo.name == "oraculo.json":
            continue
        referencia = json.loads(archivo.read_text("utf-8"))
        mediciones.append(MEDIDORES[referencia["enfoque"]](referencia))
    columnas_tarifa = " | ".join(f"Costo a {t} USD/h" for t in TARIFAS_USD_POR_HORA)
    print(
        "| Caso | Enfoque | Corridas | Máquina (min) | Horas-persona | Inferencia (USD) | "
        f"{columnas_tarifa} | Referencia | Tasa de errores |"
    )
    print("|---|---|---|---|---|---|" + "---|" * len(TARIFAS_USD_POR_HORA) + "---|---|")
    for r in agrupar(mediciones):
        costos = " | ".join(
            f"{costo_total(r.inferencia_usd, r.horas_persona, t):.2f}" for t in TARIFAS_USD_POR_HORA
        )
        print(
            f"| {r.caso} | {r.enfoque} | {r.corridas} | {r.tiempo_maquina_min:.1f} | "
            f"{r.horas_persona:.2f} | {r.inferencia_usd:.3f} | {costos} | "
            f"{r.pasan} de {r.total} | {r.tasa_errores:.3f} |"
        )


if __name__ == "__main__":
    main()
