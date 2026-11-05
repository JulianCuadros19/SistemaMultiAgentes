"""Entidades y contratos del seguimiento de cambios de estado."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class AvisoCambioEstado:
    """Aviso inmutable de una transición.

    Args:
        numero_tramite: Identificador no vacío.
        tipo_tramite: Tipo no vacío.
        estado_anterior: Estado antes del cambio.
        estado_nuevo: Estado después del cambio.
        fecha_hora: Fecha y hora local.
        funcionario: Identificador no vacío del funcionario.
        es_valida: Validez según las transiciones permitidas.

    Raises:
        ValueError: Los datos no cumplen las restricciones del aviso.
    """

    numero_tramite: str
    tipo_tramite: str
    estado_anterior: str
    estado_nuevo: str
    fecha_hora: datetime
    funcionario: str
    es_valida: bool

    def __post_init__(self) -> None:
        """Valida los datos antes de que el aviso pueda publicarse."""
        for valor in (self.numero_tramite, self.tipo_tramite, self.funcionario):
            if not isinstance(valor, str) or not valor.strip():
                raise ValueError("Los identificadores y el tipo deben ser textos no vacíos.")
        estados = ("radicado", "en revisión", "aprobado", "rechazado")
        for estado in (self.estado_anterior, self.estado_nuevo):
            if not isinstance(estado, str) or estado not in estados:
                raise ValueError("El estado no pertenece al conjunto esperado.")
        if not isinstance(self.fecha_hora, datetime):
            raise ValueError("La fecha y hora debe ser datetime.")
        permitidas = (
            ("radicado", "en revisión"),
            ("en revisión", "aprobado"),
            ("en revisión", "rechazado"),
        )
        valida = (self.estado_anterior, self.estado_nuevo) in permitidas
        if not isinstance(self.es_valida, bool) or self.es_valida != valida:
            raise ValueError("La marca de validez no coincide con la transición.")


@dataclass(frozen=True)
class AsientoBitacora:
    """Datos de un aviso almacenados en la bitácora.

    Args:
        numero_tramite: Identificador del trámite.
        tipo_tramite: Tipo del trámite.
        estado_anterior: Estado antes del cambio.
        estado_nuevo: Estado después del cambio.
        fecha_hora: Fecha y hora del aviso.
        funcionario: Funcionario que registró el cambio.
        transicion_valida: Marca de validez de la transición.
    """

    numero_tramite: str
    tipo_tramite: str
    estado_anterior: str
    estado_nuevo: str
    fecha_hora: datetime
    funcionario: str
    transicion_valida: bool


@dataclass(frozen=True)
class MensajeCiudadano:
    """Mensaje preparado para un trámite.

    Args:
        numero_tramite: Identificador del trámite.
        texto: Contenido en español.
    """

    numero_tramite: str
    texto: str


class CanalEventos(ABC):
    """Contrato de publicación diferida y entrega de avisos."""

    @abstractmethod
    def suscribir(self, manejador: Callable[[AvisoCambioEstado], None]) -> None:
        """Suscribe un receptor.

        Args:
            manejador: Función que recibe cada aviso al despachar.
        """
        raise NotImplementedError("El canal debe implementar la suscripción.")

    @abstractmethod
    def publicar(self, aviso: AvisoCambioEstado) -> None:
        """Encola un aviso sin ejecutar receptores.

        Args:
            aviso: Evento que se entregará posteriormente.
        """
        raise NotImplementedError("El canal debe implementar la publicación.")

    @abstractmethod
    def obtener_pendientes(self) -> list[AvisoCambioEstado]:
        """Consulta la cola.

        Returns:
            Copia de los avisos pendientes.
        """
        raise NotImplementedError("El canal debe implementar la consulta.")

    @abstractmethod
    def despachar_pendientes(self) -> None:
        """Entrega avisos a todos los receptores, aislando sus fallos."""
        raise NotImplementedError("El canal debe implementar la entrega.")


class RegistroBitacora(ABC):
    """Contrato de almacenamiento de asientos."""

    @abstractmethod
    def registrar(self, asiento: AsientoBitacora) -> None:
        """Guarda un asiento.

        Args:
            asiento: Datos del aviso recibido.
        """
        raise NotImplementedError("El registro debe implementar el almacenamiento.")

    @abstractmethod
    def consultar_por_tramite(self, numero_tramite: str) -> list[AsientoBitacora]:
        """Consulta los asientos de un trámite.

        Args:
            numero_tramite: Identificador buscado.

        Returns:
            Asientos en orden de registro.
        """
        raise NotImplementedError("El registro debe implementar la consulta.")


class RegistroIndicadores(ABC):
    """Contrato de almacenamiento de tiempos y promedios."""

    @abstractmethod
    def registrar_dias(self, numero_tramite: str, tipo_tramite: str, dias_habiles: int) -> None:
        """Registra el tiempo de un trámite.

        Args:
            numero_tramite: Identificador del trámite.
            tipo_tramite: Tipo para agrupar el promedio.
            dias_habiles: Tiempo calculado en días hábiles.
        """
        raise NotImplementedError("El registro debe implementar el almacenamiento.")

    @abstractmethod
    def consultar_dias_calculados(self, numero_tramite: str) -> int | None:
        """Consulta un cálculo.

        Args:
            numero_tramite: Identificador buscado.

        Returns:
            Días registrados o None si no hay cálculo.
        """
        raise NotImplementedError("El registro debe implementar la consulta.")

    @abstractmethod
    def promedio_por_tipo(self, tipo_tramite: str) -> Decimal:
        """Consulta el promedio por tipo.

        Args:
            tipo_tramite: Tipo buscado.

        Returns:
            Promedio decimal, o cero si no hay datos.
        """
        raise NotImplementedError("El registro debe implementar el promedio.")


class RegistroFechasTramite(ABC):
    """Contrato de almacenamiento de fechas de radicación."""

    @abstractmethod
    def registrar_radicado(self, numero_tramite: str, fecha: date) -> None:
        """Guarda la fecha de radicación.

        Args:
            numero_tramite: Identificador del trámite.
            fecha: Fecha de radicación.
        """
        raise NotImplementedError("El registro debe implementar el almacenamiento.")

    @abstractmethod
    def obtener_fecha_radicado(self, numero_tramite: str) -> date | None:
        """Consulta la fecha de radicación.

        Args:
            numero_tramite: Identificador buscado.

        Returns:
            Fecha registrada o None si no existe.
        """
        raise NotImplementedError("El registro debe implementar la consulta.")


class RegistroMensajes(ABC):
    """Contrato de almacenamiento de mensajes al ciudadano."""

    @abstractmethod
    def registrar(self, mensaje: MensajeCiudadano) -> None:
        """Guarda un mensaje.

        Args:
            mensaje: Mensaje generado.
        """
        raise NotImplementedError("El registro debe implementar el almacenamiento.")

    @abstractmethod
    def consultar_por_tramite(self, numero_tramite: str) -> list[MensajeCiudadano]:
        """Consulta mensajes de un trámite.

        Args:
            numero_tramite: Identificador buscado.

        Returns:
            Mensajes en orden de registro.
        """
        raise NotImplementedError("El registro debe implementar la consulta.")
