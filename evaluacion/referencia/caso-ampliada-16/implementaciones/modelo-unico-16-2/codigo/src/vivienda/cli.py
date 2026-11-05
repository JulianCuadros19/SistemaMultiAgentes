"""Interfaz interactiva para los asesores."""

import sys

from vivienda.calculo import Resultado, calcular, guardar_csv


def mostrar(resultado: Resultado) -> None:
    """Muestre cuota, todas las filas y totales en pesos sin decimales."""
    print(f"Cuota mensual fija (pesos): {resultado.cuota_mensual}")
    print("La última cuota se ajusta para cancelar el saldo.")
    print("Mes | Cuota | Interés | Abono a capital | Saldo (pesos)")
    for fila in resultado.tabla:
        print(
            f"{fila.mes} | {fila.cuota} | {fila.interes} | "
            f"{fila.abono_capital} | {fila.saldo}"
        )
    print(f"Total pagado (pesos): {resultado.total_pagado}")
    print(f"Total intereses (pesos): {resultado.total_intereses}")


def _exportar(resultado: Resultado) -> int:
    respuesta = input("¿Guardar la tabla en CSV? [s/n; Enter = no]: ").strip().lower()
    if respuesta in {"", "n", "no"}:
        return 0
    if respuesta not in {"s", "si", "sí"}:
        raise ValueError("Respuesta inválida: use s para sí o n para no.")
    ruta = input("Nombre o ruta del archivo CSV: ").strip()
    try:
        if not ruta:
            raise ValueError("Ruta vacía.")
        guardar_csv(resultado, ruta)
    except (OSError, UnicodeError, ValueError):
        print("No se pudo guardar el CSV", file=sys.stderr)
        return 1
    print(f"CSV guardado en: {ruta}")
    return 0


def main() -> int:
    """Ejecute la atención interactiva y devuelva cero o un código de error."""
    print("Crédito de vivienda: importes en pesos, sin seguros ni comisiones.")
    print("Redondeo provisional: al peso más cercano; empates al par (ver USO.md).")
    try:
        monto = input("Monto en pesos sin puntos ni comas (10000000 a 500000000): ")
        plazo = input("Plazo en meses enteros (12 a 240): ")
        tasa = input("Tasa efectiva anual sin % (1 a 30; ejemplo: 12 o 12.50): ")
        resultado = calcular(monto, plazo, tasa)
        mostrar(resultado)
        return _exportar(resultado)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    except EOFError:
        print("Entrada incompleta: no se recibieron todos los datos.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Operación cancelada.", file=sys.stderr)
        return 1
