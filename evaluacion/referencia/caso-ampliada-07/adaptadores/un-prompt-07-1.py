"""Adaptador de un-prompt-07-1: corre el lote y entrega sus resultados como texto."""

from pathlib import Path

from conciliacion import Archivos, Lote


def conciliar(
    banco_a: str, banco_b: str, banco_c: str, facturas: str, carpeta_salida: str
) -> tuple[list[dict[str, str]], dict[str, int]]:
    archivos = Archivos(Path(banco_a), Path(banco_b), Path(banco_c), Path(facturas))
    informe = Lote(archivos, Path(f"{carpeta_salida}/resultados.csv")).ejecutar()
    filas = [
        {
            "referencia": r.referencia,
            "valor_facturado": str(r.valor_facturado),
            "valor_pagado": str(r.valor_pagado),
            "banco": r.banco,
            "estado": r.estado,
            "diferencia": str(r.diferencia),
        }
        for r in informe.resultados
    ]
    return filas, dict(informe.resumen)
