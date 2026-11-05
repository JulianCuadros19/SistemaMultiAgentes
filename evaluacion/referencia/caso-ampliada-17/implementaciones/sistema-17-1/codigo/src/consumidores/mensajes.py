"""Preparación de mensajes en español para el ciudadano."""

from dataclasses import dataclass

from eventos.aviso import AvisoCambioEstado, MensajeCiudadano, RegistroMensajes


@dataclass
class MensajesConsumidor:
    """Prepara mensajes únicamente para cambios válidos.

    Args:
        registro: Almacén de mensajes inyectado.
    """

    registro: RegistroMensajes

    def manejar(self, aviso: AvisoCambioEstado) -> None:
        """Genera el texto correspondiente al estado nuevo.

        Args:
            aviso: Evento recibido del canal.
        """
        if not aviso.es_valida:
            return
        plantillas = {
            "aprobado": "Su trámite {numero} fue aprobado",
            "rechazado": "Su trámite {numero} fue rechazado; puede consultar el motivo en la oficina",
            "en revisión": "Su trámite {numero} está en revisión",
        }
        plantilla = plantillas.get(aviso.estado_nuevo)
        if plantilla is not None:
            self.registro.registrar(
                MensajeCiudadano(
                    aviso.numero_tramite,
                    plantilla.format(numero=aviso.numero_tramite),
                )
            )
