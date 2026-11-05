"""Implementación de control del caso 07, para validar las pruebas de referencia (ADR-0019).

No participa en la comparación: sirve para comprobar que las pruebas pasan con una implementación
que sigue la ficha y fallan con cada mutante de `mutantes.json`. Expone directamente la interfaz de
referencia, así que hace también de adaptador.
"""

import csv
from collections import Counter
from pathlib import Path

COLUMNAS = {
    "A": (";", "referencia", "valor"),
    "B": (",", "REF", "MONTO"),
    "C": (",", "referencia_factura", "valor_pagado"),
}


def _leer(ruta: str, separador: str, columnas: tuple[str, ...]) -> list[dict[str, str]]:
    with Path(ruta).open(encoding="utf-8", newline="") as archivo:
        lector = csv.DictReader(archivo, delimiter=separador)
        for columna in columnas:
            if columna not in (lector.fieldnames or ()):
                raise ValueError(f"Al archivo {ruta} le falta la columna {columna}")
        return list(lector)


def _pagos(rutas: dict[str, str]) -> list[tuple[str, int, str]]:
    pagos = []
    for banco, ruta in rutas.items():
        separador, referencia, valor = COLUMNAS[banco]
        for fila in _leer(ruta, separador, (referencia, valor)):
            if fila[valor].strip().isdigit():
                pagos.append((fila[referencia], int(fila[valor]), banco))
    return pagos


def conciliar(
    banco_a: str, banco_b: str, banco_c: str, facturas: str, carpeta_salida: str
) -> tuple[list[dict[str, str]], dict[str, int]]:
    """Corre el proceso con esos archivos y devuelve las filas del CSV y el total de cada estado."""
    pagos = _pagos({"A": banco_a, "B": banco_b, "C": banco_c})
    valores = {
        fila["referencia"]: int(fila["valor"])
        for fila in _leer(facturas, ",", ("referencia", "valor"))
    }
    filas = []
    for referencia, pagado, banco in pagos:
        facturado = valores.get(referencia)
        if facturado is None:
            estado, diferencia = "pago sin factura", 0
        elif facturado == pagado:
            estado, diferencia = "conciliado", 0
        else:
            estado, diferencia = "diferencia", facturado - pagado
        filas.append(
            {
                "referencia": referencia,
                "valor_facturado": "" if facturado is None else str(facturado),
                "valor_pagado": str(pagado),
                "banco": banco,
                "estado": estado,
                "diferencia": str(diferencia),
            }
        )
    con_pago = {referencia for referencia, _, _ in pagos}
    for referencia, facturado in valores.items():
        if referencia not in con_pago:
            filas.append(
                {
                    "referencia": referencia,
                    "valor_facturado": str(facturado),
                    "valor_pagado": "",
                    "banco": "",
                    "estado": "pendiente",
                    "diferencia": "0",
                }
            )
    with (Path(carpeta_salida) / "resultados.csv").open("w", encoding="utf-8", newline="") as salida:
        escritor = csv.DictWriter(salida, fieldnames=list(filas[0]))
        escritor.writeheader()
        escritor.writerows(filas)
    return filas, dict(Counter(fila["estado"] for fila in filas))
