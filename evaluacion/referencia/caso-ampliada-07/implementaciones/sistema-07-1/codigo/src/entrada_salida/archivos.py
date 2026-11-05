"""Utilidades CSV independientes de las etapas y de la orquestación."""

import csv
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class _RegistroResultado:
    referencia: str
    valor_facturado: Decimal | None
    valor_pagado: Decimal | None
    banco: str | None
    estado: str
    diferencia: Decimal


RegistroResultado = _RegistroResultado


def _generar(
    path: str,
    filas: list[tuple[str, str, str]],
    cabecera: tuple[str, str, str],
    separador: str,
) -> None:
    with open(path, "w", encoding="utf-8", newline="") as archivo:
        escritor = csv.writer(archivo, delimiter=separador)
        escritor.writerow(cabecera)
        escritor.writerows(filas)


def generar_csv_banco_a(path: str, pagos: list[tuple[str, str, str]]) -> None:
    """Crea un CSV de Banco A.

    Args:
        path: Ruta de salida.
        pagos: Tuplas de referencia, valor textual y fecha AAAA-MM-DD.

    Raises:
        OSError: Si no se puede escribir el archivo.
    """
    _generar(path, pagos, ("referencia", "valor", "fecha"), ";")


def generar_csv_banco_b(path: str, pagos: list[tuple[str, str, str]]) -> None:
    """Crea un CSV de Banco B.

    Args:
        path: Ruta de salida.
        pagos: Tuplas de referencia, valor textual y fecha DD/MM/AAAA.

    Raises:
        OSError: Si no se puede escribir el archivo.
    """
    _generar(path, pagos, ("REF", "MONTO", "FECHA_PAGO"), ",")


def generar_csv_banco_c(path: str, pagos: list[tuple[str, str, str]]) -> None:
    """Crea un CSV de Banco C.

    Args:
        path: Ruta de salida.
        pagos: Tuplas de referencia, valor textual y fecha AAAA/MM/DD.

    Raises:
        OSError: Si no se puede escribir el archivo.
    """
    _generar(path, pagos, ("referencia_factura", "valor_pagado", "fecha"), ",")


def generar_csv_facturas(path: str, facturas: list[tuple[str, str, str]]) -> None:
    """Crea un CSV de facturas emitidas.

    Args:
        path: Ruta de salida.
        facturas: Tuplas de referencia, valor textual entero y vencimiento AAAA-MM-DD.

    Raises:
        OSError: Si no se puede escribir el archivo.
    """
    _generar(path, facturas, ("referencia", "valor", "vencimiento"), ",")


def leer_csv_resultados(path: str) -> list[RegistroResultado]:
    """Lee filas tipadas del CSV de resultados.

    Args:
        path: Ruta del CSV generado por la escritura.

    Returns:
        Registros estructurales con importes Decimal y campos ausentes como None.

    Raises:
        OSError: Si no se puede leer el archivo.
        ValueError: Si el CSV no tiene las columnas requeridas.
        ArithmeticError: Si un importe no puede convertirse a Decimal.
    """
    columnas = ("referencia", "valor facturado", "valor pagado", "banco", "estado", "diferencia")
    with open(path, encoding="utf-8-sig", newline="") as archivo:
        lector = csv.DictReader(archivo)
        if any(columna not in (lector.fieldnames or []) for columna in columnas):
            raise ValueError("El CSV de resultados no contiene las columnas requeridas.")
        return [
            _RegistroResultado(
                fila["referencia"],
                Decimal(fila["valor facturado"]) if fila["valor facturado"] else None,
                Decimal(fila["valor pagado"]) if fila["valor pagado"] else None,
                fila["banco"] or None,
                fila["estado"],
                Decimal(fila["diferencia"]),
            )
            for fila in lector
        ]


def escribir_texto(path: str, contenido: str) -> None:
    """Escribe un contenido textual exacto en UTF-8.

    Args:
        path: Ruta de salida.
        contenido: Texto que se escribirá sin transformar sus saltos de línea.

    Raises:
        OSError: Si no se puede escribir el archivo.
    """
    with open(path, "w", encoding="utf-8", newline="") as archivo:
        archivo.write(contenido)
