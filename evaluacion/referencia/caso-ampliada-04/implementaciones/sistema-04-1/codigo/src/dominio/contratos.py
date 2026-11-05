"""Entidades, resultados, excepciones y puerto de los contratos de arrendamiento."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class Contrato:
    """Representa los datos de un contrato, incluidos los borradores incompletos.

    Args:
        codigo: Identificador del contrato.
        inmueble: Código del inmueble.
        fecha_inicio: Inicio del periodo.
        fecha_fin: Fin del periodo.
        documento_arrendatario: Documento, que puede faltar en un borrador.
        canon_mensual: Canon expresado mediante Decimal.
        estado: Borrador, vigente, terminado o anulado.
    """

    codigo: str
    inmueble: str
    fecha_inicio: date
    fecha_fin: date
    documento_arrendatario: str | None
    canon_mensual: Decimal
    estado: str


@dataclass(frozen=True)
class CambioEstado:
    """Resultado de un cambio de estado.

    Args:
        fecha_cambio: Fecha en que se registró el cambio.
        usuario: Usuario que realizó el cambio.
        contrato: Contrato con su nuevo estado.
    """

    fecha_cambio: date
    usuario: str
    contrato: Contrato


class _ErrorNegocio(ValueError):
    _mensaje: str = "Operación no permitida"

    def __init__(self) -> None:
        super().__init__(self._mensaje)


class DocumentoArrendatarioObligatorio(_ErrorNegocio):
    """Indica que falta el documento necesario para activar el contrato."""

    _mensaje = "El documento del arrendatario es obligatorio"


class CanonInvalido(_ErrorNegocio):
    """Indica que el canon no es un entero positivo en pesos."""

    _mensaje = "El canon mensual debe ser mayor que cero y en pesos sin decimales"


class FechasInvalidas(_ErrorNegocio):
    """Indica que el periodo no cumple las condiciones de activación."""

    _mensaje = "La fecha de fin debe ser posterior al inicio y la duración mínima es seis meses"


class CruceDeVigencias(_ErrorNegocio):
    """Indica que existe otro contrato vigente en el mismo inmueble y periodo."""

    _mensaje = "El inmueble ya tiene un contrato vigente en ese periodo"


class TransicionNoPermitida(_ErrorNegocio):
    """Indica que la solicitud no permite una transición válida."""

    _mensaje = "La transición solicitada no está permitida"


class EstadoNoModificable(_ErrorNegocio):
    """Indica que el contrato tiene un estado final no modificable."""

    _mensaje = "El estado actual del contrato no permite modificaciones"


class MotivoObligatorio(_ErrorNegocio):
    """Indica que falta el motivo de terminación."""

    _mensaje = "El motivo es obligatorio para terminar un contrato"


class FechaTerminacionFueraDePeriodo(_ErrorNegocio):
    """Indica que la fecha de terminación no pertenece al periodo contractual."""

    _mensaje = "La fecha de terminación debe estar dentro del periodo del contrato"


class RepositorioContratos(ABC):
    """Define el puerto de almacenamiento y consulta de contratos."""

    @abstractmethod
    def registrar(self, contrato: Contrato) -> None:
        """Registra los datos iniciales de un contrato.

        Args:
            contrato: Contrato que se registra.
        """

    @abstractmethod
    def consultar_por_codigo(self, codigo: str) -> Contrato:
        """Consulta un contrato registrado.

        Args:
            codigo: Identificador del contrato.

        Returns:
            Contrato correspondiente al código.
        """

    @abstractmethod
    def existe_vigencia_en_inmueble(self, inmueble: str, desde: date, hasta: date) -> bool:
        """Consulta si existe una vigencia que intersecta el periodo cerrado.

        Args:
            inmueble: Código del inmueble.
            desde: Inicio del periodo consultado.
            hasta: Fin del periodo consultado.

        Returns:
            Si existe al menos un contrato vigente que se cruza con el periodo.
        """

    @abstractmethod
    def actualizar(self, contrato: Contrato) -> None:
        """Persiste los nuevos datos de un contrato existente.

        Args:
            contrato: Contrato actualizado.
        """
