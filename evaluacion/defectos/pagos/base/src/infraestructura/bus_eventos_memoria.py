"""Bus síncrono en memoria con enriquecimiento y control de duplicados."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from eventos.aviso_pago import AvisoPagoConfirmado, AvisoPagoReversado
from eventos.aviso_pago_enriquecido import (
    AvisoPagoConfirmadoEnriquecido,
    AvisoPagoReversadoEnriquecido,
)
from eventos.resultados import (
    ActualizacionCarteraResultado,
    AjusteFacturaResultado,
    AnulacionReciboResultado,
    EmisionReciboResultado,
)
from infraestructura import repos_facturacion_memoria as repos
from infraestructura.repos_facturacion_memoria import (
    FacturaNoExiste,
    ReferenciaNoAsociada,
)


class EventoDuplicadoIgnorado(ValueError):
    """Indica que el aviso ya fue procesado y no vuelve a producir cambios."""


def suscribir_pago_confirmado(self, manejador: callable) -> None:  # noqa: ANN001
    """Registra un consumidor de pagos confirmados.

    Args:
        self: Bus en el que se registra la suscripción.
        manejador: Función que recibe un evento enriquecido y devuelve una decisión.
    """
    self._confirmados.append(manejador)


def suscribir_pago_reversado(self, manejador: callable) -> None:  # noqa: ANN001
    """Registra un consumidor de reversos.

    Args:
        self: Bus en el que se registra la suscripción.
        manejador: Función que recibe un reverso enriquecido y devuelve una decisión.
    """
    self._reversados.append(manejador)


def publicar_pago_confirmado(self, aviso: AvisoPagoConfirmado) -> None:  # noqa: ANN001
    """Enriquece el aviso y aplica las decisiones de todos los suscriptores.

    Args:
        self: Bus que procesa el aviso.
        aviso: Aviso bruto de pago confirmado.

    Raises:
        EventoDuplicadoIgnorado: Si ya se procesó la referencia para este tipo de aviso.
        FacturaNoExiste: Si no existe la factura asociada.
    """
    aviso = replace(aviso)
    clave = ("confirmado", aviso.referencia_pago)
    if clave in self._eventos_procesados:
        raise EventoDuplicadoIgnorado("El pago confirmado duplicado fue ignorado.")
    try:
        factura = repos.obtener_factura_por_numero(aviso.numero_factura)
    except FacturaNoExiste:
        raise
    enriquecido = AvisoPagoConfirmadoEnriquecido(
        aviso.referencia_pago,
        aviso.numero_factura,
        aviso.valor,
        aviso.fecha,
        factura.saldo,
        factura.estado,
        factura.id_familia,
    )
    resultados = [manejador(enriquecido) for manejador in self._confirmados]
    repos.registrar_mapeo_referencia_factura(aviso.referencia_pago, aviso.numero_factura)
    for resultado in resultados:
        self._aplicar(resultado)
    self._eventos_procesados.add(clave)


def publicar_pago_reversado(self, aviso: AvisoPagoReversado) -> None:  # noqa: ANN001
    """Resuelve la factura del reverso y aplica las decisiones de los suscriptores.

    Args:
        self: Bus que procesa el aviso.
        aviso: Aviso bruto de pago reversado.

    Raises:
        EventoDuplicadoIgnorado: Si ya se procesó este reverso.
        ReferenciaNoAsociada: Si no se puede resolver la factura del pago.
    """
    aviso = replace(aviso)
    clave = ("reversado", aviso.referencia_pago)
    if clave in self._eventos_procesados:
        raise EventoDuplicadoIgnorado("El reverso duplicado fue ignorado.")
    try:
        numero = repos.obtener_numero_factura_por_referencia(aviso.referencia_pago)
    except ReferenciaNoAsociada:
        raise
    factura = repos.obtener_factura_por_numero(numero)
    enriquecido = AvisoPagoReversadoEnriquecido(
        aviso.referencia_pago,
        aviso.fecha,
        aviso.motivo,
        numero,
        factura.estado_anterior,
        factura.id_familia,
    )
    resultados = [manejador(enriquecido) for manejador in self._reversados]
    for resultado in resultados:
        self._aplicar(resultado)
    self._eventos_procesados.add(clave)


class BusEventosMemoria:
    """Bus volátil con suscripción explícita de consumidores.

    El constructor no recibe parámetros ni registra consumidores automáticamente.
    Cada instancia conserva sus propias claves de idempotencia.
    """

    def __init__(self) -> None:
        """Inicializa las suscripciones y las claves de procesamiento."""
        self._confirmados: list[Callable] = []
        self._reversados: list[Callable] = []
        self._eventos_procesados: set[tuple[str, str]] = set()
        self._resultados_procesados: set[tuple[type, str]] = set()

    suscribir_pago_confirmado = suscribir_pago_confirmado
    suscribir_pago_reversado = suscribir_pago_reversado
    publicar_pago_confirmado = publicar_pago_confirmado
    publicar_pago_reversado = publicar_pago_reversado

    def _aplicar(self, resultado: object) -> None:
        if isinstance(resultado, AjusteFacturaResultado):
            aplicador = repos.aplicar_ajuste_factura
        elif isinstance(resultado, EmisionReciboResultado):
            aplicador = repos.aplicar_emision_recibo
        elif isinstance(resultado, AnulacionReciboResultado):
            aplicador = repos.aplicar_anulacion_recibo
        elif isinstance(resultado, ActualizacionCarteraResultado):
            aplicador = repos.actualizar_cartera
        else:
            raise TypeError("El consumidor debe devolver un resultado declarado.")
        clave = (type(resultado), resultado.clave_idempotencia)
        if clave not in self._resultados_procesados:
            aplicador(resultado)
            self._resultados_procesados.add(clave)
