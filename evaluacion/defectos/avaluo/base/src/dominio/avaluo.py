"""Objetos de dominio y validaciones del cálculo de avalúos."""

from dataclasses import dataclass
from decimal import Decimal


class NumeroPredialInvalido(ValueError):
    """El número predial no contiene exactamente 30 dígitos."""


class AreaTerrenoInvalida(ValueError):
    """El área de terreno no es un Decimal finito mayor que cero."""


class AreaConstruidaInvalida(ValueError):
    """El área construida no es un Decimal finito no negativo."""


class VigenciaInvalida(ValueError):
    """La vigencia no cumple las restricciones del año."""


class ValoresUnitariosNoEncontrados(LookupError):
    """No existen valores unitarios para el predio y la vigencia."""


def numero_predial_valido(numero: str) -> bool:
    """Indica si el número predial tiene exactamente 30 dígitos.

    Args:
        numero: Número predial.

    Returns:
        True si es un texto de 30 dígitos decimales.
    """
    return isinstance(numero, str) and len(numero) == 30 and numero.isdecimal()


def _decimal_valido(valor: Decimal, permitir_cero: bool) -> bool:
    if not isinstance(valor, Decimal) or not valor.is_finite():
        return False
    return valor >= 0 if permitir_cero else valor > 0


@dataclass(frozen=True)
class Predio:
    """Representa un predio validado.

    Args:
        numero_predial: Identificador de exactamente 30 dígitos.
        area_terreno: Área finita mayor que cero, en metros cuadrados.
        area_construida: Área finita no negativa, en metros cuadrados.

    Raises:
        NumeroPredialInvalido: Si el identificador es inválido.
        AreaTerrenoInvalida: Si el área de terreno es inválida.
        AreaConstruidaInvalida: Si el área construida es inválida.
    """

    numero_predial: str
    area_terreno: Decimal
    area_construida: Decimal

    def __post_init__(self) -> None:
        """Comprueba las restricciones del predio.

        Raises:
            NumeroPredialInvalido: Si el identificador es inválido.
            AreaTerrenoInvalida: Si el terreno no tiene área positiva.
            AreaConstruidaInvalida: Si la construcción tiene área inválida.
        """
        if not numero_predial_valido(self.numero_predial):
            raise NumeroPredialInvalido("El número predial debe contener exactamente 30 dígitos.")
        if not _decimal_valido(self.area_terreno, permitir_cero=False):
            raise AreaTerrenoInvalida("El área de terreno debe ser mayor que cero y finita.")
        if not _decimal_valido(self.area_construida, permitir_cero=True):
            raise AreaConstruidaInvalida(
                "El área construida debe ser mayor o igual a cero y finita."
            )


@dataclass(frozen=True)
class ValoresUnitarios:
    """Contiene los valores unitarios en pesos por metro cuadrado.

    Args:
        valor_terreno_m2: Decimal finito mayor que cero.
        valor_construccion_m2: Decimal finito mayor o igual a cero.

    Raises:
        ValueError: Si algún valor incumple su restricción.
    """

    valor_terreno_m2: Decimal
    valor_construccion_m2: Decimal

    def __post_init__(self) -> None:
        """Valida los valores unitarios.

        Raises:
            ValueError: Si algún valor no tiene el tipo o rango requerido.
        """
        if not _decimal_valido(self.valor_terreno_m2, permitir_cero=False):
            raise ValueError("El valor unitario de terreno debe ser un Decimal finito positivo.")
        if not _decimal_valido(self.valor_construccion_m2, permitir_cero=True):
            raise ValueError("El valor unitario de construcción debe ser un Decimal no negativo.")


@dataclass(frozen=True)
class ResultadoAvaluo:
    """Contiene los avalúos en pesos enteros no negativos.

    Args:
        avaluo_terreno: Avalúo del terreno.
        avaluo_construccion: Avalúo de la construcción.
        avaluo_total: Avalúo total.

    Raises:
        ValueError: Si algún importe no es un Decimal finito, entero y no negativo.
    """

    avaluo_terreno: Decimal
    avaluo_construccion: Decimal
    avaluo_total: Decimal

    def __post_init__(self) -> None:
        """Valida el formato y rango de los importes.

        Raises:
            ValueError: Si algún importe no representa pesos enteros no negativos.
        """
        for valor in (self.avaluo_terreno, self.avaluo_construccion, self.avaluo_total):
            if not _decimal_valido(valor, permitir_cero=True):
                raise ValueError("Los avalúos deben ser Decimal finitos no negativos.")
            if valor != valor.to_integral_value():
                raise ValueError("Los avalúos deben expresarse en pesos sin decimales.")
