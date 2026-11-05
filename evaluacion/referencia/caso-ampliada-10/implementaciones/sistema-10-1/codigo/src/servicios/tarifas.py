"""Consulta de tarifas y cálculo del impuesto predial en pesos."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, localcontext


@dataclass(frozen=True)
class TarifaResultado:
    """Resultado de la consulta de tarifa.

    Args:
        tarifa: Tarifa entera por mil.
        estrato_aplicado: Estrato residencial aplicado, o ninguno.
    """

    tarifa: int
    estrato_aplicado: int | None = None


@dataclass(frozen=True)
class CalculoImpuestoResultado:
    """Resultado del cálculo del impuesto.

    Args:
        impuesto_calculado: Impuesto en pesos enteros.
        tarifa: Tarifa entera por mil utilizada.
        estrato_aplicado: Estrato residencial aplicado, o ninguno.
    """

    impuesto_calculado: int
    tarifa: int
    estrato_aplicado: int | None = None


class DestinoNoReconocidoError(ValueError):
    """Indica que el destino económico no se reconoce.

    Args:
        mensaje: Descripción del error de negocio.
    """

    def __init__(self, mensaje: str = "Destino económico no reconocido") -> None:
        """Inicializa el error.

        Args:
            mensaje: Descripción del error de negocio.
        """
        super().__init__(mensaje)


class EstratoInvalidoError(ValueError):
    """Indica que el estrato residencial no es válido.

    Args:
        mensaje: Descripción del error de negocio.
    """

    def __init__(self, mensaje: str = "Estrato inválido") -> None:
        """Inicializa el error.

        Args:
            mensaje: Descripción del error de negocio.
        """
        super().__init__(mensaje)


class AvaluoNoValidoError(ValueError):
    """Indica que el avalúo no es un entero positivo.

    Args:
        mensaje: Descripción del error de negocio.
    """

    def __init__(self, mensaje: str = "El avalúo debe ser mayor que cero") -> None:
        """Inicializa el error.

        Args:
            mensaje: Descripción del error de negocio.
        """
        super().__init__(mensaje)


def obtener_tarifa(destino: str, estrato: int | None = None) -> TarifaResultado:
    """Determina la tarifa por mil del destino indicado.

    Args:
        destino: Nombre exacto del destino económico reconocido.
        estrato: Estrato de 1 a 6 para residencial; se ignora en otros destinos.

    Returns:
        Tarifa y estrato aplicado cuando corresponde.

    Raises:
        DestinoNoReconocidoError: Si el destino no está reconocido.
        EstratoInvalidoError: Si el estrato residencial no es un entero de 1 a 6.
    """
    if not isinstance(destino, str):
        raise DestinoNoReconocidoError()
    if destino == "residencial":
        if type(estrato) is not int or not 1 <= estrato <= 6:
            raise EstratoInvalidoError()
        tarifas_residenciales = (5, 6, 8, 10, 12, 14)
        return TarifaResultado(tarifas_residenciales[estrato - 1], estrato)
    tarifas = {"comercial": 11, "industrial": 12, "lote urbanizable no edificado": 33}
    if destino not in tarifas:
        raise DestinoNoReconocidoError()
    return TarifaResultado(tarifas[destino])


def calcular_impuesto(
    avaluo: int, destino: str, estrato: int | None = None
) -> CalculoImpuestoResultado:
    """Calcula el impuesto con redondeo al peso y mitades hacia arriba.

    Args:
        avaluo: Avalúo en pesos enteros, mayor que cero.
        destino: Nombre exacto del destino económico reconocido.
        estrato: Estrato residencial, cuando aplica.

    Returns:
        Impuesto en pesos, tarifa y estrato aplicado.

    Raises:
        AvaluoNoValidoError: Si el avalúo no es un entero positivo.
        DestinoNoReconocidoError: Si el destino no está reconocido.
        EstratoInvalidoError: Si el estrato residencial no es válido.
    """
    if type(avaluo) is not int or avaluo <= 0:
        raise AvaluoNoValidoError()
    resultado = obtener_tarifa(destino, estrato)
    valor = Decimal(avaluo)
    with localcontext() as contexto:
        contexto.prec = max(28, valor.adjusted() + 10)
        impuesto = (valor * Decimal(resultado.tarifa) / Decimal(1000)).quantize(
            Decimal(1), rounding=ROUND_HALF_UP
        )
    return CalculoImpuestoResultado(
        int(impuesto), resultado.tarifa, resultado.estrato_aplicado
    )
