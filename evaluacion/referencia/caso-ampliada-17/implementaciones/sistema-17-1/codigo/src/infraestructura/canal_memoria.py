"""Canal en memoria con publicación diferida y aislamiento de fallos."""

import logging
from collections import deque
from collections.abc import Callable

from eventos.aviso import AvisoCambioEstado, CanalEventos


class CanalEventosMemoria(CanalEventos):
    """Cola y suscriptores independientes para cada instancia."""

    def __init__(self) -> None:
        """Inicializa una cola vacía y sin suscriptores."""
        self._pendientes: deque[AvisoCambioEstado] = deque()
        self._manejadores: list[Callable[[AvisoCambioEstado], None]] = []

    def suscribir(self, manejador: Callable[[AvisoCambioEstado], None]) -> None:
        """Añade un receptor para entregas posteriores.

        Args:
            manejador: Función invocable que recibe un aviso.

        Raises:
            ValueError: El manejador no es invocable.
        """
        if not callable(manejador):
            raise ValueError("El manejador debe ser invocable.")
        self._manejadores.append(manejador)

    def publicar(self, aviso: AvisoCambioEstado) -> None:
        """Encola un aviso sin llamar a los receptores.

        Args:
            aviso: Evento que se entregará al despachar.

        Raises:
            ValueError: El dato no es un aviso.
        """
        if not isinstance(aviso, AvisoCambioEstado):
            raise ValueError("Se requiere un aviso de cambio de estado.")
        self._pendientes.append(aviso)

    def obtener_pendientes(self) -> list[AvisoCambioEstado]:
        """Devuelve una copia de la cola sin consumirla.

        Returns:
            Avisos pendientes en orden de publicación.
        """
        return list(self._pendientes)

    def despachar_pendientes(self) -> None:
        """Entrega la cola y registra fallos sin datos personales ni detalles de excepciones."""
        while self._pendientes:
            aviso = self._pendientes.popleft()
            for manejador in tuple(self._manejadores):
                try:
                    manejador(aviso)
                except Exception:  # noqa: BLE001 -- Se aíslan fallos arbitrarios de receptores.
                    logging.getLogger(__name__).warning(
                        "Un receptor falló; se continúa con los demás receptores."
                    )
