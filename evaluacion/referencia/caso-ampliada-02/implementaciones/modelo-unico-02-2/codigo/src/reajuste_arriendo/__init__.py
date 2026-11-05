"""Calcule el reajuste anual de un contrato de arriendo, sin servicios externos."""

import re
from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime
from decimal import MAX_EMAX, MIN_EMIN, Context, Decimal, ROUND_HALF_UP, localcontext

__all__ = ["ErrorReajuste", "ResultadoReajuste", "calcular_reajuste"]

_Numero = Decimal | int | str
_CENTENA = Decimal("1E2")
_CERO = Decimal(0)
_CIEN = Decimal(100)
_PATRON_NUMERO = re.compile(r"[+-]?[0-9]+(?:[.,][0-9]+)?\Z")
_PATRON_FECHA = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
_ERROR_PLAZO = "El contrato aún no cumple doce meses desde el último reajuste"


class ErrorReajuste(ValueError):
    """Indique un dato inválido, ausente o un reajuste solicitado antes de tiempo."""


@dataclass(frozen=True)
class ResultadoReajuste:
    """Contenga los tres resultados monetarios y porcentuales del cálculo.

    Attributes:
        porcentaje_aplicado: Porcentaje en unidades porcentuales; 5.20 significa 5.20 %.
        nuevo_canon: Canon resultante en pesos, como Decimal.
        incremento: Incremento mostrado en pesos, como Decimal.
    """

    porcentaje_aplicado: Decimal
    nuevo_canon: Decimal
    incremento: Decimal


def _es_ausente(valor: object) -> bool:
    return valor is None or (isinstance(valor, str) and not valor.strip())


def _numero(valor: _Numero | None, campo: str) -> Decimal:
    if _es_ausente(valor):
        raise ErrorReajuste(f"Falta el dato obligatorio: {campo}")
    if isinstance(valor, bool):
        raise ErrorReajuste(f"{campo}: debe ser un número decimal válido")
    if isinstance(valor, str):
        texto = valor.strip()
        if not _PATRON_NUMERO.fullmatch(texto):
            raise ErrorReajuste(f"{campo}: debe ser un número decimal válido")
        numero = Decimal(texto.replace(",", "."))
    elif isinstance(valor, (Decimal, int)):
        numero = Decimal(valor)
    else:
        raise ErrorReajuste(f"{campo}: debe ser un número decimal válido")
    if not numero.is_finite():
        raise ErrorReajuste(f"{campo}: debe ser un número decimal válido")
    return numero


def _porcentaje(valor: _Numero | None, campo: str) -> Decimal:
    numero = _numero(valor, campo)
    exponente = numero.as_tuple().exponent
    # Los valores no finitos ya fueron rechazados; aquí el exponente es entero.
    if isinstance(exponente, int) and exponente < -2:
        raise ErrorReajuste(f"{campo}: debe tener como máximo dos decimales")
    return numero


def _fecha(valor: date | str | None, campo: str) -> date:
    if _es_ausente(valor):
        raise ErrorReajuste(f"Falta el dato obligatorio: {campo}")
    if isinstance(valor, datetime):
        raise ErrorReajuste(f"{campo}: debe ser una fecha válida en formato AAAA-MM-DD")
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str) and _PATRON_FECHA.fullmatch(valor.strip()):
        try:
            return date.fromisoformat(valor.strip())
        except ValueError as error:
            raise ErrorReajuste(
                f"{campo}: debe ser una fecha válida en formato AAAA-MM-DD"
            ) from error
    raise ErrorReajuste(f"{campo}: debe ser una fecha válida en formato AAAA-MM-DD")


def _validar_plazo(fecha_base: date, fecha_reajuste: date) -> None:
    # No existe una fecha representable doce meses después del año 9999.
    if fecha_base.year == date.max.year:
        raise ErrorReajuste(_ERROR_PLAZO)
    anio = fecha_base.year + 1
    dia = min(fecha_base.day, monthrange(anio, fecha_base.month)[1])
    aniversario = date(anio, fecha_base.month, dia)
    if fecha_reajuste < aniversario:
        raise ErrorReajuste(_ERROR_PLAZO)


def _calcular_importes(canon: Decimal, porcentaje: Decimal) -> ResultadoReajuste:
    exponente = canon.as_tuple().exponent
    if not isinstance(exponente, int):
        raise ErrorReajuste("canon_actual: debe ser un número decimal válido")
    precision = max(28, len(canon.as_tuple().digits) + abs(exponente) + 10)
    contexto = Context(
        prec=precision,
        rounding=ROUND_HALF_UP,
        Emin=MIN_EMIN,
        Emax=MAX_EMAX,
    )
    with localcontext(contexto):
        incremento_exacto = canon * porcentaje / _CIEN
        nuevo_exacto = canon + incremento_exacto
        return ResultadoReajuste(
            porcentaje_aplicado=porcentaje,
            nuevo_canon=nuevo_exacto.quantize(_CENTENA, rounding=ROUND_HALF_UP),
            incremento=incremento_exacto.quantize(_CENTENA, rounding=ROUND_HALF_UP),
        )


def calcular_reajuste(
    canon_actual: _Numero | None = None,
    ipc_anterior: _Numero | None = None,
    porcentaje_pactado: _Numero | None = None,
    fecha_base: date | str | None = None,
    fecha_reajuste: date | str | None = None,
) -> ResultadoReajuste:
    """Calcule un contrato tras validar sus datos y el plazo mínimo de doce meses.

    Args:
        canon_actual: Canon vigente en pesos, mayor que cero.
        ipc_anterior: IPC del año calendario anterior, con hasta dos decimales.
        porcentaje_pactado: Límite entre 0 y 100 %, con hasta dos decimales.
        fecha_base: Fecha de inicio o del último reajuste, como date o AAAA-MM-DD.
        fecha_reajuste: Fecha solicitada, como date o AAAA-MM-DD.

    Returns:
        Porcentaje aplicado, nuevo canon e incremento, todos como Decimal.

    Raises:
        ErrorReajuste: Si falta un dato, es inválido o no se cumple el plazo mínimo.

    Notes:
        Los números admiten Decimal, enteros o texto sin separadores de miles.
        El texto admite coma o punto decimal. No se admiten float ni booleanos.
        Las decisiones sobre aniversario, formatos y redondeo están en USO.md.
    """
    canon = _numero(canon_actual, "canon_actual")
    if canon <= _CERO:
        raise ErrorReajuste("canon_actual: debe ser mayor que cero")
    ipc = _porcentaje(ipc_anterior, "ipc_anterior")
    pactado = _porcentaje(porcentaje_pactado, "porcentaje_pactado")
    if not _CERO <= pactado <= _CIEN:
        raise ErrorReajuste("porcentaje_pactado: debe estar entre 0 y 100")
    base = _fecha(fecha_base, "fecha_base")
    reajuste = _fecha(fecha_reajuste, "fecha_reajuste")
    _validar_plazo(base, reajuste)
    aplicado = min(ipc, pactado) if ipc > _CERO else _CERO
    if aplicado == _CERO:
        return ResultadoReajuste(_CERO, canon, _CERO)
    return _calcular_importes(canon, aplicado)
