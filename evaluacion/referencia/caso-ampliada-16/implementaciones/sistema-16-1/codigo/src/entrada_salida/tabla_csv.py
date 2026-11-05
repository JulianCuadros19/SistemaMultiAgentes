"""Lectura y escritura explícitas de tablas de amortización en CSV."""

import csv
from dataclasses import dataclass
from pathlib import Path

from dominio.credito import AmortizacionFila


@dataclass
class EscritorTablaCSV:
    """Destino de una tabla de amortización en formato CSV.

    Args:
        ruta_salida: Ruta del archivo de destino.
    """

    ruta_salida: str

    def escribir(self, filas: list[AmortizacionFila]) -> str:
        """Escribe encabezados y filas en el archivo configurado.

        Args:
            filas: Filas de amortización a guardar.

        Returns:
            Ruta del archivo escrito.

        Raises:
            OSError: Si no se puede escribir el archivo.
        """
        with Path(self.ruta_salida).open("w", encoding="utf-8", newline="") as archivo:
            escritor = csv.writer(archivo)
            escritor.writerow(["mes", "cuota", "interes", "abono_capital", "saldo"])
            for fila in filas:
                escritor.writerow(
                    [fila.mes, fila.cuota, fila.interes, fila.abono_capital, fila.saldo]
                )
        return self.ruta_salida

    def existe(self) -> bool:
        """Comprueba si existe el archivo configurado.

        Returns:
            Verdadero si la ruta corresponde a un archivo existente.
        """
        return Path(self.ruta_salida).is_file()

    def leer(self) -> list[str]:
        """Lee las líneas del archivo CSV, sin sus terminadores.

        Returns:
            Líneas de texto del archivo, incluidos los encabezados.

        Raises:
            OSError: Si no se puede leer el archivo.
        """
        return Path(self.ruta_salida).read_text(encoding="utf-8").splitlines()
