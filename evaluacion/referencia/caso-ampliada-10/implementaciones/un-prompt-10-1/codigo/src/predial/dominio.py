"""Reglas del impuesto predial, independientes del transporte HTTP."""

_TARIFAS_RESIDENCIALES = {1: 5, 2: 6, 3: 8, 4: 10, 5: 12, 6: 14}
_TARIFAS_OTROS_DESTINOS = {
    "comercial": 11,
    "industrial": 12,
    "lote urbanizable no edificado": 33,
}


class ErrorConsulta(ValueError):
    """Indique una entrada inválida mediante un mensaje apto para el consumidor."""


def consultar_tarifa(destino: str, estrato: int | None = None) -> int:
    """Obtenga la tarifa en pesos por cada mil pesos de avalúo.

    Args:
        destino: Nombre exacto del destino económico.
        estrato: Entero de 1 a 6 para residencial; se ignora para otros destinos.

    Returns:
        Tarifa entera por mil.

    Raises:
        ErrorConsulta: Si el destino es desconocido o el estrato residencial es inválido.
    """
    if not isinstance(destino, str):
        raise ErrorConsulta("Destino económico no reconocido")
    if destino == "residencial":
        if isinstance(estrato, bool) or not isinstance(estrato, int):
            raise ErrorConsulta("Estrato inválido")
        if estrato not in _TARIFAS_RESIDENCIALES:
            raise ErrorConsulta("Estrato inválido")
        return _TARIFAS_RESIDENCIALES[estrato]
    if destino not in _TARIFAS_OTROS_DESTINOS:
        raise ErrorConsulta("Destino económico no reconocido")
    return _TARIFAS_OTROS_DESTINOS[destino]


def calcular_impuesto(avaluo: int, destino: str, estrato: int | None = None) -> int:
    """Calcule el impuesto al peso, con las mitades hacia arriba.

    Args:
        avaluo: Avalúo positivo en pesos enteros, sin decimales.
        destino: Nombre exacto del destino económico.
        estrato: Estrato residencial; se ignora para otros destinos.

    Returns:
        Impuesto en pesos enteros, calculado sin aritmética de punto flotante.

    Raises:
        ErrorConsulta: Si el avalúo no es entero positivo o la tarifa no puede consultarse.
    """
    if isinstance(avaluo, bool) or not isinstance(avaluo, int):
        raise ErrorConsulta("El avalúo debe ser un entero en pesos")
    if avaluo <= 0:
        raise ErrorConsulta("El avalúo debe ser mayor que cero")
    tarifa = consultar_tarifa(destino, estrato)
    return (avaluo * tarifa + 500) // 1000
