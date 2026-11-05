"""Validación y cálculo monetario con aritmética decimal."""

import csv
import re
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from pathlib import Path


@dataclass(frozen=True)
class Cuota:
    """Fila mensual; todos los importes están en pesos enteros."""

    mes: int
    cuota: int
    interes: int
    abono_capital: int
    saldo: int


@dataclass(frozen=True)
class Resultado:
    """Cuota fija, tasa mensual, tabla y totales del crédito."""

    cuota_mensual: int
    tasa_mensual: Decimal
    tabla: tuple[Cuota, ...]
    total_pagado: int
    total_intereses: int


def _validar(monto: str, plazo: str, tasa: str) -> tuple[int, int, Decimal]:
    monto = monto.strip()
    plazo = plazo.strip()
    tasa = tasa.strip()
    if re.fullmatch(r"[0-9]+", monto) is None or len(monto) > 9:
        raise ValueError("Monto inválido: ingrese pesos enteros sin puntos ni comas.")
    capital = int(monto)
    if not 10_000_000 <= capital <= 500_000_000:
        raise ValueError("Monto fuera de rango: debe estar entre 10000000 y 500000000 pesos.")
    if re.fullmatch(r"[0-9]+", plazo) is None or len(plazo) > 3:
        raise ValueError("Plazo inválido: ingrese un número entero de meses.")
    meses = int(plazo)
    if not 12 <= meses <= 240:
        raise ValueError("Plazo fuera de rango: debe estar entre 12 y 240 meses.")
    if re.fullmatch(r"[0-9]+(?:\.[0-9]{1,2})?", tasa) is None or len(tasa) > 5:
        raise ValueError("Tasa inválida: ingrese un porcentaje sin %, con hasta dos decimales.")
    porcentaje = Decimal(tasa)
    if not Decimal(1) <= porcentaje <= Decimal(30):
        raise ValueError("Tasa fuera de rango: debe estar entre 1 y 30 por ciento.")
    return capital, meses, porcentaje


def _pesos(valor: Decimal) -> int:
    return int(valor.quantize(Decimal(1), rounding=ROUND_HALF_EVEN))


def calcular(monto: str, plazo: str, tasa_anual: str) -> Resultado:
    """Calcule un crédito a partir de los mismos textos que recibe la terminal.

    Args:
        monto: Pesos enteros sin separadores, entre 10000000 y 500000000.
        plazo: Meses enteros, entre 12 y 240.
        tasa_anual: Porcentaje efectivo anual entre 1 y 30, con hasta dos decimales.

    Returns:
        Cuota fija, tasa mensual como fracción, tabla completa y sumas de sus filas.

    Raises:
        ValueError: Si una entrada tiene formato inválido o está fuera de rango.

    Note:
        El criterio preciso de redondeo no fue aprobado por el cliente. La decisión
        provisional aplicada aquí se explica en USO.md.
    """
    capital, meses, porcentaje = _validar(monto, plazo, tasa_anual)
    with localcontext() as contexto:
        contexto.prec = 50
        contexto.rounding = ROUND_HALF_EVEN
        tasa = (Decimal(1) + porcentaje / Decimal(100)) ** (
            Decimal(1) / Decimal(12)
        ) - Decimal(1)
        cuota_fija = _pesos(
            Decimal(capital) * tasa / (Decimal(1) - (Decimal(1) + tasa) ** (-meses))
        )
        saldo = capital
        filas: list[Cuota] = []
        for mes in range(1, meses + 1):
            interes = _pesos(Decimal(saldo) * tasa)
            pago = saldo + interes if mes == meses else cuota_fija
            abono = pago - interes
            saldo -= abono
            filas.append(Cuota(mes, pago, interes, abono, saldo))
        return Resultado(
            cuota_mensual=cuota_fija,
            tasa_mensual=tasa,
            tabla=tuple(filas),
            total_pagado=sum(fila.cuota for fila in filas),
            total_intereses=sum(fila.interes for fila in filas),
        )


def guardar_csv(resultado: Resultado, ruta: str | Path) -> None:
    """Guarde la tabla completa como CSV UTF-8 con encabezado y comas.

    El archivo existente se reemplaza. No se crean directorios. Los errores del
    sistema de archivos se propagan para que el llamador pueda informarlos.
    """
    with Path(ruta).open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(["mes", "cuota", "interes", "abono_capital", "saldo"])
        for fila in resultado.tabla:
            escritor.writerow(
                [fila.mes, fila.cuota, fila.interes, fila.abono_capital, fila.saldo]
            )
