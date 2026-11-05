"""Adaptador de un-prompt-14-1: `procesar` y la herramienta de terminal `cli.main`."""

from escaneos.cli import main
from escaneos.core import procesar


def validar(carpeta: str) -> dict[str, str]:
    informe = procesar(carpeta, "validar")
    return {a.nombre: a.motivo for a in informe.archivos if a.estado == "Inválido"}


def renombrar(carpeta: str, simulacion: bool) -> dict[str, str]:
    informe = procesar(carpeta, "renombrar", simular=simulacion)
    tratados = {}
    for archivo in informe.archivos:
        if archivo.estado in ("Conflicto", "Error") or not archivo.destino:
            tratados[archivo.nombre] = f"{archivo.estado}: {archivo.motivo}"
        else:
            tratados[archivo.nombre] = archivo.destino
    return tratados


def reporte(carpeta: str) -> tuple[dict[int, int], dict[str, int]]:
    informe = procesar(carpeta, "reporte")
    return informe.por_anio, informe.por_tipo


def codigo_de_salida(operacion: str, carpeta: str) -> int:
    try:
        return main([operacion, carpeta])
    except SystemExit as salida:
        return int(salida.code or 0)
