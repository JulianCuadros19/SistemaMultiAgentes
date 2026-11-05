"""Matriz de confusión del tester frente al oráculo común (paso 15, ADR-0019).

La tesis mide al tester con defectos inyectados, que el corpus conoce de antemano. Esta matriz lo
mide en módulos reales: cada versión que el tester dictaminó se evalúa también con las pruebas de
aceptación de referencia, que no dependen de lo que el sistema elicitó.

- **Positivo real:** la versión tiene un error, porque alguna verificación de referencia no pasa.
- **Predicción positiva:** el tester la rechaza.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass

_VEREDICTO = re.compile(r"\*\*Veredicto: (APROBADO|RECHAZADO)\*\*")


class ReporteSinVeredicto(ValueError):
    """El reporte de validación no trae un veredicto que se pueda leer."""


def rechazada_por_el_tester(reporte: str) -> bool:
    """Lee el veredicto del tester en el reporte de validación de una versión.

    Args:
        reporte: Texto de `REPORTE_VALIDACION.md`.

    Returns:
        Si el tester rechazó la versión.

    Raises:
        ReporteSinVeredicto: Si el reporte no trae el veredicto.
    """
    coincidencia = _VEREDICTO.search(reporte)
    if coincidencia is None:
        raise ReporteSinVeredicto("El reporte no trae un veredicto.")
    return coincidencia.group(1) == "RECHAZADO"


@dataclass(frozen=True)
class VersionEvaluada:
    """Una versión dictaminada por el tester y evaluada con el oráculo.

    Attributes:
        caso: Identificador del caso de referencia.
        etiqueta: Corrida del sistema, como `sistema-02-1`.
        version: Número de la versión del módulo.
        rechazada: Si el tester la rechazó.
        pasan: Verificaciones de referencia que pasan.
        total: Verificaciones de referencia del caso.
    """

    caso: str
    etiqueta: str
    version: int
    rechazada: bool
    pasan: int
    total: int

    @property
    def tiene_error(self) -> bool:
        """Si alguna verificación de referencia no pasa."""
        return self.pasan < self.total


def _razon(numerador: int, denominador: int) -> float | None:
    return numerador / denominador if denominador else None


@dataclass(frozen=True)
class MatrizConfusion:
    """Conteos de la matriz y sus métricas (Tabla 13 de la tesis).

    Una métrica sin denominador vale None: la muestra no permite calcularla.

    Attributes:
        verdaderos_positivos: Versiones con error que el tester rechazó.
        falsos_positivos: Versiones sin error que el tester rechazó.
        falsos_negativos: Versiones con error que el tester aprobó.
        verdaderos_negativos: Versiones sin error que el tester aprobó.
    """

    verdaderos_positivos: int
    falsos_positivos: int
    falsos_negativos: int
    verdaderos_negativos: int

    @property
    def total(self) -> int:
        """Versiones de la matriz."""
        return (
            self.verdaderos_positivos
            + self.falsos_positivos
            + self.falsos_negativos
            + self.verdaderos_negativos
        )

    @property
    def exactitud(self) -> float | None:
        """Proporción de versiones en que el tester coincide con el oráculo."""
        return _razon(self.verdaderos_positivos + self.verdaderos_negativos, self.total)

    @property
    def precision(self) -> float | None:
        """De las versiones rechazadas, la proporción que tiene un error."""
        return _razon(self.verdaderos_positivos, self.verdaderos_positivos + self.falsos_positivos)

    @property
    def sensibilidad(self) -> float | None:
        """De las versiones con error, la proporción que el tester rechazó."""
        return _razon(self.verdaderos_positivos, self.verdaderos_positivos + self.falsos_negativos)

    @property
    def f1(self) -> float | None:
        """Media armónica entre la precisión y la sensibilidad."""
        if not self.precision or not self.sensibilidad:
            return None
        return 2 * self.precision * self.sensibilidad / (self.precision + self.sensibilidad)


def matriz_de_versiones(versiones: Iterable[VersionEvaluada]) -> MatrizConfusion:
    """Cuenta cada versión en su celda de la matriz.

    Args:
        versiones: Versiones dictaminadas y evaluadas con el oráculo.

    Returns:
        La matriz de confusión del tester frente al oráculo.
    """
    lista = list(versiones)
    return MatrizConfusion(
        verdaderos_positivos=sum(v.tiene_error and v.rechazada for v in lista),
        falsos_positivos=sum(not v.tiene_error and v.rechazada for v in lista),
        falsos_negativos=sum(v.tiene_error and not v.rechazada for v in lista),
        verdaderos_negativos=sum(not v.tiene_error and not v.rechazada for v in lista),
    )
