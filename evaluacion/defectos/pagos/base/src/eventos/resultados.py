"""Decisiones de consumidores que la infraestructura aplica en memoria."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


def _validar_pesos(valor: Decimal) -> None:
    if not isinstance(valor, Decimal) or not valor.is_finite():
        raise ValueError("El importe debe ser un Decimal finito.")
    if valor < 0 or valor != valor.to_integral_value():
        raise ValueError("El importe debe contener pesos enteros no negativos.")


class _ResultadoValidado:
    def __post_init__(self) -> None:
        for nombre, valor in vars(self).items():
            if nombre in {"valor", "valor_aplicado", "saldo_a_favor"}:
                _validar_pesos(valor)
            elif nombre == "fecha":
                if type(valor) is not date:
                    raise ValueError("La fecha debe ser una fecha calendario válida.")
            elif not isinstance(valor, str) or not valor.strip():
                raise ValueError(f"El campo {nombre} debe ser texto no vacío.")
        estados = {
            "estado_factura": {"pagada", "abonada", "pendiente"},
            "estado_recibo": {"anulado"},
            "estado_cartera": {"al día", "en mora"},
        }
        for nombre, permitidos in estados.items():
            if nombre in vars(self) and vars(self)[nombre] not in permitidos:
                raise ValueError(f"El campo {nombre} contiene un estado no permitido.")


@dataclass(frozen=True)
class AjusteFacturaResultado(_ResultadoValidado):
    """Instrucción para ajustar una factura.

    Args:
        numero_factura: Número de factura.
        estado_factura: Estado resultante de factura.
        valor_aplicado: Importe aplicado al saldo, en pesos enteros.
        saldo_a_favor: Excedente del pago, en pesos enteros.
        clave_idempotencia: Clave derivada del tipo, referencia y factura.
    """

    numero_factura: str
    estado_factura: str
    valor_aplicado: Decimal
    saldo_a_favor: Decimal
    clave_idempotencia: str


@dataclass(frozen=True)
class EmisionReciboResultado(_ResultadoValidado):
    """Solicitud de emisión de recibo.

    Args:
        numero_factura: Factura del recibo.
        referencia_pago: Referencia del pago.
        valor: Importe total del pago en pesos enteros.
        fecha: Fecha calendario del pago.
        clave_idempotencia: Clave derivada del tipo y referencia.
    """

    numero_factura: str
    referencia_pago: str
    valor: Decimal
    fecha: date
    clave_idempotencia: str


@dataclass(frozen=True)
class AnulacionReciboResultado(_ResultadoValidado):
    """Solicitud de anulación de recibo.

    Args:
        referencia_pago: Referencia del pago cuyo recibo se anula.
        motivo: Motivo informado por la pasarela.
        estado_recibo: Estado solicitado, anulado.
        clave_idempotencia: Clave derivada del tipo y referencia.
    """

    referencia_pago: str
    motivo: str
    estado_recibo: str
    clave_idempotencia: str


@dataclass(frozen=True)
class ActualizacionCarteraResultado(_ResultadoValidado):
    """Instrucción de actualización de cartera.

    Args:
        referencia_pago: Referencia del pago.
        id_familia: Identificador de familia.
        estado_cartera: Estado resultante, al día o en mora.
        clave_idempotencia: Clave derivada del tipo y referencia.
    """

    referencia_pago: str
    id_familia: str
    estado_cartera: str
    clave_idempotencia: str
