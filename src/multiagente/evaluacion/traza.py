"""Lo gastado en una traza JSONL de llamadas, para el tope de cada guion del paso 15 (ADR-0019)."""

import json
from decimal import Decimal
from pathlib import Path


def gastado_en_traza(ruta: Path) -> Decimal:
    """Suma el costo de todas las llamadas de una traza JSONL.

    Args:
        ruta: Traza con una llamada por línea, como la que escribe `RegistroJsonl`.

    Returns:
        El costo en USD, cero si la traza todavía no existe.
    """
    if not ruta.exists():
        return Decimal(0)
    return sum(
        (
            Decimal(json.loads(linea)["costo_usd"])
            for linea in ruta.read_text(encoding="utf-8").splitlines()
            if linea.strip()
        ),
        Decimal(0),
    )
