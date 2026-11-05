"""Consumidor que falla deliberadamente para comprobar el aislamiento de receptores."""

from eventos.aviso import AvisoCambioEstado


class ConsumidorFalla:
    """Receptor sin estado que siempre falla al recibir un aviso."""

    def manejar(self, aviso: AvisoCambioEstado) -> None:
        """Simula un fallo de procesamiento.

        Args:
            aviso: Evento que no se procesará.

        Raises:
            Exception: Fallo deliberado del receptor.
        """
        raise Exception("Fallo deliberado del consumidor.")
