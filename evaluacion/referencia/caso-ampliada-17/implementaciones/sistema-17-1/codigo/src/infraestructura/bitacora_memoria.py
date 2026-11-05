"""Almacenamiento de bitácora en memoria, sin recursos externos."""

from eventos.aviso import AsientoBitacora, RegistroBitacora


class RegistroBitacoraMemoria(RegistroBitacora):
    """Conserva asientos en orden de recepción por instancia."""

    def __init__(self) -> None:
        """Inicializa una bitácora vacía."""
        self._asientos: list[AsientoBitacora] = []

    def registrar(self, asiento: AsientoBitacora) -> None:
        """Añade un asiento.

        Args:
            asiento: Entrada de bitácora a conservar.

        Raises:
            ValueError: El dato no es un asiento.
        """
        if not isinstance(asiento, AsientoBitacora):
            raise ValueError("Se requiere un asiento de bitácora.")
        self._asientos.append(asiento)

    def consultar_por_tramite(self, numero_tramite: str) -> list[AsientoBitacora]:
        """Consulta sin exponer la lista interna.

        Args:
            numero_tramite: Identificador buscado.

        Returns:
            Asientos del trámite en orden de registro.
        """
        return [asiento for asiento in self._asientos if asiento.numero_tramite == numero_tramite]
