"""Validación de entradas y cálculo monetario exacto del reajuste."""

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation, localcontext
from typing import TypeAlias

_Numero: TypeAlias = Decimal | int | str
_Fecha: TypeAlias = date | str

_PLAZO = "El contrato aún no cumple doce meses desde el último reajuste"


class ErrorReajuste(ValueError):
    """Indica que los datos no permiten calcular el reajuste."""


@dataclass(frozen=True)
class ResultadoReajuste:
    """Resultado con porcentaje aplicado y valores monetarios en pesos.

    Attributes:
        porcentaje_aplicado: Porcentaje elegido antes del redondeo monetario.
        nuevo_canon: Canon resultante, expresado como Decimal.
        incremento: Diferencia entre el nuevo canon y el canon actual.
    """

    porcentaje_aplicado: Decimal
    nuevo_canon: Decimal
    incremento: Decimal


def _numero(valor: _Numero | None, nombre: str) -> Decimal:
    if valor is None:
        raise ErrorReajuste(f"Falta el dato obligatorio: {nombre}")
    if isinstance(valor, bool) or not isinstance(valor, (Decimal, int, str)):
        raise ErrorReajuste(f"Dato inválido: {nombre}")
    try:
        resultado = Decimal(valor)
    except (InvalidOperation, ValueError) as exc:
        raise ErrorReajuste(f"Dato inválido: {nombre}") from exc
    if not resultado.is_finite():
        raise ErrorReajuste(f"Dato inválido: {nombre}")
    return resultado


def _porcentaje(valor: _Numero | None, nombre: str) -> Decimal:
    resultado = _numero(valor, nombre)
    partes = resultado.as_tuple()
    exponente = int(partes.exponent)
    if exponente < -2 and any(partes.digits[exponente + 2 :]):
        raise ErrorReajuste(f"El {nombre} debe tener como máximo dos decimales")
    return resultado


def _fecha(valor: _Fecha | None, nombre: str) -> date:
    if valor is None:
        raise ErrorReajuste(f"Falta el dato obligatorio: {nombre}")
    if isinstance(valor, datetime):
        raise ErrorReajuste(f"Dato inválido: {nombre}")
    if isinstance(valor, date):
        return valor
    if not isinstance(valor, str):
        raise ErrorReajuste(f"Dato inválido: {nombre}")
    try:
        resultado = date.fromisoformat(valor)
    except ValueError as exc:
        raise ErrorReajuste(f"Dato inválido: {nombre}") from exc
    if resultado.isoformat() != valor:
        raise ErrorReajuste(f"Dato inválido: {nombre}")
    return resultado


def _validar_plazo(referencia: date, reajuste: date) -> None:
    if referencia.year == date.max.year:
        raise ErrorReajuste(_PLAZO)
    siguiente_anio = referencia.year + 1
    ultimo_dia = monthrange(siguiente_anio, referencia.month)[1]
    aniversario = date(siguiente_anio, referencia.month, min(referencia.day, ultimo_dia))
    if reajuste < aniversario:
        raise ErrorReajuste(_PLAZO)


def _calcular_importes(canon: Decimal, aplicado: Decimal) -> tuple[Decimal, Decimal]:
    # La precisión depende de las entradas, no del contexto Decimal del llamador.
    precision = sum(
        len(valor.as_tuple().digits) + abs(int(valor.as_tuple().exponent))
        for valor in (canon, aplicado)
    ) + 20
    with localcontext() as contexto:
        contexto.prec = max(28, precision)
        contexto.rounding = ROUND_HALF_UP
        contexto.Emax = max(contexto.Emax, canon.adjusted() + 10)
        contexto.Emin = min(contexto.Emin, canon.adjusted() - precision)
        sin_redondear = canon * (Decimal(1) + aplicado / Decimal(100))
        nuevo = sin_redondear.quantize(Decimal("1E2"), rounding=ROUND_HALF_UP)
        incremento = nuevo - canon
    return nuevo, incremento


def calcular_reajuste(
    canon_actual: _Numero | None = None,
    porcentaje_pactado: _Numero | None = None,
    ipc_anterior: _Numero | None = None,
    fecha_referencia: _Fecha | None = None,
    fecha_reajuste: _Fecha | None = None,
) -> ResultadoReajuste:
    """Calcule el reajuste de un contrato después de al menos doce meses.

    Args:
        canon_actual: Canon positivo en pesos, como Decimal, entero o texto decimal.
        porcentaje_pactado: Porcentaje entre 0 y 100, con hasta dos decimales.
        ipc_anterior: IPC del año calendario anterior, con hasta dos decimales.
        fecha_referencia: Inicio o último reajuste; date o texto AAAA-MM-DD.
        fecha_reajuste: Fecha del nuevo reajuste; date o texto AAAA-MM-DD.

    Returns:
        Porcentaje aplicado, nuevo canon e incremento, todos como Decimal.

    Raises:
        ErrorReajuste: Si falta un dato, es inválido o no han pasado doce meses.
    """
    canon = _numero(canon_actual, "canon_actual")
    if canon <= 0:
        raise ErrorReajuste("El canon actual debe ser mayor que cero")
    pactado = _porcentaje(porcentaje_pactado, "porcentaje_pactado")
    if not Decimal(0) <= pactado <= Decimal(100):
        raise ErrorReajuste("El porcentaje pactado debe estar entre 0 y 100")
    ipc = _porcentaje(ipc_anterior, "ipc_anterior")
    referencia = _fecha(fecha_referencia, "fecha_referencia")
    reajuste = _fecha(fecha_reajuste, "fecha_reajuste")
    _validar_plazo(referencia, reajuste)
    if ipc <= 0 or pactado == 0:
        return ResultadoReajuste(Decimal(0), canon, Decimal(0))
    aplicado = min(ipc, pactado)
    nuevo, incremento = _calcular_importes(canon, aplicado)
    return ResultadoReajuste(aplicado, nuevo, incremento)
