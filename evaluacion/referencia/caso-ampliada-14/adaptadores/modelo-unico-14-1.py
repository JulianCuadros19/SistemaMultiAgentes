"""Adaptador de modelo-unico-14-1: `procesar_carpeta` y la herramienta de terminal `cli.main`."""

from expedientes.cli import main
from expedientes.core import procesar_carpeta

MODOS = {"validar": "validar", "renombrar": "renombrar", "reporte": "reportar"}


def validar(carpeta: str) -> dict[str, str]:
    informe = procesar_carpeta(carpeta, "validar")
    return {r.nombre: r.detalle for r in informe.resultados if r.estado != "Correcto"}


def renombrar(carpeta: str, simulacion: bool) -> dict[str, str]:
    informe = procesar_carpeta(carpeta, "renombrar", simular=simulacion)
    return {
        r.nombre: r.destino if r.estado in ("Cambio", "Renombrado") else r.detalle
        for r in informe.resultados
        if r.estado != "Correcto"
    }


def reporte(carpeta: str) -> tuple[dict[int, int], dict[str, int]]:
    informe = procesar_carpeta(carpeta, "reportar")
    return informe.por_anio, informe.por_tipo


def codigo_de_salida(operacion: str, carpeta: str) -> int:
    try:
        return main([MODOS[operacion], carpeta])
    except SystemExit as salida:
        return int(salida.code or 0)
