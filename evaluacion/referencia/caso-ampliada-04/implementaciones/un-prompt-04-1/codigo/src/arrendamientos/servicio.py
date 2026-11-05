"""Casos de uso que coordinan reglas puras, reloj y almacenamiento."""

from collections.abc import Callable
from datetime import date, datetime, timezone

from arrendamientos.dominio import Contrato, Estado, cambiar_estado
from arrendamientos.repositorio import RepositorioContratos


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


class ServicioContratos:
    """Gestiona contratos mediante un puerto de persistencia intercambiable."""

    def __init__(
        self,
        repositorio: RepositorioContratos,
        reloj: Callable[[], datetime] = _ahora,
    ) -> None:
        """Recibe el almacenamiento y, opcionalmente, un reloj para pruebas."""
        self._repositorio = repositorio
        self._reloj = reloj

    def registrar(self, contrato: Contrato) -> Contrato:
        """Registra un borrador nuevo; la creación no es un cambio de estado."""
        return self._repositorio.agregar(contrato)

    def obtener(self, codigo: str) -> Contrato:
        """Consulta un contrato por su código o produce un rechazo si no existe."""
        return self._repositorio.obtener(codigo)

    def cambiar_estado(
        self,
        codigo: str,
        nuevo_estado: Estado,
        usuario: str,
        *,
        motivo: str | None = None,
        fecha_terminacion: date | None = None,
    ) -> Contrato:
        """Valida y persiste atómicamente un cambio, o lanza RechazoContrato.

        El rechazo no modifica el contrato ni añade entradas a su historial.
        """
        def transformar(actual: Contrato, contratos: tuple[Contrato, ...]) -> Contrato:
            return cambiar_estado(
                actual,
                nuevo_estado,
                usuario,
                self._reloj(),
                contratos=contratos,
                motivo=motivo,
                fecha_terminacion=fecha_terminacion,
            )

        return self._repositorio.actualizar(codigo, transformar)
