"""Validación y cálculo monetario del reajuste."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation, localcontext
from typing import TypeAlias

EntradaNumero: TypeAlias = Decimal | int | str | None
EntradaFecha: TypeAlias = date | str | None

_ESPERA = "El contrato aún no cumple doce meses desde el último reajuste"


class ErrorReajuste(ValueError):
    """Indica un dato inválido o un reajuste solicitado antes del plazo permitido."""


@dataclass(frozen=True)
class ResultadoReajuste:
    """Resultado monetario exacto del reajuste.

    Attributes:
        nuevo_canon: Canon resultante, en pesos.
        incremento: Diferencia entre el nuevo canon y el canon recibido.
        porcentaje_aplicado: Porcentaje seleccionado antes del redondeo monetario.
    """

    nuevo_canon: Decimal
    incremento: Decimal
    porcentaje_aplicado: Decimal


def _numero(valor: EntradaNumero, nombre: str) -> Decimal:
    if valor is None:
        raise ErrorReajuste(f"Falta el dato obligatorio: {nombre}")
    if isinstance(valor, bool) or not isinstance(valor, Decimal | int | str):
        raise ErrorReajuste(f"{nombre} debe ser un número decimal válido")
    try:
        numero = Decimal(valor)
    except (InvalidOperation, ValueError) as exc:
        raise ErrorReajuste(f"{nombre} debe ser un número decimal válido") from exc
    if not numero.is_finite():
        raise ErrorReajuste(f"{nombre} debe ser un número decimal válido")
    return numero


def _validar_decimales(numero: Decimal, nombre: str) -> None:
    partes = numero.as_tuple()
    exponente = partes.exponent
    # Los valores no finitos ya fueron rechazados por _numero.
    if not isinstance(exponente, int):
        raise ErrorReajuste(f"{nombre} debe ser un número decimal válido")
    digitos = list(partes.digits)
    while digitos and digitos[-1] == 0:
        digitos.pop()
        exponente += 1
    if digitos and exponente < -2:
        raise ErrorReajuste(f"{nombre} debe tener hasta dos decimales")


def _fecha(valor: EntradaFecha, nombre: str) -> date:
    if valor is None:
        raise ErrorReajuste(f"Falta el dato obligatorio: {nombre}")
    if isinstance(valor, date) and not isinstance(valor, datetime):
        return valor
    if isinstance(valor, str):
        try:
            resultado = date.fromisoformat(valor)
        except ValueError as exc:
            raise ErrorReajuste(f"{nombre} debe ser una fecha válida en formato AAAA-MM-DD") from exc
        if resultado.isoformat() == valor:
            return resultado
    raise ErrorReajuste(f"{nombre} debe ser una fecha válida en formato AAAA-MM-DD")


def _validar_plazo(inicio: date, reajuste: date) -> None:
    if inicio.year == 9999:
        raise ErrorReajuste(_ESPERA)
    try:
        aniversario = inicio.replace(year=inicio.year + 1)
    except ValueError:
        aniversario = date(inicio.year + 1, 2, 28)
    if reajuste < aniversario:
        raise ErrorReajuste(_ESPERA)


def _calcular(canon: Decimal, aplicado: Decimal) -> ResultadoReajuste:
    partes = canon.as_tuple()
    exponente = partes.exponent
    if not isinstance(exponente, int):
        raise ErrorReajuste("canon_actual debe ser un número decimal válido")
    # Precisión local suficiente para multiplicar, dividir por 100 y restar,
    # sin depender de la precisión decimal configurada por quien llama.
    precision = len(partes.digits) + abs(exponente) + 20
    with localcontext() as contexto:
        contexto.prec = precision
        contexto.Emax = max(contexto.Emax, precision)
        contexto.Emin = min(contexto.Emin, -precision)
        calculado = canon * (Decimal(1) + aplicado / Decimal(100))
        nuevo = calculado.quantize(Decimal("1E2"), rounding=ROUND_HALF_UP)
        incremento = nuevo - canon
    return ResultadoReajuste(nuevo, incremento, aplicado)


def calcular_reajuste(
    *,
    canon_actual: EntradaNumero = None,
    porcentaje_pactado: EntradaNumero = None,
    ipc_anterior: EntradaNumero = None,
    fecha_base: EntradaFecha = None,
    fecha_reajuste: EntradaFecha = None,
) -> ResultadoReajuste:
    """Valida los datos y calcula el reajuste de un canon.

    Args:
        canon_actual: Canon positivo, en pesos; Decimal, entero o texto decimal.
        porcentaje_pactado: Porcentaje entre 0 y 100, con hasta dos decimales.
        ipc_anterior: IPC del año calendario anterior, con hasta dos decimales.
        fecha_base: Fecha de inicio o último reajuste; date o texto AAAA-MM-DD.
        fecha_reajuste: Fecha solicitada; date o texto AAAA-MM-DD.

    Returns:
        Nuevo canon, incremento y porcentaje aplicado, expresados como Decimal.

    Raises:
        ErrorReajuste: Si falta un dato, es inválido o no han pasado doce meses.
    """
    canon = _numero(canon_actual, "canon_actual")
    pactado = _numero(porcentaje_pactado, "porcentaje_pactado")
    ipc = _numero(ipc_anterior, "ipc_anterior")
    inicio = _fecha(fecha_base, "fecha_base")
    reajuste = _fecha(fecha_reajuste, "fecha_reajuste")
    if canon <= 0:
        raise ErrorReajuste("canon_actual debe ser mayor que cero")
    if not Decimal(0) <= pactado <= Decimal(100):
        raise ErrorReajuste("porcentaje_pactado debe estar entre 0 y 100")
    _validar_decimales(pactado, "porcentaje_pactado")
    _validar_decimales(ipc, "ipc_anterior")
    _validar_plazo(inicio, reajuste)
    if ipc <= 0:
        return ResultadoReajuste(canon, Decimal(0), Decimal(0))
    return _calcular(canon, min(pactado, ipc))
