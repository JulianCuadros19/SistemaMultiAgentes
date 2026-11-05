"""Servicio independiente de revisión de una carpeta."""

from entrada_salida.archivos import CarpetaNoExiste, GestorArchivos


def revisar_carpeta(ruta: str, gestor: GestorArchivos) -> list[str]:
    """Comprueba la carpeta y devuelve sus archivos.

    Args:
        ruta: Carpeta que se revisa.
        gestor: Adaptador de acceso a archivos.

    Returns:
        Nombres de los archivos encontrados.

    Raises:
        CarpetaNoExiste: La ruta no identifica una carpeta existente.
    """
    if not gestor.existe_carpeta(ruta):
        raise CarpetaNoExiste(f"La carpeta no existe: {ruta}")
    return gestor.listar_archivos(ruta)
