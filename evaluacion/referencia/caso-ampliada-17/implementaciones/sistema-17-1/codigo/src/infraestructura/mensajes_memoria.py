"""Almacenamiento en memoria de mensajes preparados para el ciudadano."""

from eventos.aviso import MensajeCiudadano, RegistroMensajes


class RegistroMensajesMemoria(RegistroMensajes):
    """Conserva mensajes en orden de registro por instancia."""

    def __init__(self) -> None:
        """Inicializa un registro vacío."""
        self._mensajes: list[MensajeCiudadano] = []

    def registrar(self, mensaje: MensajeCiudadano) -> None:
        """Añade un mensaje preparado.

        Args:
            mensaje: Mensaje a conservar.

        Raises:
            ValueError: El dato no es un mensaje.
        """
        if not isinstance(mensaje, MensajeCiudadano):
            raise ValueError("Se requiere un mensaje al ciudadano.")
        self._mensajes.append(mensaje)

    def consultar_por_tramite(self, numero_tramite: str) -> list[MensajeCiudadano]:
        """Consulta sin exponer la lista interna.

        Args:
            numero_tramite: Identificador buscado.

        Returns:
            Mensajes del trámite en orden de registro.
        """
        return [mensaje for mensaje in self._mensajes if mensaje.numero_tramite == numero_tramite]
