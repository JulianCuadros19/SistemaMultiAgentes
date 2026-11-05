"""Implementación de control del caso 16, para validar las pruebas de referencia (ADR-0019).

No participa en la comparación: sirve para comprobar que las pruebas pasan con una implementación
que sigue la ficha y fallan con cada mutante de `mutantes.json`. Expone directamente la interfaz de
referencia, así que hace también de adaptador.
"""

import csv
from decimal import ROUND_HALF_UP, Decimal


def _validar(monto: int, plazo_meses: int, tasa_efectiva_anual: Decimal) -> None:
    if not 10_000_000 <= monto <= 500_000_000:
        raise ValueError("El monto debe estar entre 10.000.000 y 500.000.000 pesos")
    if not 12 <= plazo_meses <= 240:
        raise ValueError("El plazo debe estar entre 12 y 240 meses")
    if not Decimal(1) <= tasa_efectiva_anual <= Decimal(30):
        raise ValueError("La tasa efectiva anual debe estar entre 1 y 30")


def _al_peso(valor: Decimal) -> int:
    return int(valor.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _tasa_mensual(tasa_efectiva_anual: Decimal) -> Decimal:
    return (1 + tasa_efectiva_anual / 100) ** (Decimal(1) / 12) - 1


def cuota(monto: int, plazo_meses: int, tasa_efectiva_anual: Decimal) -> int:
    """Cuota mensual fija."""
    _validar(monto, plazo_meses, tasa_efectiva_anual)
    tasa = _tasa_mensual(tasa_efectiva_anual)
    return _al_peso(Decimal(monto) * tasa / (1 - (1 + tasa) ** -plazo_meses))


def tabla(
    monto: int, plazo_meses: int, tasa_efectiva_anual: Decimal
) -> list[tuple[int, int, int, int]]:
    """Cuota, interés, abono y saldo de cada mes."""
    valor = cuota(monto, plazo_meses, tasa_efectiva_anual)
    tasa = _tasa_mensual(tasa_efectiva_anual)
    saldo, filas = monto, []
    for mes in range(1, plazo_meses + 1):
        interes = _al_peso(Decimal(saldo) * tasa)
        pago = valor if mes < plazo_meses else saldo + interes
        abono = pago - interes
        saldo -= abono
        filas.append((pago, interes, abono, saldo))
    return filas


def resumen(monto: int, plazo_meses: int, tasa_efectiva_anual: Decimal) -> tuple[int, int]:
    """Total pagado y total de intereses."""
    total = sum(fila[0] for fila in tabla(monto, plazo_meses, tasa_efectiva_anual))
    return total, total - monto


def guardar_tabla_csv(
    monto: int, plazo_meses: int, tasa_efectiva_anual: Decimal, ruta: str
) -> None:
    """Guarda la tabla en un CSV."""
    with open(ruta, "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(["mes", "cuota", "interes", "abono", "saldo"])
        for mes, fila in enumerate(tabla(monto, plazo_meses, tasa_efectiva_anual), start=1):
            escritor.writerow([mes, *fila])


def codigo_de_salida(
    operacion: str, monto: str, plazo_meses: str, tasa_efectiva_anual: str
) -> int:
    """Código de salida de la herramienta con esa operación y esos datos."""
    operaciones = {"cuota": cuota, "tabla": tabla, "resumen": resumen}
    try:
        operaciones[operacion](int(monto), int(plazo_meses), Decimal(tasa_efectiva_anual))
    except (ValueError, ArithmeticError, KeyError):
        return 1
    return 0
