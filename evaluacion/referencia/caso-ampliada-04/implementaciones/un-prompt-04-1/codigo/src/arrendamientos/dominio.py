"""Modelo inmutable y reglas independientes del almacenamiento y del reloj."""

from calendar import monthrange
from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import date, datetime
from enum import StrEnum


class RechazoContrato(ValueError):
    """Rechazo de una operación; su representación textual contiene el motivo."""


class Estado(StrEnum):
    """Estados posibles de un contrato."""

    BORRADOR = "borrador"
    VIGENTE = "vigente"
    TERMINADO = "terminado"
    ANULADO = "anulado"


@dataclass(frozen=True, slots=True)
class CambioEstado:
    """Registro inmutable de una transición y de quién la realizó."""

    estado_anterior: Estado
    estado_nuevo: Estado
    momento: datetime
    usuario: str
    motivo: str | None = None
    fecha_terminacion: date | None = None


@dataclass(frozen=True, slots=True)
class Contrato:
    """Datos del contrato; un borrador puede tener datos de activación pendientes."""

    codigo: str
    codigo_inmueble: str
    documento_arrendatario: str | None = None
    canon_mensual: int | None = None
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    estado: Estado = Estado.BORRADOR
    historial: tuple[CambioEstado, ...] = ()
    motivo_terminacion: str | None = None
    fecha_terminacion: date | None = None

    def __post_init__(self) -> None:
        """Comprueba identificadores y tipos, sin exigir un borrador completo."""
        _exigir_texto(self.codigo, "El código del contrato es obligatorio")
        _exigir_texto(self.codigo_inmueble, "El código del inmueble es obligatorio")
        _validar_tipos_datos(self)
        if not isinstance(self.estado, Estado):
            raise RechazoContrato("El estado debe ser un valor de Estado")
        if not isinstance(self.historial, tuple) or not all(
            isinstance(cambio, CambioEstado) for cambio in self.historial
        ):
            raise RechazoContrato("El historial debe ser una tupla de cambios de estado")


def _exigir_texto(valor: str | None, mensaje: str) -> None:
    if not isinstance(valor, str) or not valor.strip():
        raise RechazoContrato(mensaje)


def _validar_fecha_opcional(valor: date | None, nombre: str) -> None:
    if valor is not None and type(valor) is not date:
        raise RechazoContrato(f"{nombre} debe ser una fecha sin hora")


def _validar_tipos_datos(contrato: Contrato) -> None:
    if contrato.documento_arrendatario is not None and not isinstance(
        contrato.documento_arrendatario, str
    ):
        raise RechazoContrato("El documento del arrendatario debe ser texto")
    if contrato.canon_mensual is not None and type(contrato.canon_mensual) is not int:
        raise RechazoContrato("El canon mensual debe ser un entero en pesos sin decimales")
    _validar_fecha_opcional(contrato.fecha_inicio, "La fecha de inicio")
    _validar_fecha_opcional(contrato.fecha_fin, "La fecha de fin")
    _validar_fecha_opcional(contrato.fecha_terminacion, "La fecha de terminación")


def _seis_meses_despues(inicio: date) -> date:
    indice_mes = inicio.month - 1 + 6
    anio = inicio.year + indice_mes // 12
    mes = indice_mes % 12 + 1
    if anio > date.max.year:
        raise RechazoContrato("El periodo no permite una duración mínima de seis meses")
    dia = min(inicio.day, monthrange(anio, mes)[1])
    return date(anio, mes, dia)


def _validar_periodo(contrato: Contrato) -> tuple[date, date]:
    inicio, fin = contrato.fecha_inicio, contrato.fecha_fin
    if inicio is None or fin is None:
        raise RechazoContrato("Para activar se requieren las fechas de inicio y fin")
    if fin <= inicio:
        raise RechazoContrato("La fecha de fin debe ser posterior a la de inicio")
    if fin < _seis_meses_despues(inicio):
        raise RechazoContrato("La duración mínima del contrato es de seis meses")
    return inicio, fin


