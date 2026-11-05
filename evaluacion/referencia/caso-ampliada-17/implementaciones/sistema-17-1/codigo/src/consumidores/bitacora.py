"""Consumidor de avisos que conserva los datos completos en bitácora."""

from dataclasses import dataclass

from eventos.aviso import AsientoBitacora, AvisoCambioEstado, RegistroBitacora


@dataclass
class BitacoraConsumidor:
    """Registra todos los avisos, incluidos los de transiciones inválidas.

    Args:
        registro: Almacén de asientos inyectado.
    """

    registro: RegistroBitacora

    def manejar(self, aviso: AvisoCambioEstado) -> None:
        """Copia el aviso a un asiento con su marca de validez.

        Args:
            aviso: Evento recibido del canal.
        """
        self.registro.registrar(
            AsientoBitacora(
                aviso.numero_tramite,
                aviso.tipo_tramite,
                aviso.estado_anterior,
                aviso.estado_nuevo,
                aviso.fecha_hora,
                aviso.funcionario,
                aviso.es_valida,
            )
        )
