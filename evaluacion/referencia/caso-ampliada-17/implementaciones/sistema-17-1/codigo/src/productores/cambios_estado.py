"""Publicación de cambios de estado sin dependencia de sus consumidores."""

from datetime import datetime

from eventos.aviso import AvisoCambioEstado, CanalEventos


def publicar_cambio_estado(
    canal: CanalEventos,
    numero_tramite: str,
    tipo_tramite: str,
    estado_anterior: str,
    estado_nuevo: str,
    fecha_hora: datetime,
    funcionario: str,
) -> AvisoCambioEstado:
    """Construye, valida y publica un aviso para entrega posterior.

    Args:
        canal: Canal de publicación diferida.
        numero_tramite: Identificador no vacío.
        tipo_tramite: Tipo no vacío.
        estado_anterior: Estado previo.
        estado_nuevo: Estado solicitado.
        fecha_hora: Fecha y hora local del cambio.
        funcionario: Identificador no vacío del funcionario.

    Returns:
        Aviso publicado, incluso si la transición es inválida.

    Raises:
        ValueError: Los datos no cumplen las restricciones del aviso.
    """
    permitidas = (
        ("radicado", "en revisión"),
        ("en revisión", "aprobado"),
        ("en revisión", "rechazado"),
    )
    aviso = AvisoCambioEstado(
        numero_tramite,
        tipo_tramite,
        estado_anterior,
        estado_nuevo,
        fecha_hora,
        funcionario,
        (estado_anterior, estado_nuevo) in permitidas,
    )
    canal.publicar(aviso)
    return aviso