def _validar_solapamiento(
    contrato: Contrato,
    inicio: date,
    fin: date,
    contratos: Iterable[Contrato],
) -> None:
    for otro in contratos:
        if (
            otro.codigo == contrato.codigo
            or otro.codigo_inmueble != contrato.codigo_inmueble
            or otro.estado != Estado.VIGENTE
        ):
            continue
        if otro.fecha_inicio is None or otro.fecha_fin is None:
            raise RechazoContrato(f"El contrato vigente {otro.codigo} tiene un periodo incompleto")
        if inicio <= otro.fecha_fin and otro.fecha_inicio <= fin:
            raise RechazoContrato("El inmueble ya tiene un contrato vigente en ese periodo")


def _validar_activacion(contrato: Contrato, contratos: Iterable[Contrato]) -> None:
    _exigir_texto(
        contrato.documento_arrendatario,
        "Para activar se requiere el documento del arrendatario",
    )
    if contrato.canon_mensual is None or contrato.canon_mensual <= 0:
        raise RechazoContrato("Para activar el canon mensual debe ser mayor que cero")
    inicio, fin = _validar_periodo(contrato)
    _validar_solapamiento(contrato, inicio, fin, contratos)


def _validar_terminacion(
    contrato: Contrato,
    motivo: str | None,
    fecha_terminacion: date | None,
) -> None:
    _exigir_texto(motivo, "Para terminar se requiere un motivo")
    _validar_fecha_opcional(fecha_terminacion, "La fecha de terminación")
    if fecha_terminacion is None:
        raise RechazoContrato("Para terminar se requiere una fecha de terminación")
    inicio, fin = contrato.fecha_inicio, contrato.fecha_fin
    if inicio is None or fin is None:
        raise RechazoContrato("El contrato vigente tiene un periodo incompleto")
    if not inicio <= fecha_terminacion <= fin:
        raise RechazoContrato("La fecha de terminación debe estar dentro del periodo del contrato")


_TRANSICIONES = {
    Estado.BORRADOR: frozenset({Estado.VIGENTE, Estado.ANULADO}),
    Estado.VIGENTE: frozenset({Estado.TERMINADO}),
    Estado.TERMINADO: frozenset(),
    Estado.ANULADO: frozenset(),
}


def cambiar_estado(
    contrato: Contrato,
    nuevo_estado: Estado,
    usuario: str,
    momento: datetime,
    *,
    contratos: Iterable[Contrato] = (),
    motivo: str | None = None,
    fecha_terminacion: date | None = None,
) -> Contrato:
    """Valida una transición y devuelve una copia con el cambio registrado.

    Args:
        contrato: Contrato original, que no se modifica.
        nuevo_estado: Estado solicitado.
        usuario: Identificación no vacía de quien realiza el cambio.
        momento: Fecha y hora del registro, proporcionadas por el llamador.
        contratos: Vista completa de los posibles contratos competidores.
        motivo: Motivo exigido para terminar.
        fecha_terminacion: Fecha efectiva exigida para terminar.

    Returns:
        Contrato inmutable con el nuevo estado y el historial ampliado.

    Raises:
        RechazoContrato: Si la transición o sus datos incumplen una regla.
    """
    if not isinstance(nuevo_estado, Estado):
        raise RechazoContrato("El estado solicitado debe ser un valor de Estado")
    if nuevo_estado not in _TRANSICIONES[contrato.estado]:
        raise RechazoContrato(
            f"Transición no permitida: estado actual {contrato.estado.value}; "
            f"estado solicitado {nuevo_estado.value}"
        )
    _exigir_texto(usuario, "El usuario que hace el cambio es obligatorio")
    if not isinstance(momento, datetime):
        raise RechazoContrato("El momento del cambio debe ser una fecha y hora")
    if nuevo_estado == Estado.VIGENTE:
        _validar_activacion(contrato, contratos)
    if nuevo_estado == Estado.TERMINADO:
        _validar_terminacion(contrato, motivo, fecha_terminacion)
    es_terminacion = nuevo_estado == Estado.TERMINADO
    cambio = CambioEstado(
        estado_anterior=contrato.estado,
        estado_nuevo=nuevo_estado,
        momento=momento,
        usuario=usuario,
        motivo=motivo if es_terminacion else None,
        fecha_terminacion=fecha_terminacion if es_terminacion else None,
    )
    return replace(
        contrato,
        estado=nuevo_estado,
        historial=(*contrato.historial, cambio),
        motivo_terminacion=motivo if es_terminacion else contrato.motivo_terminacion,
        fecha_terminacion=(
            fecha_terminacion if es_terminacion else contrato.fecha_terminacion
        ),
    )
