"""Escritura del CSV de resultados con importes enteros."""

import csv
from decimal import ROUND_HALF_EVEN, Decimal, localcontext

from contratos.esquemas import ResultadoConciliacion


class EscrituraError(OSError):
    """Error al escribir el archivo de resultados.

    Args:
        mensaje: Descripción del error.
    """

    def __init__(self, mensaje: str) -> None:
        """Inicializa el error de escritura."""
        super().__init__(mensaje)


def _importe(valor: Decimal | None) -> str:
    if valor is None:
        return ""
    with localcontext() as contexto:
        contexto.prec = max(28, len(valor.as_tuple().digits) + abs(valor.as_tuple().exponent) + 1)
        return str(valor.quantize(Decimal(1), rounding=ROUND_HALF_EVEN))


def escribir_resultados(resultado: ResultadoConciliacion, destino_csv: str) -> None:
    """Escribe las filas de resultado en un CSV separado por comas.

    Args:
        resultado: Filas y resumen del procesamiento.
        destino_csv: Ruta del archivo que se creará o reemplazará.

    Raises:
        EscrituraError: Si no se puede escribir el archivo.
    """
    try:
        with open(destino_csv, "w", encoding="utf-8", newline="") as archivo:
            escritor = csv.writer(archivo)
            escritor.writerow(
                ("referencia", "valor facturado", "valor pagado", "banco", "estado", "diferencia")
            )
            for registro in resultado.registros:
                escritor.writerow(
                    (
                        registro.referencia,
                        _importe(registro.valor_facturado),
                        _importe(registro.valor_pagado),
                        registro.banco or "",
                        registro.estado,
                        _importe(registro.diferencia),
                    )
                )
    except (OSError, csv.Error) as error:
        raise EscrituraError(f"No se pudo escribir el archivo {destino_csv}: {error}") from error
