"""Servicio HTTP de consulta de tarifas y cálculo del impuesto predial."""

from predial.servicio import ErrorConsulta, app, calcular_impuesto, consultar_tarifa

__all__ = ["ErrorConsulta", "app", "calcular_impuesto", "consultar_tarifa"]
