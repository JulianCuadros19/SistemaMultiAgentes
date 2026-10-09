"""Entidad y validaciones para solicitudes de mutación de propietario."""

import re
from dataclasses import dataclass
from datetime import date


class PredioInexistente(ValueError):
    """El número predial es inválido o no existe en la base catastral."""


class TipoDocumentoInvalido(ValueError):
    """Los datos textuales de la solicitud o del documento son inválidos."""


class FechaDocumentoInvalida(ValueError):
    """Las fechas son inválidas o el documento es posterior a la radicación."""


def validar_numero_predial(numero_predial: str) -> None:
    """Valida que el número predial tenga exactamente 30 dígitos.

    Args:
        numero_predial: Número predial del predio.

    Raises:
        PredioInexistente: Si no tiene 30 dígitos.
    """
    if not isinstance(numero_predial, str) or re.fullmatch(r"[0-9]{30}", numero_predial) is None:
        raise PredioInexistente("El número predial debe contener exactamente 30 dígitos.")


def validar_texto_obligatorio(valor: str, campo: str) -> None:
    """Valida que un campo obligatorio sea un texto no vacío.

    Args:
        valor: Valor del campo.
        campo: Nombre del campo, para el mensaje de error.

    Raises:
        TipoDocumentoInvalido: Si el valor está vacío o no es texto.
    """
    if not isinstance(valor, str) or not valor.strip():
        raise TipoDocumentoInvalido(f"El campo {campo} es obligatorio y debe ser texto.")


def validar_identificacion(identificacion: str) -> None:
    """Valida que la identificación tenga solo dígitos, entre 6 y 10.

    Args:
        identificacion: Identificación del nuevo propietario.

    Raises:
        TipoDocumentoInvalido: Si no cumple el formato.
    """
    if not isinstance(identificacion, str) or re.fullmatch(r"[0-9]{6,10}", identificacion) is None:
        raise TipoDocumentoInvalido(
            "La identificación del nuevo propietario debe contener solo dígitos, entre 6 y 10."
        )


def validar_tipo_documento(tipo_documento_soporte: str) -> None:
    """Valida el tipo de documento soporte sin normalizarlo.

    Args:
        tipo_documento_soporte: Tipo de documento recibido.

    Raises:
        TipoDocumentoInvalido: Si no es escritura pública ni sentencia judicial.
    """
    if not isinstance(tipo_documento_soporte, str) or tipo_documento_soporte not in (
        "escritura pública", "sentencia judicial"
    ):
        raise TipoDocumentoInvalido(
            "El documento soporte debe ser escritura pública o sentencia judicial."
        )


def validar_fecha_documento_no_posterior(
    fecha_documento_soporte: date, fecha_radicacion: date
) -> None:
    """Valida las fechas y permite documentos del mismo día de radicación.

    Args:
        fecha_documento_soporte: Fecha del documento soporte.
        fecha_radicacion: Fecha de radicación de la solicitud.

    Raises:
        FechaDocumentoInvalida: Si alguna fecha es inválida o el documento es posterior.
    """
    if type(fecha_documento_soporte) is not date or type(fecha_radicacion) is not date:
        raise FechaDocumentoInvalida("Las fechas deben ser valores date, sin hora.")
    if fecha_documento_soporte > fecha_radicacion:
        raise FechaDocumentoInvalida("El documento no puede ser posterior a la radicación.")


@dataclass(frozen=True)
class SolicitudMutacion:
    """Solicitud registrada con sus invariantes básicas.

    Args:
        numero_predial: Número predial de 30 dígitos.
        tipo_documento_soporte: Escritura pública o sentencia judicial.
        fecha_documento_soporte: Fecha del documento soporte.
        identificacion_nuevo_propietario: Identificación de entre 6 y 10 dígitos.
        nombre_completo_nuevo_propietario: Nombre obligatorio del nuevo propietario.
        fecha_radicacion: Fecha de radicación.
        radicado: Identificador RAD-AAAA-XXXXXX del año de radicación.
        estado: Estado inicial en trámite.

    Raises:
        PredioInexistente: Si el número predial tiene formato inválido.
        TipoDocumentoInvalido: Si los datos textuales son inválidos.
        FechaDocumentoInvalida: Si las fechas incumplen las restricciones.
    """

    numero_predial: str
    tipo_documento_soporte: str
    fecha_documento_soporte: date
    identificacion_nuevo_propietario: str
    nombre_completo_nuevo_propietario: str
    fecha_radicacion: date
    radicado: str
    estado: str

    def __post_init__(self) -> None:
        """Comprueba las invariantes al construir la solicitud.

        Raises:
            PredioInexistente: Si el número predial tiene formato inválido.
            TipoDocumentoInvalido: Si hay datos textuales inválidos.
            FechaDocumentoInvalida: Si las fechas no son válidas.
        """
        validar_numero_predial(self.numero_predial)
        validar_tipo_documento(self.tipo_documento_soporte)
        validar_fecha_documento_no_posterior(
            self.fecha_documento_soporte, self.fecha_radicacion
        )
        validar_identificacion(self.identificacion_nuevo_propietario)
        validar_texto_obligatorio(self.nombre_completo_nuevo_propietario, "nombre completo")
        patron = rf"RAD-{self.fecha_radicacion.year:04d}-[0-9]{{6}}"
        if not isinstance(self.radicado, str) or re.fullmatch(patron, self.radicado) is None:
            raise TipoDocumentoInvalido("El radicado debe tener formato RAD-AAAA-XXXXXX.")
        if self.estado != "en trámite":
            raise TipoDocumentoInvalido("El estado inicial debe ser en trámite.")
