"""Conciliación de pagos por referencia y cálculo de totales."""

import re
from decimal import Decimal

from contratos.esquemas import (
    DatosNormalizados,
    RegistroResultado,
    ResultadoConciliacion,
    Resumen,
)


def conciliar_lotes(datos: DatosNormalizados) -> ResultadoConciliacion:
    """Cruza los pagos válidos con las facturas sin interrumpir el lote.

    Args:
        datos: Pagos normalizados y facturas emitidas.

    Returns:
        Filas de resultado y totales; los pagos de valor inválido se omiten.
    """
    facturas = {factura.referencia: factura for factura in datos.facturas}
    referencias_pagadas: set[str] = set()
    registros = []
    totales = {"conciliado": 0, "diferencia": 0, "pago sin factura": 0, "pendiente": 0}
    for pago in datos.pagos:
        texto = pago.valor_str.strip()
        if re.fullmatch(r"[+-]?[0-9]+", texto) is None:
            continue
        valor = Decimal(texto)
        factura = facturas.get(pago.referencia)
        diferencia = Decimal(0)
        valor_facturado = None
        estado = "pago sin factura"
        if factura is not None:
            referencias_pagadas.add(pago.referencia)
            valor_facturado = factura.valor
            diferencia = valor - factura.valor
            estado = "conciliado" if diferencia == 0 else "diferencia"
        registros.append(
            RegistroResultado(
                pago.referencia, valor_facturado, valor, pago.banco, estado, diferencia
            )
        )
        totales[estado] += 1
    for factura in facturas.values():
        if factura.referencia not in referencias_pagadas:
            registros.append(
                RegistroResultado(
                    factura.referencia, factura.valor, None, None, "pendiente", Decimal(0)
                )
            )
            totales["pendiente"] += 1
    resumen = Resumen(
        totales["conciliado"],
        totales["diferencia"],
        totales["pago sin factura"],
        totales["pendiente"],
    )
    return ResultadoConciliacion(registros, resumen)
