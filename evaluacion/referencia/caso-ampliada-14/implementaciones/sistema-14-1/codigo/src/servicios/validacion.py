"""Servicio independiente de validación de nombres de escaneos."""

from dominio.convencion import (
    AnioFueraDeRango,
    CarpetaNoExiste,
    ExtensionInvalida,
    FormatoInvalido,
    ResultadoValidacion,
    TipoDesconocido,
    analizar_nombre,
)
from entrada_salida.archivos import GestorArchivos


def validar_nombres(
    ruta: str, gestor: GestorArchivos
) -> tuple[list[ResultadoValidacion], dict[str, int]]:
    """Lista los incumplimientos y suma sus motivos.

    Args:
        ruta: Carpeta que se valida.
        gestor: Adaptador de acceso a archivos.

    Returns:
        Incumplimientos y totales agrupados por el texto del motivo.

    Raises:
        CarpetaNoExiste: La carpeta no existe.
    """
    if not gestor.existe_carpeta(ruta):
        raise CarpetaNoExiste(f"La carpeta no existe: {ruta}")
    resultados: list[ResultadoValidacion] = []
    totales: dict[str, int] = {}
    for nombre in gestor.listar_archivos(ruta):
        try:
            analizar_nombre(nombre, None)
        except (FormatoInvalido, TipoDesconocido, AnioFueraDeRango, ExtensionInvalida) as error:
            motivo = str(error)
            resultados.append(ResultadoValidacion(nombre, motivo))
            totales[motivo] = totales.get(motivo, 0) + 1
    return resultados, totales
