"""Exportación de filas de amortización sin dependencias entre capas."""

import csv
from pathlib import Path
from typing import Any as AmortizacionFila


class TablaCSV:
    """Escritor de tablas de amortización en CSV.

    Args:
        delimitador: Carácter separador de columnas; por defecto, una coma.
    """

    def __init__(self, delimitador: str = ",") -> None:
        """Configure el separador del archivo CSV.

        Args:
            delimitador: Carácter separador de columnas.
        """
        self.delimitador = delimitador

    def guardar(self, tabla: list[AmortizacionFila], ruta: str) -> None:
        """Escriba la tabla completa, con encabezado, en UTF-8.

        Args:
            tabla: Filas con los seis atributos del modelo de amortización.
            ruta: Ruta del archivo que se creará o reemplazará.
        """
        with Path(ruta).open("w", encoding="utf-8", newline="") as archivo:
            escritor = csv.writer(archivo, delimiter=self.delimitador)
            escritor.writerow(
                ["mes", "saldo_inicial", "interes", "abono_capital", "cuota", "saldo_final"]
            )
            escritor.writerows(
                (
                    fila.mes,
                    fila.saldo_inicial,
                    fila.interes,
                    fila.abono_capital,
                    fila.cuota,
                    fila.saldo_final,
                )
                for fila in tabla
            )

    def existe(self, ruta: str) -> bool:
        """Compruebe si una ruta corresponde a un archivo existente.

        Args:
            ruta: Ruta que se desea consultar.

        Returns:
            True si existe un archivo en la ruta indicada.
        """
        return Path(ruta).is_file()
