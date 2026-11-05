"""Adaptador de modelo-unico-07-1: corre el lote y traduce sus estados y su diferencia.

El rechazo de un archivo llega como una incidencia de lectura, sin fila: se convierte en excepción.
La diferencia llega como texto, «faltan 20000» o «sobran 20000»: se toma su número.
"""

import re
from dataclasses import asdict

from conciliacion.lote import Entrada, Lote

ESTADOS = {
    "conciliada": "conciliado",
    "con_diferencia": "diferencia",
    "pago_sin_factura": "pago sin factura",
}


def conciliar(
    banco_a: str, banco_b: str, banco_c: str, facturas: str, carpeta_salida: str
) -> tuple[list[dict[str, str]], dict[str, int]]:
    lote = Lote(
        [
            Entrada("A", banco_a),
            Entrada("B", banco_b),
            Entrada("C", banco_c),
            Entrada("facturas", facturas),
        ],
        carpeta_salida,
    )
    lote.ejecutar()
    for incidencia in lote.incidencias:
        if incidencia.etapa == "lectura" and incidencia.fila is None:
            raise ValueError(f"{incidencia.archivo}: {incidencia.mensaje}")
    filas = [
        {
            **asdict(detalle),
            "estado": ESTADOS.get(detalle.estado, detalle.estado),
            "diferencia": re.sub(r"[^0-9-]", "", detalle.diferencia),
        }
        for detalle in lote.detalle
    ]
    return filas, {ESTADOS.get(estado, estado): total for estado, total in lote.resumen.items()}
