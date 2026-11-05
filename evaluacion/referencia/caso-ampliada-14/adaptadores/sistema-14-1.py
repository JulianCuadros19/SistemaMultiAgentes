"""Adaptador de sistema-14-1: los comandos y su `_principal`, que es la herramienta de terminal.

El reporte entrega los conteos por año y tipo; el adaptador los agrupa con `Counter`, sin contar
archivos por su cuenta.
"""

import sys
from collections import Counter

from comandos.renombrar import _principal as _renombrar_terminal
from comandos.renombrar import ejecutar_renombrar
from comandos.reporte import _principal as _reporte_terminal
from comandos.reporte import ejecutar_reporte
from comandos.validar import _principal as _validar_terminal
from comandos.validar import ejecutar_validar


def validar(carpeta: str) -> dict[str, str]:
    resultados, _ = ejecutar_validar(carpeta)
    return {r.archivo: r.motivo for r in resultados}


def renombrar(carpeta: str, simulacion: bool) -> dict[str, str]:
    cambios, conflictos, errores = ejecutar_renombrar(carpeta, simulacion)
    tratados = {c.anterior: c.nuevo for c in cambios}
    tratados.update({c.archivo: c.motivo for c in conflictos})
    tratados.update({e.archivo: e.motivo for e in errores})
    return tratados


def reporte(carpeta: str) -> tuple[dict[str, int], dict[str, int]]:
    por_anio: Counter[str] = Counter()
    por_tipo: Counter[str] = Counter()
    for anio, tipos in ejecutar_reporte(carpeta).conteos_por_anio_y_tipo.items():
        for tipo, cantidad in tipos.items():
            por_anio.update({str(anio): cantidad})
            por_tipo.update({tipo: cantidad})
    return dict(por_anio), dict(por_tipo)


def codigo_de_salida(operacion: str, carpeta: str) -> int:
    principales = {
        "validar": _validar_terminal,
        "renombrar": _renombrar_terminal,
        "reporte": _reporte_terminal,
    }
    argumentos = sys.argv
    sys.argv = [operacion, carpeta]
    try:
        return principales[operacion]()
    except SystemExit as salida:
        return int(salida.code or 0)
    finally:
        sys.argv = argumentos
