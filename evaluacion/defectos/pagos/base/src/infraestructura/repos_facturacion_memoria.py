"""Repositorio volátil de facturas, recibos, asociaciones y cartera."""

from dataclasses import dataclass, replace
from decimal import ROUND_HALF_UP, Decimal

from eventos.resultados import (
    ActualizacionCarteraResultado,
    AjusteFacturaResultado,
    AnulacionReciboResultado,
    EmisionReciboResultado,
)


class FacturaNoExiste(LookupError):
    """Indica que el número solicitado no identifica una factura registrada."""


class ReferenciaNoAsociada(LookupError):
    """Indica que la referencia no tiene una factura asociada."""


class ReciboNoExiste(LookupError):
    """Indica que no existe un recibo asociado a la referencia."""


def _validar_texto(valor: str) -> None:
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError("Se requiere texto no vacío.")


def _validar_pesos(valor: Decimal) -> None:
    if not isinstance(valor, Decimal) or not valor.is_finite():
        raise ValueError("Se requiere un Decimal finito.")
    if valor < 0 or valor != valor.to_integral_value():
        raise ValueError("Se requieren pesos enteros no negativos.")


def _validar_estado(estado: str, permitidos: set[str]) -> None:
    _validar_texto(estado)
    if estado not in permitidos:
        raise ValueError("El estado no está permitido.")


@dataclass(frozen=True)
class Factura:
    """Factura almacenada en memoria.

    Args:
        numero: Número no vacío de factura.
        id_familia: Identificador no vacío de familia.
        saldo: Saldo en pesos enteros no negativos.
        estado: Estado actual de factura.
        estado_anterior: Estado anterior al último ajuste.
    """

    numero: str
    id_familia: str
    saldo: Decimal
    estado: str
    estado_anterior: str

    def __post_init__(self) -> None:
        """Valida los datos de la factura.

        Raises:
            ValueError: Si un campo incumple el modelo de datos.
        """
        _validar_texto(self.numero)
        _validar_texto(self.id_familia)
        _validar_pesos(self.saldo)
        _validar_estado(self.estado, {"pagada", "abonada", "pendiente"})
        _validar_estado(self.estado_anterior, {"pagada", "abonada", "pendiente"})


@dataclass(frozen=True)
class Recibo:
    """Recibo emitido y, opcionalmente, anulado.

    Args:
        consecutivo: Identificador con formato REC-000001 y sucesivos.
        numero_factura: Factura asociada.
        valor: Importe total del pago en pesos enteros.
        estado_recibo: Estado emitido o anulado.
        referencia_pago: Referencia asociada.
        motivo: Motivo registrado al anular, ausente en la emisión.
    """

    consecutivo: str
    numero_factura: str
    valor: Decimal
    estado_recibo: str
    referencia_pago: str
    motivo: str | None = None

    def __post_init__(self) -> None:
        """Valida los campos del recibo.

        Raises:
            ValueError: Si un campo incumple el modelo de datos.
        """
        _validar_texto(self.consecutivo)
        sufijo = self.consecutivo.removeprefix("REC-")
        if not self.consecutivo.startswith("REC-") or not sufijo.isascii():
            raise ValueError("El consecutivo debe comenzar por REC- y contener dígitos.")
        if not sufijo.isdigit() or len(sufijo) < 6 or int(sufijo) < 1:
            raise ValueError("El consecutivo debe seguir el formato REC-000001.")
        _validar_texto(self.numero_factura)
        _validar_texto(self.referencia_pago)
        _validar_pesos(self.valor)
        _validar_estado(self.estado_recibo, {"emitido", "anulado"})
        if self.motivo is not None:
            _validar_texto(self.motivo)


@dataclass(frozen=True)
class Cartera:
    """Estado de cartera de una familia.

    Args:
        id_familia: Identificador no vacío de familia.
        estado: Estado al día o en mora.
        ultima_referencia_procesada: Última referencia aplicada, si existe.
    """

    id_familia: str
    estado: str
    ultima_referencia_procesada: str | None = None

    def __post_init__(self) -> None:
        """Valida el estado y los identificadores de cartera.

        Raises:
            ValueError: Si un campo incumple el modelo de datos.
        """
        _validar_texto(self.id_familia)
        _validar_estado(self.estado, {"al día", "en mora"})
        if self.ultima_referencia_procesada is not None:
            _validar_texto(self.ultima_referencia_procesada)


