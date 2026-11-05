"""Validación y cálculo del reajuste, sin dependencias externas."""

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation, localcontext
from fractions import Fraction

_Numero = Decimal | int | float | str
_MENSAJE_PLAZO = "El contrato aún no cumple doce meses desde el último reajuste"


@dataclass(frozen=True)
class ResultadoReajuste:
    """Resultado monetario del reajuste.

    Attributes:
        nuevo_canon: Canon resultante, en pesos.
        porcentaje_aplicado: Porcentaje utilizado; 5.20 significa 5,20 %.
        incremento: Diferencia entre el nuevo canon y el canon recibido.
    """

    nuevo_canon: Decimal
    porcentaje_aplicado: Decimal
    incremento: Decimal


def _decimal(valor: _Numero, nombre: str) -> Decimal:
    if isinstance(valor, bool) or not isinstance(valor, Decimal | int | float | str):
        raise ValueError(f"{nombre} debe ser un número finito obligatorio")
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{nombre} debe ser un número finito obligatorio") from exc
    if not numero.is_finite():
        raise ValueError(f"{nombre} debe ser un número finito obligatorio")
    return numero


def _porcentaje(valor: _Numero, nombre: str) -> Decimal:
    numero = _decimal(valor, nombre)
    if (Fraction(numero) * 100).denominator != 1:
        raise ValueError(f"{nombre} debe tener hasta dos decimales")
    return numero


def _validar_fecha(valor: date, nombre: str) -> None:
    if not isinstance(valor, date) or isinstance(valor, datetime):
        raise ValueError(f"{nombre} debe ser una fecha obligatoria de tipo date")


def _cumple_plazo(fecha_base: date, fecha_reajuste: date) -> bool:
    diferencia = fecha_reajuste.year - fecha_base.year
    if diferencia < 1:
        return False
    if diferencia > 1:
        return True
    ultimo_dia = monthrange(fecha_reajuste.year, fecha_base.month)[1]
    aniversario = date(
        fecha_reajuste.year,
        fecha_base.month,
        min(fecha_base.day, ultimo_dia),
    )
    return fecha_reajuste >= aniversario


def calcular_reajuste(
    canon_actual: _Numero,
    porcentaje_pactado: _Numero,
    ipc_anterior: _Numero,
    fecha_base: date,
    fecha_reajuste: date,
) -> ResultadoReajuste:
    """Calcule el reajuste tras al menos doce meses calendario.

    Args:
        canon_actual: Canon vigente en pesos, obligatorio y mayor que cero.
        porcentaje_pactado: Porcentaje entre 0 y 100, con hasta dos decimales.
        ipc_anterior: IPC del año calendario anterior, con hasta dos decimales.
        fecha_base: Fecha de inicio o del último reajuste, según corresponda.
        fecha_reajuste: Fecha efectiva del reajuste, no la fecha de notificación.

    Returns:
        Nuevo canon, porcentaje aplicado e incremento, como valores Decimal.

    Raises:
        ValueError: Si un dato es inválido o todavía no se cumple el plazo.
        TypeError: Si se omite un argumento obligatorio.
    """
    canon = _decimal(canon_actual, "canon_actual")
    if canon <= 0:
        raise ValueError("canon_actual debe ser mayor que cero")
    pactado = _porcentaje(porcentaje_pactado, "porcentaje_pactado")
    if not 0 <= pactado <= 100:
        raise ValueError("porcentaje_pactado debe estar entre 0 y 100")
    ipc = _porcentaje(ipc_anterior, "ipc_anterior")
    _validar_fecha(fecha_base, "fecha_base")
    _validar_fecha(fecha_reajuste, "fecha_reajuste")
    if not _cumple_plazo(fecha_base, fecha_reajuste):
        raise ValueError(_MENSAJE_PLAZO)
    if ipc <= 0:
        return ResultadoReajuste(canon, Decimal(0), Decimal(0))
    aplicado = min(pactado, ipc)
    # La precisión incluye los dígitos y escalas de ambas entradas para no
    # redondear importes intermedios antes de aplicar la regla de centenas.
    with localcontext() as contexto:
        contexto.prec = max(
            28,
            len(canon.as_tuple().digits)
            + abs(int(canon.as_tuple().exponent))
            + len(aplicado.as_tuple().digits)
            + abs(int(aplicado.as_tuple().exponent))
            + 10,
        )
        importe = canon * (Decimal(1) + aplicado / Decimal(100))
        nuevo = importe.quantize(Decimal("1E2"), rounding=ROUND_HALF_UP)
        nuevo = nuevo.quantize(Decimal(1))
        incremento = nuevo - canon
    return ResultadoReajuste(nuevo, aplicado, incremento)
