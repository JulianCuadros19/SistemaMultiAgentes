"""Caso de uso de registro mediante colaboradores inyectados."""

from collections.abc import Callable
from datetime import date

from dominio.solicitud import (
    FechaDocumentoInvalida,
    PredioInexistente,
    SolicitudMutacion,
    TipoDocumentoInvalido,
    validar_fecha_documento_no_posterior,
    validar_identificacion,
    validar_numero_predial,
    validar_texto_obligatorio,
    validar_tipo_documento,
)

__all__ = [
    "FechaDocumentoInvalida",
    "PredioInexistente",
    "SolicitudMutacion",
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
    """Valida, asigna un radicado y guarda la solicitud en trámite.

    Args:
        numero_predial: Número de 30 dígitos existente en la base catastral.
        tipo_documento_soporte: Escritura pública o sentencia judicial.
        fecha_documento_soporte: Fecha no posterior a la radicación.
        identificacion_nuevo_propietario: Identificación de entre 6 y 10 dígitos.
        nombre_completo_nuevo_propietario: Nombre completo obligatorio.
        generar_radicado: Colaborador que entrega un radicado para la fecha indicada.
        predio_existe: Colaborador que consulta la existencia del predio.
        guardar_solicitud: Colaborador que persiste la solicitud válida.
        fecha_radicacion: Fecha explícita; si se omite, se utiliza date.today().

    Returns:
        Solicitud guardada con radicado y estado en trámite.

    Raises:
        PredioInexistente: Si el número predial es inválido o no existe.
        TipoDocumentoInvalido: Si hay datos textuales o colaboradores inválidos.
        FechaDocumentoInvalida: Si las fechas son inválidas o inconsistentes.
    """
    validar_numero_predial(numero_predial)
    validar_tipo_documento(tipo_documento_soporte)
    fecha = date.today() if fecha_radicacion is None else fecha_radicacion
    validar_fecha_documento_no_posterior(fecha_documento_soporte, fecha)
    validar_identificacion(identificacion_nuevo_propietario)
    validar_texto_obligatorio(nombre_completo_nuevo_propietario, "nombre completo")
    if not all(callable(valor) for valor in (generar_radicado, predio_existe, guardar_solicitud)):
        raise TipoDocumentoInvalido("Los colaboradores deben ser invocables.")
    if not predio_existe(numero_predial):
        raise PredioInexistente("El predio no existe en la base catastral.")
    solicitud = SolicitudMutacion(
        numero_predial=numero_predial,
        tipo_documento_soporte=tipo_documento_soporte,
        fecha_documento_soporte=fecha_documento_soporte,
        identificacion_nuevo_propietario=identificacion_nuevo_propietario,
        nombre_completo_nuevo_propietario=nombre_completo_nuevo_propietario,
        fecha_radicacion=fecha,
        radicado=generar_radicado(fecha),
        estado="en trámite",
    )
    guardar_solicitud(solicitud)
    return solicitud
