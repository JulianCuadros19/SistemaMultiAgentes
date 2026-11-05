"""Validación y amortización mediante Decimal con precisión interna de 60 dígitos."""

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, localcontext

_PRECISION = 60
_ENTERO = re.compile(r"[0-9]+")
_PORCENTAJE = re.compile(r"[0-9]+(?:\.[0-9]{1,2})?")


class EntradaInvalida(ValueError):
    """Indica que un dato del crédito no cumple los límites o el formato permitido."""


def _entero(valor: str | int, nombre: str, minimo: int, maximo: int) -> int:
    mensaje = (
        f"{nombre}: ingrese un entero entre {minimo} y {maximo}, "
        "sin decimales ni separadores de miles."
    )
    if isinstance(valor, bool) or not isinstance(valor, (str, int)):
        raise EntradaInvalida(mensaje)
    texto = str(valor).strip()
    if not _ENTERO.fullmatch(texto):
        raise EntradaInvalida(mensaje)
    # Decimal evita el límite de conversión de cadenas muy largas a int.
    numero = Decimal(texto)
    if not minimo <= numero <= maximo:
        raise EntradaInvalida(mensaje)
    return int(numero)


def _tasa(valor: str | int | Decimal) -> Decimal:
    mensaje = (
        "Tasa efectiva anual: ingrese un porcentaje entre 1 y 30, "
        "con hasta dos decimales y punto decimal (por ejemplo, 12.50)."
    )
    if isinstance(valor, bool) or not isinstance(valor, (str, int, Decimal)):
        raise EntradaInvalida(mensaje)
    texto = str(valor).strip()
    if not _PORCENTAJE.fullmatch(texto):
        raise EntradaInvalida(mensaje)
    numero = Decimal(texto)
    if not Decimal(1) <= numero <= Decimal(30):
        raise EntradaInvalida(mensaje)
    return numero


@dataclass(frozen=True)
class Credito:
    """Crédito validado: monto entero, meses enteros y tasa anual porcentual."""

    monto: int
    plazo: int
    tasa_anual: Decimal

    def __post_init__(self) -> None:
        """Comprueba los límites también cuando se construye el objeto directamente."""
        object.__setattr__(self, "monto", _entero(self.monto, "Monto", 10_000_000, 500_000_000))
        object.__setattr__(self, "plazo", _entero(self.plazo, "Plazo", 12, 240))
        object.__setattr__(self, "tasa_anual", _tasa(self.tasa_anual))


@dataclass(frozen=True)
class FilaAmortizacion:
    """Mes y valores enteros en pesos de una fila de amortización."""

    mes: int
    cuota: int
    interes: int
    capital: int
    saldo: int


@dataclass(frozen=True)
class Resumen:
    """Suma de las cuotas y de los intereses de la amortización completa."""

    total_pagado: int
    total_intereses: int


def crear_credito(
    monto: str | int,
    plazo: str | int,
    tasa_anual: str | int | Decimal,
) -> Credito:
    """Valida los datos de entrada y devuelve un crédito listo para calcular.

    Args:
        monto: Pesos enteros entre 10000000 y 500000000.
        plazo: Meses enteros entre 12 y 240.
        tasa_anual: Porcentaje entre 1 y 30, con hasta dos decimales.

    Raises:
        EntradaInvalida: Si un dato no cumple el formato o el rango.
    """
    return Credito(
        _entero(monto, "Monto", 10_000_000, 500_000_000),
        _entero(plazo, "Plazo", 12, 240),
        _tasa(tasa_anual),
    )


def tasa_mensual(credito: Credito) -> Decimal:
    """Convierte el porcentaje efectivo anual a una tasa mensual fraccionaria."""
    with localcontext() as contexto:
        contexto.prec = _PRECISION
        contexto.rounding = ROUND_HALF_UP
        anual = credito.tasa_anual / Decimal(100)
        return contexto.power(Decimal(1) + anual, Decimal(1) / Decimal(12)) - Decimal(1)


def _pesos(valor: Decimal) -> int:
    return int(valor.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def cuota_mensual(credito: Credito) -> int:
    """Calcula la cuota fija redondeada al peso; la última cuota puede diferir."""
    with localcontext() as contexto:
        contexto.prec = _PRECISION
        contexto.rounding = ROUND_HALF_UP
        mensual = tasa_mensual(credito)
        denominador = Decimal(1) - (Decimal(1) + mensual) ** (-credito.plazo)
        return _pesos(Decimal(credito.monto) * mensual / denominador)


def amortizacion(credito: Credito) -> tuple[FilaAmortizacion, ...]:
    """Genera todos los meses, redondeando intereses y ajustando la última cuota.

    El saldo se conserva en pesos enteros. En el último mes se paga todo el
    saldo pendiente más el interés de ese mes, dejando el saldo en cero.
    """
    with localcontext() as contexto:
        contexto.prec = _PRECISION
        contexto.rounding = ROUND_HALF_UP
        mensual = tasa_mensual(credito)
        cuota = cuota_mensual(credito)
        saldo = credito.monto
        filas: list[FilaAmortizacion] = []
        for mes in range(1, credito.plazo + 1):
            interes = _pesos(Decimal(saldo) * mensual)
            pago = saldo + interes if mes == credito.plazo else cuota
            capital = pago - interes
            saldo -= capital
            filas.append(FilaAmortizacion(mes, pago, interes, capital, saldo))
        return tuple(filas)


def resumen(credito: Credito) -> Resumen:
    """Devuelve los totales de la tabla, incluida su última cuota ajustada."""
    filas = amortizacion(credito)
    return Resumen(
        total_pagado=sum(fila.cuota for fila in filas),
        total_intereses=sum(fila.interes for fila in filas),
    )