_facturas: dict[str, Factura] = {}
_referencias: dict[str, str] = {}
_recibos: dict[str, Recibo] = {}
_carteras: dict[str, Cartera] = {}
_saldos_iniciales: dict[str, Decimal] = {}
_pagos_aplicados: dict[tuple[str, str], Decimal] = {}
_consecutivo = 0


def registrar_factura_inicial(
    numero_factura: str, id_familia: str, saldo_inicial: Decimal, estado_inicial: str
) -> None:
    """Registra la factura inicial en el almacén volátil.

    Args:
        numero_factura: Número de factura.
        id_familia: Identificador de familia.
        saldo_inicial: Pesos enteros no negativos.
        estado_inicial: Estado pagada, abonada o pendiente.

    Raises:
        ValueError: Si los datos incumplen el modelo.
    """
    factura = Factura(
        numero_factura, id_familia, saldo_inicial, estado_inicial, estado_inicial
    )
    _facturas[numero_factura] = factura
    _saldos_iniciales[numero_factura] = saldo_inicial


def obtener_factura_por_numero(numero_factura: str) -> Factura:
    """Obtiene una factura registrada.

    Args:
        numero_factura: Número de factura buscado.

    Returns:
        Instantánea inmutable de la factura.

    Raises:
        FacturaNoExiste: Si el número no identifica una factura registrada.
    """
    if not isinstance(numero_factura, str) or not numero_factura.strip():
        raise FacturaNoExiste("El número de factura es inválido.")
    try:
        return _facturas[numero_factura]
    except KeyError as error:
        raise FacturaNoExiste("La factura no existe.") from error


def registrar_mapeo_referencia_factura(referencia_pago: str, numero_factura: str) -> None:
    """Registra la asociación referencia a factura.

    Args:
        referencia_pago: Referencia no vacía.
        numero_factura: Número no vacío de factura.

    Raises:
        ValueError: Si algún identificador es inválido.
    """
    _validar_texto(referencia_pago)
    _validar_texto(numero_factura)
    _referencias[referencia_pago] = numero_factura


def obtener_numero_factura_por_referencia(referencia_pago: str) -> str:
    """Resuelve la factura de una referencia.

    Args:
        referencia_pago: Referencia buscada.

    Returns:
        Número de factura asociado.

    Raises:
        ReferenciaNoAsociada: Si no existe una asociación para la referencia.
    """
    if not isinstance(referencia_pago, str) or not referencia_pago.strip():
        raise ReferenciaNoAsociada("La referencia es inválida.")
    try:
        return _referencias[referencia_pago]
    except KeyError as error:
        raise ReferenciaNoAsociada("La referencia no está asociada.") from error


def registrar_cartera_familia(id_familia: str, estado_inicial: str) -> None:
    """Registra la cartera inicial de una familia.

    Args:
        id_familia: Identificador de familia.
        estado_inicial: Estado al día o en mora.

    Raises:
        ValueError: Si los datos incumplen el modelo.
    """
    cartera = Cartera(id_familia, estado_inicial)
    _carteras[id_familia] = cartera


def obtener_cartera_por_familia(id_familia: str) -> Cartera:
    """Obtiene la cartera previamente registrada de una familia.

    Args:
        id_familia: Identificador no vacío de familia.

    Returns:
        Instantánea inmutable de cartera.

    Raises:
        ValueError: Si el identificador es inválido.
        KeyError: Si no se registró la cartera, incumpliendo la precondición.
    """
    _validar_texto(id_familia)
    return _carteras[id_familia]


