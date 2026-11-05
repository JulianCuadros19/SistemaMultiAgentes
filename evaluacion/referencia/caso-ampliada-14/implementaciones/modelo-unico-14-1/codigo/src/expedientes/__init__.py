"""Validación, corrección y reporte de nombres de expedientes escaneados."""

from expedientes.core import CarpetaError, Evaluacion, Informe, Resultado, evaluar_nombre, procesar_carpeta

__all__ = [
    "CarpetaError",
    "Evaluacion",
    "Informe",
    "Resultado",
    "evaluar_nombre",
    "procesar_carpeta",
]
