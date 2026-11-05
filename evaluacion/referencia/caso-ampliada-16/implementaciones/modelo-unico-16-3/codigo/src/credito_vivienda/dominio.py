"""Entradas y operaciones del crédito con las restricciones confirmadas."""

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Never

_MENSAJE_PENDIENTE = (
    "Reglas de redondeo pendientes de definir: redondeo de la tasa mensual "
    "y tratamiento de los medios pesos. No se ha autorizado una regla alternativa; "
    "no se emiten resultados financieros ni archivos CSV."
)
_NUMERO = re.compile(r"[+-]?[0-9]+(?:\.[0-9]+)?")


class DatoInvalido(ValueError):
    """Indica un dato no numérico, fuera de rango o con precisión no admitida."""


class ReglasPendientes(RuntimeError):
    """Indica que no se puede calcular sin sustituir reglas no autorizadas."""


def _validar_intervalo(
    valor: Decimal,
    nombre: str,
    minimo: str,
    maximo: str,
    unidad: str,
) -> None:
    if not isinstance(valor, Decimal) or not valor.is_finite():
        raise DatoInvalido(f"{nombre}: debe ser un número decimal finito.")
    if not Decimal(minimo) <= valor <= Decimal(maximo):
        raise DatoInvalido(
            f"{nombre}: debe estar entre {minimo} y {maximo} {unidad}, inclusive."
        )


@dataclass(frozen=True)
class Solicitud:
    """Contiene los datos validados, sin convertir ni redondear tasas.

    Attributes:
        monto: Capital solicitado en pesos, representado con Decimal.
        plazo: Duración en meses; no se exige un valor entero.
        tasa_anual: Tasa efectiva anual expresada en porcentaje, no en proporción.
    """

    monto: Decimal
    plazo: Decimal
    tasa_anual: Decimal

    def __post_init__(self) -> None:
        """Valida los datos al construir la solicitud."""
        self.validar()

    def validar(self) -> None:
        """Comprueba límites inclusivos y hasta dos decimales en la tasa.

        Raises:
            DatoInvalido: Si algún campo no cumple las restricciones conocidas.
        """
        _validar_intervalo(self.monto, "Monto", "10000000", "500000000", "pesos")
        _validar_intervalo(self.plazo, "Plazo", "12", "240", "meses")
        _validar_intervalo(self.tasa_anual, "Tasa efectiva anual", "1", "30", "%")
        if self.tasa_anual.as_tuple().exponent < -2:
            raise DatoInvalido("Tasa efectiva anual: admite hasta dos decimales.")


def _leer_decimal(texto: str, nombre: str) -> Decimal:
    limpio = texto.strip()
    if _NUMERO.fullmatch(limpio) is None:
        raise DatoInvalido(
            f"{nombre}: debe ser un número con punto decimal, sin separadores de miles."
        )
    return Decimal(limpio)


def leer_solicitud(monto: str, plazo: str, tasa_anual: str) -> Solicitud:
    """Lee números decimales escritos sin separadores de miles.

    Args:
        monto: Capital en pesos, por ejemplo '100000000'.
        plazo: Meses, por ejemplo '120'.
        tasa_anual: Porcentaje anual, por ejemplo '12' o '12.25'.

    Returns:
        Solicitud validada; no se realiza ningún cálculo financiero.

    Raises:
        DatoInvalido: Si un dato no es numérico o incumple las restricciones.
    """
    return Solicitud(
        monto=_leer_decimal(monto, "Monto"),
        plazo=_leer_decimal(plazo, "Plazo"),
        tasa_anual=_leer_decimal(tasa_anual, "Tasa efectiva anual"),
    )


def _exigir_reglas(solicitud: Solicitud) -> Never:
    solicitud.validar()
    raise ReglasPendientes(_MENSAJE_PENDIENTE)


def calcular_cuota(solicitud: Solicitud) -> Never:
    """Solicita la cuota como operación independiente.

    Args:
        solicitud: Datos del crédito previamente ingresados.

    Raises:
        DatoInvalido: Si los datos incumplen las restricciones conocidas.
        ReglasPendientes: Siempre, mientras el redondeo no esté definido.
    """
    _exigir_reglas(solicitud)


def generar_tabla(solicitud: Solicitud) -> Never:
    """Solicita la tabla como operación independiente.

    Args:
        solicitud: Datos del crédito previamente ingresados.

    Raises:
        DatoInvalido: Si los datos incumplen las restricciones conocidas.
        ReglasPendientes: Siempre; no se genera una amortización no autorizada.
    """
    _exigir_reglas(solicitud)


def calcular_resumen(solicitud: Solicitud) -> Never:
    """Solicita total pagado e intereses como operación independiente.

    Args:
        solicitud: Datos del crédito previamente ingresados.

    Raises:
        DatoInvalido: Si los datos incumplen las restricciones conocidas.
        ReglasPendientes: Siempre; no se calculan totales sin una tabla válida.
    """
    _exigir_reglas(solicitud)