def aplicar_ajuste_factura(ajuste: AjusteFacturaResultado) -> Factura:
    """Aplica un pago o devuelve únicamente su importe aplicado ante un reverso.

    Args:
        ajuste: Resultado validado de un consumidor de factura.

    Returns:
        Factura actualizada. En reversos, el estado se deriva del saldo resultante.

    Raises:
        FacturaNoExiste: Si no existe la factura del ajuste.
        ValueError: Si el resultado contiene datos inválidos.
    """
    ajuste = replace(ajuste)
    anterior = obtener_factura_por_numero(ajuste.numero_factura)
    es_reverso = ajuste.clave_idempotencia.startswith("reversado:")
    prefijo = "reversado:" if es_reverso else "confirmado:"
    referencia = ajuste.clave_idempotencia.removeprefix(prefijo).removesuffix(
        f":{ajuste.numero_factura}"
    )
    clave_pago = (referencia, anterior.numero)
    estado = ajuste.estado_factura
    if es_reverso:
        saldo = anterior.saldo + _pagos_aplicados.get(clave_pago, Decimal(0))
        if saldo == 0:
            estado = "pagada"
        elif saldo == _saldos_iniciales[anterior.numero]:
            estado = "pendiente"
        else:
            estado = "abonada"
    else:
        if ajuste.valor_aplicado > anterior.saldo:
            raise ValueError("El importe aplicado no puede superar el saldo.")
        saldo = anterior.saldo - ajuste.valor_aplicado
    nueva = Factura(
        anterior.numero,
        anterior.id_familia,
        saldo.quantize(Decimal(1), rounding=ROUND_HALF_UP),
        estado,
        anterior.estado,
    )
    if es_reverso:
        _pagos_aplicados.pop(clave_pago, None)
    else:
        _pagos_aplicados[clave_pago] = ajuste.valor_aplicado
    _facturas[anterior.numero] = nueva
    return nueva


def aplicar_emision_recibo(emision: EmisionReciboResultado) -> Recibo:
    """Emite el recibo de una referencia y asigna un consecutivo.

    Args:
        emision: Solicitud validada de emisión.

    Returns:
        Recibo emitido; si ya existe para la referencia, el mismo recibo almacenado.

    Raises:
        ValueError: Si el resultado contiene datos inválidos.
    """
    global _consecutivo
    emision = replace(emision)
    if emision.referencia_pago in _recibos:
        return _recibos[emision.referencia_pago]
    siguiente = _consecutivo + 1
    recibo = Recibo(
        f"REC-{siguiente:06d}",
        emision.numero_factura,
        emision.valor.quantize(Decimal(1), rounding=ROUND_HALF_UP),
        "emitido",
        emision.referencia_pago,
    )
    _recibos[emision.referencia_pago] = recibo
    _consecutivo = siguiente
    return recibo


def aplicar_anulacion_recibo(anulacion: AnulacionReciboResultado) -> Recibo:
    """Anula el recibo de una referencia y registra el motivo.

    Args:
        anulacion: Solicitud validada de anulación.

    Returns:
        Recibo anulado con su motivo.

    Raises:
        ReciboNoExiste: Si no existe un recibo para la referencia.
        ValueError: Si el resultado contiene datos inválidos.
    """
    anulacion = replace(anulacion)
    try:
        anterior = _recibos[anulacion.referencia_pago]
    except KeyError as error:
        raise ReciboNoExiste("No existe el recibo asociado al pago.") from error
    nuevo = replace(
        anterior, estado_recibo=anulacion.estado_recibo, motivo=anulacion.motivo
    )
    _recibos[anulacion.referencia_pago] = nuevo
    return nuevo


def obtener_recibo_por_referencia(referencia_pago: str) -> Recibo:
    """Obtiene el recibo de una referencia de pago, emitido o anulado.

    Args:
        referencia_pago: Referencia del pago.

    Returns:
        Instantánea inmutable del recibo, con su motivo si se anuló.

    Raises:
        ReciboNoExiste: Si no se emitió un recibo para la referencia.
        ValueError: Si la referencia es inválida.
    """
    _validar_texto(referencia_pago)
    try:
        return _recibos[referencia_pago]
    except KeyError as error:
        raise ReciboNoExiste("No existe el recibo asociado al pago.") from error


def actualizar_cartera(actualizacion: ActualizacionCarteraResultado) -> Cartera:
    """Actualiza la cartera registrada de una familia.

    Args:
        actualizacion: Estado resultante y referencia aplicada.

    Returns:
        Cartera actualizada.

    Raises:
        ValueError: Si el resultado contiene datos inválidos.
        KeyError: Si no se registró la cartera, incumpliendo la precondición.
    """
    actualizacion = replace(actualizacion)
    anterior = obtener_cartera_por_familia(actualizacion.id_familia)
    nueva = replace(
        anterior,
        estado=actualizacion.estado_cartera,
        ultima_referencia_procesada=actualizacion.referencia_pago,
    )
    _carteras[nueva.id_familia] = nueva
    return nueva
