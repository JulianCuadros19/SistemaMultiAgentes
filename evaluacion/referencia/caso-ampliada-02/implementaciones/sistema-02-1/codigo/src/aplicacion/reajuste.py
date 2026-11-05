"""Caso de uso para realizar el reajuste anual de un canon."""

from datetime import date
from decimal import Decimal

from dominio.reajuste import MesesInsuficientesError, ReajusteResultado, calcular_reajuste


def realizar_reajuste(
    canon_actual: Decimal,
    porcentaje_pactado: Decimal,
    ipc_del_ano_anterior: Decimal,
    fecha_de_inicio_o_del_ultimo_reajuste: date,
    fecha_del_reajuste: date,
) -> ReajusteResultado:
    """Delega la validación y el cálculo del reajuste en el dominio.

    Args:
        canon_actual: Canon positivo, expresado en pesos.
        porcentaje_pactado: Porcentaje entre cero y cien, con hasta dos decimales.
        ipc_del_ano_anterior: IPC finito, con hasta dos decimales.
        fecha_de_inicio_o_del_ultimo_reajuste: Fecha inicial del plazo mínimo.
        fecha_del_reajuste: Fecha propuesta para el reajuste.

    Returns:
        Resultado del reajuste que permite comunicar el nuevo canon.

    Raises:
        MesesInsuficientesError: Si los datos son inválidos o el plazo es insuficiente.
    """
    try:
        return calcular_reajuste(
            canon_actual,
            porcentaje_pactado,
            ipc_del_ano_anterior,
            fecha_de_inicio_o_del_ultimo_reajuste,
            fecha_del_reajuste,
        )
    except MesesInsuficientesError:
        raise
