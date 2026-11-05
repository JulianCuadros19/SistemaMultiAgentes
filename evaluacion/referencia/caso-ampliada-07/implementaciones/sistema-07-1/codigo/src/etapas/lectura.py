"""Lectura de CSV bancarios y de facturas emitidas."""

import csv
import re
from datetime import date
from decimal import Decimal

from contratos.esquemas import DatosLeidos, Factura, PagoEntrada


class ColumnaFaltante(ValueError):
    """Error de cabecera de un archivo.

    Args:
        archivo: Ruta del archivo rechazado.
        columna: Nombre de la columna ausente.
    """

    def __init__(self, archivo: str, columna: str) -> None:
        """Conserva el archivo y la columna que originaron el error."""
        self.archivo = archivo
        self.columna = columna
        super().__init__(f"El archivo {archivo} no contiene la columna {columna}.")


def _leer(path: str, separador: str, columnas: tuple[str, ...]) -> list[dict[str, str]]:
    with open(path, encoding="utf-8-sig", newline="") as archivo:
        lector = csv.DictReader(archivo, delimiter=separador)
        cabecera = lector.fieldnames or []
        for columna in columnas:
            if columna not in cabecera:
                raise ColumnaFaltante(path, columna)
        filas = []
        for fila in lector:
            if None in fila or any(fila[columna] is None for columna in columnas):
                raise ValueError(f"El archivo {path} contiene una fila incompleta o excedida.")
            filas.append({columna: fila[columna] for columna in columnas})
        return filas


def _pagos(
    path: str, banco: str, separador: str, columnas: tuple[str, str, str]
) -> list[PagoEntrada]:
    return [
        PagoEntrada(fila[columnas[0]], fila[columnas[1]], fila[columnas[2]], banco)
        for fila in _leer(path, separador, columnas)
    ]


def _facturas(path: str) -> list[Factura]:
    facturas = []
    for fila in _leer(path, ",", ("referencia", "valor", "vencimiento")):
        valor = fila["valor"].strip()
        if re.fullmatch(r"[+-]?[0-9]+", valor) is None:
            continue
        fecha = fila["vencimiento"]
        if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", fecha) is None:
            raise ValueError("El vencimiento debe tener formato AAAA-MM-DD.")
        facturas.append(Factura(fila["referencia"], Decimal(valor), date.fromisoformat(fecha)))
    return facturas


def leer_archivos(
    pagos_banco_a: str,
    pagos_banco_b: str,
    pagos_banco_c: str,
    facturas_emitidas: str,
) -> DatosLeidos:
    """Lee los cuatro archivos respetando sus formatos.

    Args:
        pagos_banco_a: Ruta del CSV de Banco A.
        pagos_banco_b: Ruta del CSV de Banco B.
        pagos_banco_c: Ruta del CSV de Banco C.
        facturas_emitidas: Ruta del CSV de facturas.

    Returns:
        Pagos textuales y facturas tipadas.

    Raises:
        ColumnaFaltante: Si falta una cabecera requerida.
        OSError: Si un archivo no puede leerse.
        ValueError: Si una fila tiene estructura, referencia o vencimiento inválidos.
    """
    pagos = _pagos(pagos_banco_a, "A", ";", ("referencia", "valor", "fecha"))
    pagos.extend(_pagos(pagos_banco_b, "B", ",", ("REF", "MONTO", "FECHA_PAGO")))
    pagos.extend(
        _pagos(pagos_banco_c, "C", ",", ("referencia_factura", "valor_pagado", "fecha"))
    )
    return DatosLeidos(pagos, _facturas(facturas_emitidas))
