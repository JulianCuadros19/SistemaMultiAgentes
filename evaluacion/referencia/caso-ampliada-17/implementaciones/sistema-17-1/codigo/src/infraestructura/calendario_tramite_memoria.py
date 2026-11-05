"""Registro en memoria de fechas de radicación."""

from datetime import date, datetime

from eventos.aviso import RegistroFechasTramite


class RegistroFechasTramiteMemoria(RegistroFechasTramite):
    """Conserva una fecha de radicación por trámite y por instancia."""

    def __init__(self) -> None:
        """Inicializa un calendario vacío."""
        self._fechas: dict[str, date] = {}

    def registrar_radicado(self, numero_tramite: str, fecha: date) -> None:
        """Guarda o reemplaza la fecha de radicación.

        Args:
            numero_tramite: Identificador no vacío.
            fecha: Fecha de radicación, sin hora.

        Raises:
            ValueError: El identificador o la fecha son inválidos.
        """
        if not isinstance(numero_tramite, str) or not numero_tramite.strip():
            raise ValueError("El número de trámite debe ser un texto no vacío.")
        if not isinstance(fecha, date) or isinstance(fecha, datetime):
            raise ValueError("La radicación requiere una fecha sin hora.")
        self._fechas[numero_tramite] = fecha

    def obtener_fecha_radicado(self, numero_tramite: str) -> date | None:
        """Consulta una fecha registrada.

        Args:
            numero_tramite: Identificador buscado.

        Returns:
            Fecha de radicación o None si no existe.
        """
        return self._fechas.get(numero_tramite)
