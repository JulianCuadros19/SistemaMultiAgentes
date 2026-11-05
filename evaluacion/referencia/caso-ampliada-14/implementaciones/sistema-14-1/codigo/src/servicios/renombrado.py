"""Servicio de renombrado efectivo o simulado de escaneos."""

from dominio.convencion import (
    AnioFueraDeRango,
    CambioNombre,
    CarpetaNoExiste,
    ConflictoRenombrado,
    ErrorRenombrado,
    ExtensionInvalida,
    FormatoInvalido,
    TipoDesconocido,
    normalizar_nombre,
)
from entrada_salida.archivos import GestorArchivos


def renombrar_archivos(
    ruta: str, modo_simulacion: bool, gestor: GestorArchivos
) -> tuple[list[CambioNombre], list[ConflictoRenombrado], list[ErrorRenombrado]]:
    """Propone o aplica cambios sin sobrescribir archivos existentes.

    Args:
        ruta: Carpeta cuyos archivos se normalizan.
        modo_simulacion: True propone cambios; False los aplica.
        gestor: Adaptador de acceso a archivos.

    Returns:
        Cambios, conflictos y errores de dominio, respectivamente.

    Raises:
        CarpetaNoExiste: La carpeta no existe.
        TypeError: El modo de simulación no es booleano.
    """
    if not gestor.existe_carpeta(ruta):
        raise CarpetaNoExiste(f"La carpeta no existe: {ruta}")
    if not isinstance(modo_simulacion, bool):
        raise TypeError("El modo de simulación debe ser booleano")
    cambios: list[CambioNombre] = []
    conflictos: list[ConflictoRenombrado] = []
    errores: list[ErrorRenombrado] = []
    nombres = gestor.listar_archivos(ruta)
    ocupados = set(nombres)
    for anterior in nombres:
        try:
            nuevo = normalizar_nombre(anterior)
        except (FormatoInvalido, TipoDesconocido, AnioFueraDeRango, ExtensionInvalida) as error:
            errores.append(ErrorRenombrado(anterior, str(error)))
            continue
        if anterior == nuevo:
            continue
        if nuevo in ocupados:
            conflictos.append(ConflictoRenombrado(anterior, "Conflicto"))
            continue
        if not modo_simulacion:
            try:
                gestor.renombrar(ruta, anterior, nuevo)
            except FileExistsError:
                conflictos.append(ConflictoRenombrado(anterior, "Conflicto"))
                continue
        cambios.append(CambioNombre(anterior, nuevo))
        ocupados.add(nuevo)
        ocupados.discard(anterior)
    return cambios, conflictos, errores
