"""Traza de cada nodo del grafo: tiempo, llamadas al modelo, costo y error (RF-34, ADR-0016).

El grafo informa cada ejecución de un nodo a un observador. Las interfaces usan la traza en
PostgreSQL (`persistencia.ejecuciones`); las pruebas, la que vive en memoria. Las pausas no se
informan: un nodo que espera a una persona se informa cuando termina, con el tiempo que tardó
después de la respuesta.
"""

from datetime import datetime
from decimal import Decimal
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from multiagente.llm.traza import RegistroLlamada


class EjecucionNodo(BaseModel):
    """Una ejecución de un nodo del grafo, con las llamadas al modelo que hizo.

    Attributes:
        sesion: Sesión a la que pertenece.
        nodo: Nodo del grafo, como `n10_generacion`.
        inicio: Cuándo empezó, después de cualquier pausa.
        duracion_ms: Cuánto tardó.
        llamadas: Llamadas al modelo del nodo, en orden.
        error: Si el nodo falló, el tipo y el mensaje de la excepción.
    """

    model_config = ConfigDict(frozen=True)

    sesion: str
    nodo: str
    inicio: datetime
    duracion_ms: int
    llamadas: tuple[RegistroLlamada, ...] = ()
    error: str | None = None

    @property
    def costo_usd(self) -> Decimal:
        """Costo de las llamadas del nodo."""
        return sum((llamada.costo_usd for llamada in self.llamadas), Decimal(0))


class ObservadorNodos(Protocol):
    """Destino de la traza de los nodos del grafo."""

    def registrar_nodo(self, ejecucion: EjecucionNodo) -> None:
        """Guarda la ejecución de un nodo."""
        ...


class TrazaDeNodos(ObservadorNodos, Protocol):
    """Traza de los nodos que además se consulta por sesión, como la de las interfaces."""

    def consultar(self, sesion: str) -> list[EjecucionNodo]:
        """Devuelve las ejecuciones de una sesión, en el orden en que ocurrieron."""
        ...


class TrazaEnMemoria:
    """Guarda la traza de los nodos en memoria, para las pruebas."""

    def __init__(self) -> None:
        """Crea la traza vacía."""
        self.ejecuciones: list[EjecucionNodo] = []

    def registrar_nodo(self, ejecucion: EjecucionNodo) -> None:
        """Agrega la ejecución de un nodo.

        Args:
            ejecucion: Ejecución del nodo.
        """
        self.ejecuciones.append(ejecucion)

    def consultar(self, sesion: str) -> list[EjecucionNodo]:
        """Devuelve las ejecuciones de una sesión, en el orden en que ocurrieron.

        Args:
            sesion: Identificador de la sesión.

        Returns:
            Las ejecuciones de esa sesión.
        """
        return [ejecucion for ejecucion in self.ejecuciones if ejecucion.sesion == sesion]
