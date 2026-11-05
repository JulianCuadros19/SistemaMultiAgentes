"""Normalización de fechas de los tres bancos."""

import re
from datetime import datetime

from contratos.esquemas import DatosLeidos, DatosNormalizados, PagoNormalizado


def normalizar_datos(datos: DatosLeidos) -> DatosNormalizados:
    """Normaliza fechas conservando el valor como texto.

    Args:
        datos: Datos de entrada de los bancos y facturas.

    Returns:
        Pagos con fechas de tipo date y facturas originales.

    Raises:
        ValueError: Si un banco o una fecha no cumple el formato requerido.
    """
    formatos = {
        "A": (r"[0-9]{4}-[0-9]{2}-[0-9]{2}", "%Y-%m-%d"),
        "B": (r"[0-9]{2}/[0-9]{2}/[0-9]{4}", "%d/%m/%Y"),
        "C": (r"[0-9]{4}/[0-9]{2}/[0-9]{2}", "%Y/%m/%d"),
    }
    pagos = []
    for pago in datos.pagos:
        if pago.banco not in formatos:
            raise ValueError("El banco debe ser A, B o C.")
        patron, formato = formatos[pago.banco]
        if re.fullmatch(patron, pago.fecha_str) is None:
            raise ValueError(f"La fecha no cumple el formato del banco {pago.banco}.")
        fecha = datetime.strptime(pago.fecha_str, formato).date()
        pagos.append(PagoNormalizado(pago.referencia, pago.valor_str, fecha, pago.banco))
    return DatosNormalizados(pagos, list(datos.facturas))
