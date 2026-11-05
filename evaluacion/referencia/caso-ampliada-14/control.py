"""Implementación de control del caso 14, para validar las pruebas de referencia (ADR-0019).

No participa en la comparación: sirve para comprobar que las pruebas pasan con una implementación
que sigue la ficha y fallan con cada mutante de `mutantes.json`. Expone directamente la interfaz de
referencia, así que hace también de adaptador.
"""

import re
from collections import Counter
from datetime import date
from pathlib import Path

TIPOS = {"ESC", "CER", "PAZ"}
ANIO_MINIMO = 1950
PARTES = re.compile(r"^([A-Za-z]+)[-_ ](\d{4})[-_ ](\d{1,5})\.(\w+)$")


def _problema(nombre: str) -> str | None:
    partes = PARTES.match(nombre)
    if partes is None:
        return "No sigue la convención de nombres"
    tipo, anio, _, extension = partes.groups()
    if tipo.upper() not in TIPOS:
        return "Tipo desconocido"
    if not ANIO_MINIMO <= int(anio) <= date.today().year:
        return "Año fuera de rango"
    if extension.lower() != "pdf":
        return "Extensión distinta de pdf"
    return None


def _corregido(nombre: str) -> str:
    tipo, anio, consecutivo, _ = PARTES.match(nombre).groups()
    return f"{tipo.upper()}_{anio}_{int(consecutivo):05d}.pdf"


def _archivos(carpeta: str) -> list[str]:
    ruta = Path(carpeta)
    if not ruta.is_dir():
        raise FileNotFoundError("La carpeta no existe")
    return sorted(archivo.name for archivo in ruta.iterdir() if archivo.is_file())


def validar(carpeta: str) -> dict[str, str]:
    """Cada archivo que no cumple la convención, con su motivo."""
    motivos = {}
    for nombre in _archivos(carpeta):
        problema = _problema(nombre)
        if problema is not None:
            motivos[nombre] = problema
        elif nombre != _corregido(nombre):
            motivos[nombre] = "No sigue la convención de nombres"
    return motivos


def renombrar(carpeta: str, simulacion: bool) -> dict[str, str]:
    """Por cada archivo tratado, el nombre corregido o el texto del problema que se reporta."""
    cambios = {}
    nombres = _archivos(carpeta)
    for nombre in nombres:
        problema = _problema(nombre)
        if problema is not None:
            cambios[nombre] = problema
            continue
        nuevo = _corregido(nombre)
        if nuevo == nombre:
            continue
        if nuevo in nombres:
            cambios[nombre] = "Conflicto"
            continue
        cambios[nombre] = nuevo
        if not simulacion:
            (Path(carpeta) / nombre).rename(Path(carpeta) / nuevo)
    return cambios


def reporte(carpeta: str) -> tuple[dict[str, int], dict[str, int]]:
    """Cantidad de archivos por año y por tipo."""
    validos = [nombre for nombre in _archivos(carpeta) if _problema(nombre) is None]
    grupos = [PARTES.match(nombre).groups() for nombre in validos]
    por_anio = Counter(grupo[1] for grupo in grupos)
    por_tipo = Counter(grupo[0].upper() for grupo in grupos)
    return dict(por_anio), dict(por_tipo)


def codigo_de_salida(operacion: str, carpeta: str) -> int:
    """Ejecuta esa operación de la herramienta de terminal y devuelve su código de salida."""
    operaciones = {"validar": validar, "reporte": reporte}
    try:
        if operacion == "renombrar":
            renombrar(carpeta, False)
        else:
            operaciones[operacion](carpeta)
    except FileNotFoundError:
        return 1
    return 0
