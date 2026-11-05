"""Reglas de validación y cálculo del reajuste anual del canon."""

from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, localcontext


@dataclass(frozen=True)
class ReajusteResultado:
    """Resultado del reajuste de canon.

    Args:
        nuevo_canon: Canon resultante del cálculo.
        porcentaje_aplicado: Porcentaje aplicado, expresado en puntos porcentuales.
        valor_del_incremento: Diferencia entre el nuevo canon y el canon actual.
    """

    nuevo_canon: Decimal
    porcentaje_aplicado: Decimal
    valor_del_incremento: Decimal


class MesesInsuficientesError(ValueError):
    """Error de validación que impide realizar el reajuste.

    Args:
        mensaje: Descripción del motivo del rechazo.
    """

    def __init__(self, mensaje: str) -> None:
        """Inicializa la excepción con el mensaje indicado.

        Args:
            mensaje: Descripción del motivo del rechazo.
        """
        super().__init__(mensaje)


def _validar_decimal(valor: Decimal, nombre: str, limitar_decimales: bool) -> None:
    if not isinstance(valor, Decimal) or not valor.is_finite():
        raise MesesInsuficientesError(f"{nombre} debe ser un Decimal finito")
    if limitar_decimales:
        partes = valor.as_tuple()
        exponente = partes.exponent
        if isinstance(exponente, int) and exponente < -2:
            if any(partes.digits[exponente + 2 :]):
                raise MesesInsuficientesError(f"{nombre} admite hasta dos decimales")


def _validar_entradas(
    canon_actual: Decimal,
    porcentaje_pactado: Decimal,
    ipc_del_ano_anterior: Decimal,
    fecha_de_inicio_o_del_ultimo_reajuste: date,
    fecha_del_reajuste: date,
) -> None:
    _validar_decimal(canon_actual, "canon_actual", False)
    _validar_decimal(porcentaje_pactado, "porcentaje_pactado", True)
    _validar_decimal(ipc_del_ano_anterior, "ipc_del_ano_anterior", True)
    if canon_actual <= 0:
        raise MesesInsuficientesError("canon_actual debe ser mayor que cero")
    if not Decimal(0) <= porcentaje_pactado <= Decimal(100):
        raise MesesInsuficientesError("porcentaje_pactado debe estar entre 0 y 100")
    if type(fecha_de_inicio_o_del_ultimo_reajuste) is not date:
        raise MesesInsuficientesError("La fecha de inicio o del último reajuste debe ser una fecha")
    if type(fecha_del_reajuste) is not date:
        raise MesesInsuficientesError("La fecha del reajuste debe ser una fecha")


def _validar_plazo(fecha_inicial: date, fecha_final: date) -> None:
    mensaje = "El contrato aún no cumple doce meses desde el último reajuste"
    if fecha_inicial.year == date.max.year:
        raise MesesInsuficientesError(mensaje)
    ano = fecha_inicial.year + 1
    dia = min(fecha_inicial.day, monthrange(ano, fecha_inicial.month)[1])
    aniversario = date(ano, fecha_inicial.month, dia)
    if fecha_final < aniversario:
        raise MesesInsuficientesError(mensaje)


def calcular_reajuste(
    canon_actual: Decimal,
    porcentaje_pactado: Decimal,
    ipc_del_ano_anterior: Decimal,
    fecha_de_inicio_o_del_ultimo_reajuste: date,
    fecha_del_reajuste: date,
) -> ReajusteResultado:
    """Valida el plazo y calcula el reajuste con el porcentaje permitido.

    Args:
        canon_actual: Canon positivo, expresado en pesos.
        porcentaje_pactado: Porcentaje entre cero y cien, con hasta dos decimales.
        ipc_del_ano_anterior: IPC finito, con hasta dos decimales.
        fecha_de_inicio_o_del_ultimo_reajuste: Fecha desde la que se mide el plazo.
        fecha_del_reajuste: Fecha en la que se pretende reajustar.

    Returns:
        Canon resultante, porcentaje aplicado e incremento efectivo.

    Raises:
        MesesInsuficientesError: Si algún dato es inválido o no se cumple el plazo.
    """
    _validar_entradas(
        canon_actual,
        porcentaje_pactado,
        ipc_del_ano_anterior,
        fecha_de_inicio_o_del_ultimo_reajuste,
        fecha_del_reajuste,
    )
    _validar_plazo(fecha_de_inicio_o_del_ultimo_reajuste, fecha_del_reajuste)
    if ipc_del_ano_anterior <= 0:
        return ReajusteResultado(canon_actual, Decimal(0), Decimal(0))
    porcentaje = min(porcentaje_pactado, ipc_del_ano_anterior)
    valores = (canon_actual, porcentaje)
    with localcontext() as contexto:
        contexto.prec = max(
            28,
            sum(len(v.as_tuple().digits) + abs(int(v.as_tuple().exponent)) for v in valores)
            + 10,
        )
        canon_calculado = canon_actual * (Decimal(1) + porcentaje / Decimal(100))
        nuevo_canon = canon_calculado.quantize(Decimal("1E2"), rounding=ROUND_HALF_UP)
        incremento = nuevo_canon - canon_actual
    return ReajusteResultado(nuevo_canon, porcentaje, incremento)
