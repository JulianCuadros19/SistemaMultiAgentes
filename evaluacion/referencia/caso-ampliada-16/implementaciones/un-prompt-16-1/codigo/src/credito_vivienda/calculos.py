"""Validación, amortización y exportación de créditos de vivienda."""

import csv
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from pathlib import Path

_CONTEXTO = Context(prec=60, rounding=ROUND_HALF_UP)
_PESO = Decimal(1)


def _decimal(valor: str | int | Decimal, nombre: str) -> Decimal:
    try:
        resultado = Decimal(str(valor))
    except (InvalidOperation, ValueError) as error:
        raise ValueError(f"{nombre}: debe ser un número decimal válido.") from error
    if not resultado.is_finite():
        raise ValueError(f"{nombre}: debe ser un número finito.")
    return resultado


@dataclass(frozen=True)
class Credito:
    """Contiene datos validados; monto en pesos y tasa anual en porcentaje."""

    monto: Decimal
    plazo: int
    tasa_anual: Decimal

    def __post_init__(self) -> None:
        """Valida los límites y redondea el monto inicial al peso."""
        monto = _decimal(self.monto, "Monto")
        tasa = _decimal(self.tasa_anual, "Tasa efectiva anual")
        if not Decimal(10_000_000) <= monto <= Decimal(500_000_000):
            raise ValueError("Monto: debe estar entre 10000000 y 500000000 pesos.")
        if type(self.plazo) is not int or not 12 <= self.plazo <= 240:
            raise ValueError("Plazo: debe ser un entero entre 12 y 240 meses.")
        if not Decimal(1) <= tasa <= Decimal(30):
            raise ValueError("Tasa efectiva anual: debe estar entre 1 y 30 por ciento.")
        if tasa.as_tuple().exponent < -2:
            raise ValueError("Tasa efectiva anual: admite hasta dos decimales.")
        with localcontext(_CONTEXTO):
            object.__setattr__(self, "monto", monto.quantize(_PESO))
        object.__setattr__(self, "tasa_anual", tasa)


@dataclass(frozen=True)
class Fila:
    """Representa un mes de amortización, con importes enteros en pesos."""

    mes: int
    cuota: int
    interes: int
    abono_capital: int
    saldo: int


@dataclass(frozen=True)
class Resumen:
    """Contiene las sumas efectivamente pagadas según la tabla."""

    total_pagado: int
    total_intereses: int


def crear_credito(
    monto: str | int | Decimal,
    plazo: int,
    tasa_anual: str | int | Decimal,
) -> Credito:
    """Crea un crédito desde números decimales o texto; rechaza datos inválidos."""
    return Credito(
        monto=_decimal(monto, "Monto"),
        plazo=plazo,
        tasa_anual=_decimal(tasa_anual, "Tasa efectiva anual"),
    )


def _tasa_mensual(credito: Credito) -> Decimal:
    return (1 + credito.tasa_anual / 100) ** (Decimal(1) / 12) - 1


def _cuota(credito: Credito, tasa: Decimal) -> int:
    valor = credito.monto * tasa / (1 - (1 + tasa) ** (-credito.plazo))
    return int(valor.quantize(_PESO))


def calcular_cuota(credito: Credito) -> int:
    """Calcula la cuota fija mensual redondeada al peso, antes del ajuste final."""
    with localcontext(_CONTEXTO):
        return _cuota(credito, _tasa_mensual(credito))


def generar_tabla(credito: Credito) -> list[Fila]:
    """Genera todos los meses, ajustando la última cuota para cancelar el saldo."""
    with localcontext(_CONTEXTO):
        tasa = _tasa_mensual(credito)
        cuota_fija = _cuota(credito, tasa)
        saldo = int(credito.monto)
        filas: list[Fila] = []
        for mes in range(1, credito.plazo + 1):
            interes = int((Decimal(saldo) * tasa).quantize(_PESO))
            cuota = saldo + interes if mes == credito.plazo else cuota_fija
            capital = cuota - interes
            saldo -= capital
            filas.append(Fila(mes, cuota, interes, capital, saldo))
        return filas


def calcular_resumen(credito: Credito) -> Resumen:
    """Suma cuotas e intereses de la tabla, incluyendo la cuota final ajustada."""
    filas = generar_tabla(credito)
    return Resumen(
        total_pagado=sum(fila.cuota for fila in filas),
        total_intereses=sum(fila.interes for fila in filas),
    )


def guardar_csv(filas: Sequence[Fila], ruta: str | Path) -> None:
    """Guarda la tabla en CSV UTF-8 con encabezado; propaga errores de escritura."""
    with Path(ruta).open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(["mes", "cuota", "interes", "abono_capital", "saldo"])
        escritor.writerows(
            (fila.mes, fila.cuota, fila.interes, fila.abono_capital, fila.saldo)
            for fila in filas
        )
