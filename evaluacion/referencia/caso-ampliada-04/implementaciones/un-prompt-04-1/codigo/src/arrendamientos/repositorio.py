"""Puerto de almacenamiento y adaptador atómico para pruebas en memoria."""

from collections.abc import Callable
from threading import Lock
from typing import Protocol

from arrendamientos.dominio import Contrato, Estado, RechazoContrato


class RepositorioContratos(Protocol):
    """Puerto que debe implementar cualquier almacenamiento de contratos.

    Las escrituras deben ser atómicas. ``actualizar`` debe impedir escrituras
    competidoras entre la lectura de los contratos y la persistencia del resultado,
    también cuando intervienen procesos o instancias diferentes del adaptador.
    """

    def agregar(self, contrato: Contrato) -> Contrato:
        """Inserta un borrador sin historial; rechaza códigos duplicados."""
        ...

    def obtener(self, codigo: str) -> Contrato:
        """Devuelve una instantánea inmutable o rechaza un código inexistente."""
        ...

    def actualizar(
        self,
        codigo: str,
        transformacion: Callable[[Contrato, tuple[Contrato, ...]], Contrato],
    ) -> Contrato:
        """Ejecuta y guarda una transformación dentro de una operación atómica.

        Entrega a la función el contrato actual y una vista completa y consistente
        de los contratos. Si la función falla, no persiste ningún cambio.
        """
        ...


class RepositorioEnMemoria:
    """Almacenamiento de proceso, seguro entre hilos que compartan esta instancia."""

    def __init__(self) -> None:
        """Crea un repositorio vacío con un bloqueo para lecturas y escrituras."""
        self._contratos: dict[str, Contrato] = {}
        self._bloqueo = Lock()

    def agregar(self, contrato: Contrato) -> Contrato:
        """Registra un borrador nuevo, sin permitir sobrescrituras ni importaciones."""
        with self._bloqueo:
            if contrato.codigo in self._contratos:
                raise RechazoContrato(f"Ya existe el contrato {contrato.codigo}")
            if contrato.estado != Estado.BORRADOR or contrato.historial:
                raise RechazoContrato("Solo se pueden registrar borradores nuevos sin historial")
            self._contratos[contrato.codigo] = contrato
            return contrato

    def _obtener(self, codigo: str) -> Contrato:
        try:
            return self._contratos[codigo]
        except KeyError as error:
            raise RechazoContrato(f"No existe el contrato {codigo}") from error

    def obtener(self, codigo: str) -> Contrato:
        """Obtiene un contrato inmutable o rechaza si el código no existe."""
        with self._bloqueo:
            return self._obtener(codigo)

    def actualizar(
        self,
        codigo: str,
        transformacion: Callable[[Contrato, tuple[Contrato, ...]], Contrato],
    ) -> Contrato:
        """Lee, transforma y persiste bajo un mismo bloqueo; falla sin escribir."""
        with self._bloqueo:
            actual = self._obtener(codigo)
            actualizado = transformacion(actual, tuple(self._contratos.values()))
            if (
                actualizado.codigo != actual.codigo
                or actualizado.codigo_inmueble != actual.codigo_inmueble
            ):
                raise RechazoContrato("Una transición no puede cambiar los códigos del contrato")
            self._contratos[codigo] = actualizado
            return actualizado
