"""Servicio de reporte de archivos por año y tipo."""

from dominio.convencion import (
    AnioFueraDeRango,
    CarpetaNoExiste,
    ExtensionInvalida,
    FormatoInvalido,
    Reporte,
    TipoDesconocido,
    analizar_nombre,
)
from entrada_salida.archivos import GestorArchivos


def generar_reporte(ruta: str, gestor: GestorArchivos) -> Reporte:
    """Genera una línea por archivo y cuenta los nombres válidos.

    Args:
        ruta: Carpeta sobre la que se informa.
        gestor: Adaptador de acceso a archivos.

    Returns:
        Detalle de cada archivo, conteos por año y tipo y suma de los conteos.

    Raises:
        CarpetaNoExiste: La carpeta no existe.
    """
    if not gestor.existe_carpeta(ruta):
        raise CarpetaNoExiste(f"La carpeta no existe: {ruta}")
    lineas: list[str] = []
    conteos: dict[int, dict[str, int]] = {}
    total = 0
    for nombre in gestor.listar_archivos(ruta):
        try:
            estructura = analizar_nombre(nombre, None)
        except (FormatoInvalido, TipoDesconocido, AnioFueraDeRango, ExtensionInvalida) as error:
            lineas.append(f"{nombre}: Error: {error}")
            continue
        por_tipo = conteos.setdefault(estructura.anio, {})
        por_tipo[estructura.tipo] = por_tipo.get(estructura.tipo, 0) + 1
        total += 1
        lineas.append(f"{nombre}: año {estructura.anio}, tipo {estructura.tipo}")
    return Reporte(lineas, conteos, total)
