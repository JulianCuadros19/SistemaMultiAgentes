"""Reglas y objetos de valor para el reajuste anual del canon."""

from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, localcontext


class DatosObligatoriosFaltantes(ValueError):
    """Indica la ausencia del canon actual o del IPC anterior."""

    def __init__(self) -> None:
        """Inicializa el error con un mensaje de dominio."""
        super().__init__("Se requieren el canon actual y el IPC del año anterior.")


class PeriodoInsuficienteDoceMeses(ValueError):
    """Indica que no se pueden acreditar doce meses completos."""

    def __init__(self) -> None:
        """Inicializa el error con un mensaje de dominio."""
        super().__init__("El contrato aún no cumple doce meses desde el inicio o último reajuste.")


class ValorInvalido(ValueError):
    """Indica un valor monetario o porcentual inválido."""

    def __init__(self) -> None:
        """Inicializa el error con un mensaje de dominio."""
        super().__init__("Los valores deben ser decimales finitos y cumplir sus restricciones.")


def _tiene_hasta_dos_decimales(valor: Decimal) -> bool:
    partes = valor.as_tuple()
    exponente = int(partes.exponent)
    return exponente >= -2 or not any(partes.digits[exponente + 2 :])


@dataclass(frozen=True)
class ResultadoReajuste:
    """Resultado inmutable del cálculo del reajuste.

    Args:
        canon_reajustado: Canon final, múltiplo de cien.
        porcentaje_aplicado: Porcentaje entre cero y cien, con hasta dos decimales.
        valor_incremento: Diferencia entre el canon final y el canon original.

    Raises:
        ValorInvalido: Si los campos no cumplen las restricciones del resultado.
    """

    canon_reajustado: Decimal
    porcentaje_aplicado: Decimal
    valor_incremento: Decimal

    def __post_init__(self) -> None:
        """Valida los campos del objeto de valor.

        Raises:
            ValorInvalido: Si algún campo no cumple su restricción.
        """
        valores = (self.canon_reajustado, self.porcentaje_aplicado, self.valor_incremento)
        if any(not isinstance(valor, Decimal) or not valor.is_finite() for valor in valores):
            raise ValorInvalido()
        if not Decimal("0") <= self.porcentaje_aplicado <= Decimal("100"):
            raise ValorInvalido()
        if not _tiene_hasta_dos_decimales(self.porcentaje_aplicado):
            raise ValorInvalido()
        if redondear_a_centena_mas_cercana(self.canon_reajustado) != self.canon_reajustado:
            raise ValorInvalido()


def validar_periodo_doce_meses(
    fecha_inicio_o_ultimo_reajuste: date, fecha_reajuste: date
) -> None:
    """Comprueba que se haya alcanzado el aniversario de doce meses.

    Args:
        fecha_inicio_o_ultimo_reajuste: Fecha desde la que se cuenta el periodo.
        fecha_reajuste: Fecha propuesta para el nuevo reajuste.

    Raises:
        PeriodoInsuficienteDoceMeses: Si las fechas no permiten acreditar doce meses.
    """
    if type(fecha_inicio_o_ultimo_reajuste) is not date or type(fecha_reajuste) is not date:
        raise PeriodoInsuficienteDoceMeses()
    inicio = fecha_inicio_o_ultimo_reajuste
    if inicio.year == 9999:
        raise PeriodoInsuficienteDoceMeses()
    ultimo_dia = monthrange(inicio.year + 1, inicio.month)[1]
    aniversario = date(inicio.year + 1, inicio.month, min(inicio.day, ultimo_dia))
    if fecha_reajuste < aniversario:
        raise PeriodoInsuficienteDoceMeses()


def calcular_porcentaje_aplicable(
    ipc_anterior: Decimal | None, porcentaje_pactado: Decimal
) -> Decimal:
    """Determina el porcentaje sin validar el rango del pacto.

    Args:
        ipc_anterior: IPC anterior, o None si no está disponible.
        porcentaje_pactado: Porcentaje pactado previamente validado.

    Returns:
        Cero para IPC no positivo; en otro caso, el menor porcentaje.

    Raises:
        DatosObligatoriosFaltantes: Si falta el IPC anterior.
    """
    if ipc_anterior is None:
        raise DatosObligatoriosFaltantes()
    if ipc_anterior <= Decimal("0"):
        return Decimal("0")
    return min(ipc_anterior, porcentaje_pactado)


def redondear_a_centena_mas_cercana(valor: Decimal) -> Decimal:
    """Redondea un decimal a centenas con redondeo convencional.

    Args:
        valor: Decimal finito que se desea redondear.

    Returns:
        Múltiplo de cien más cercano, usando ROUND_HALF_UP en los empates.
    """
    with localcontext() as contexto:
        contexto.prec = max(28, len(valor.as_tuple().digits), valor.adjusted() + 2)
        return valor.quantize(Decimal("1E2"), rounding=ROUND_HALF_UP)
