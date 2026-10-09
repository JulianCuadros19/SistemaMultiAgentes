"""Adaptador de entrada para registrar solicitudes de mutación."""

from collections.abc import Callable
from datetime import date

from aplicacion.registro_mutacion import (
    FechaDocumentoInvalida,
    PredioInexistente,
    SolicitudMutacion,
    TipoDocumentoInvalido,
)
from aplicacion.registro_mutacion import (
    registrar_solicitud_mutacion as _registrar_solicitud_mutacion,
)

__all__ = [
    "FechaDocumentoInvalida",
    "PredioInexistente",
    "TipoDocumentoInvalido",
    "registrar_solicitud_mutacion",
]


def registrar_solicitud_mutacion(
    numero_predial: str,
    tipo_documento_soporte: str,
    fecha_documento_soporte: date,
    identificacion_nuevo_propietario: str,
    nombre_completo_nuevo_propietario: str,
    generar_radicado: Callable[[date], str],
    predio_existe: Callable[[str], bool],
    guardar_solicitud: Callable[[SolicitudMutacion], None],
    fecha_radicacion: date | None = None,
) -> SolicitudMutacion:
    """Delega el registro y sus validaciones en el caso de uso.

    Args:
        numero_predial: Número de 30 dígitos del predio.
        tipo_documento_soporte: Tipo permitido de documento soporte.
        fecha_documento_soporte: Fecha del documento soporte.
        identificacion_nuevo_propietario: Identificación obligatoria del propietario.
        nombre_completo_nuevo_propietario: Nombre completo obligatorio del propietario.
        generar_radicado: Generador de radicados por fecha.
        predio_existe: Consulta de existencia del predio.
        guardar_solicitud: Persistencia inyectada de la solicitud.
        fecha_radicacion: Fecha explícita o None para utilizar la fecha actual.

    Returns:
        Solicitud registrada en trámite.

    Raises:
        PredioInexistente: Si el predio es inválido o inexistente.
        TipoDocumentoInvalido: Si los datos textuales o colaboradores son inválidos.
        FechaDocumentoInvalida: Si las fechas son inválidas o inconsistentes.
    """
    return _registrar_solicitud_mutacion(
        numero_predial,
        tipo_documento_soporte,
        fecha_documento_soporte,
        identificacion_nuevo_propietario,
        nombre_completo_nuevo_propietario,
        generar_radicado,
        predio_existe,
        guardar_solicitud,
        fecha_radicacion,
    )
