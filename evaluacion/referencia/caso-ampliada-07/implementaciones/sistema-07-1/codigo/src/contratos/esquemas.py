"""Contratos de datos del procesamiento de recaudo."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


def _referencia(valor: str) -> None:
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError("La referencia no puede estar vacía.")


def _pesos(valor: Decimal) -> None:
    if not isinstance(valor, Decimal) or not valor.is_finite():
        raise ValueError("El valor debe ser un Decimal finito.")
    if valor != valor.to_integral_value():
        raise ValueError("El valor debe representar pesos sin decimales.")


def _banco(valor: str) -> None:
    if valor not in ("A", "B", "C"):
        raise ValueError("El banco debe ser A, B o C.")


def _fecha(valor: date) -> None:
    if type(valor) is not date:
        raise ValueError("La fecha debe ser de tipo date.")


def _lista(valor: list[object], tipo: type) -> None:
    if not isinstance(valor, list) or any(not isinstance(item, tipo) for item in valor):
        raise ValueError("La lista contiene datos de un tipo incorrecto.")


@dataclass
class PagoEntrada:
    """Pago pendiente de normalización y validación numérica.

    Args:
        referencia: Identificador no vacío.
        valor_str: Valor textual, cuya validación se difiere a conciliación.
        fecha_str: Fecha textual según el banco.
        banco: A, B o C.

    Raises:
        ValueError: Si los datos estructurales son inválidos.
    """

    referencia: str
    valor_str: str
    fecha_str: str
    banco: str

    def __post_init__(self) -> None:
        """Valida la estructura sin convertir el valor monetario."""
        _referencia(self.referencia)
        _banco(self.banco)
        if not isinstance(self.valor_str, str) or not isinstance(self.fecha_str, str):
            raise ValueError("El valor y la fecha de entrada deben ser textos.")


@dataclass
class Factura:
    """Factura emitida.

    Args:
        referencia: Identificador no vacío.
        valor: Importe entero en pesos.
        vencimiento: Fecha de vencimiento.

    Raises:
        ValueError: Si algún dato no cumple su restricción.
    """

    referencia: str
    valor: Decimal
    vencimiento: date

    def __post_init__(self) -> None:
        """Valida los datos de la factura."""
        _referencia(self.referencia)
        _pesos(self.valor)
        _fecha(self.vencimiento)


@dataclass
class DatosLeidos:
    """Datos obtenidos de los archivos.

    Args:
        pagos: Pagos de entrada, posiblemente ninguno.
        facturas: Facturas emitidas, posiblemente ninguna.

    Raises:
        ValueError: Si las listas tienen tipos incorrectos.
    """

    pagos: list[PagoEntrada]
    facturas: list[Factura]

    def __post_init__(self) -> None:
        """Valida las colecciones recibidas."""
        _lista(self.pagos, PagoEntrada)
        _lista(self.facturas, Factura)


@dataclass
class PagoNormalizado:
    """Pago con fecha normalizada y valor todavía textual.

    Args:
        referencia: Identificador no vacío.
        valor_str: Texto que se validará durante la conciliación.
        fecha: Fecha del pago.
        banco: A, B o C.

    Raises:
        ValueError: Si los datos estructurales son inválidos.
    """

    referencia: str
    valor_str: str
    fecha: date
    banco: str

    def __post_init__(self) -> None:
        """Valida los datos salvo el contenido numérico del valor."""
        _referencia(self.referencia)
        _banco(self.banco)
        _fecha(self.fecha)
        if not isinstance(self.valor_str, str):
            raise ValueError("El valor del pago debe ser texto.")


@dataclass
class DatosNormalizados:
    """Datos disponibles para conciliación.

    Args:
        pagos: Pagos normalizados, posiblemente ninguno.
        facturas: Facturas emitidas, posiblemente ninguna.

    Raises:
        ValueError: Si las listas tienen tipos incorrectos.
    """

    pagos: list[PagoNormalizado]
    facturas: list[Factura]

    def __post_init__(self) -> None:
        """Valida las colecciones recibidas."""
        _lista(self.pagos, PagoNormalizado)
        _lista(self.facturas, Factura)


@dataclass
class RegistroResultado:
    """Fila resultante de la conciliación.

    Args:
        referencia: Identificador no vacío.
        valor_facturado: Importe facturado o None si no hay factura.
        valor_pagado: Importe pagado o None si está pendiente.
        banco: Banco del pago o None si está pendiente.
        estado: Uno de los cuatro estados del proceso.
        diferencia: Pago menos factura, o cero cuando no aplica.

    Raises:
        ValueError: Si los campos no corresponden al estado.
    """

    referencia: str
    valor_facturado: Decimal | None
    valor_pagado: Decimal | None
    banco: str | None
    estado: str
    diferencia: Decimal

    def __post_init__(self) -> None:
        """Valida importes, estado y campos opcionales."""
        _referencia(self.referencia)
        _pesos(self.diferencia)
        for valor in (self.valor_facturado, self.valor_pagado):
            if valor is not None:
                _pesos(valor)
        if self.banco is not None:
            _banco(self.banco)
        if self.estado not in ("conciliado", "diferencia", "pago sin factura", "pendiente"):
            raise ValueError("Estado de conciliación inválido.")
        self._validar_estado()

    def _validar_estado(self) -> None:
        if self.estado == "pendiente":
            valido = (
                self.valor_facturado is not None
                and self.valor_pagado is None
                and self.banco is None
                and self.diferencia == 0
            )
        elif self.estado == "pago sin factura":
            valido = (
                self.valor_facturado is None
                and self.valor_pagado is not None
                and self.banco is not None
                and self.diferencia == 0
            )
        else:
            valido = (
                self.valor_facturado is not None
                and self.valor_pagado is not None
                and self.banco is not None
            )
            if valido:
                valido = self.diferencia == self.valor_pagado - self.valor_facturado
                valido = valido and ((self.diferencia == 0) == (self.estado == "conciliado"))
        if not valido:
            raise ValueError("Los campos del resultado no corresponden a su estado.")


@dataclass
class Resumen:
    """Totales por estado.

    Args:
        conciliado: Número de pagos conciliados.
        diferencia: Número de pagos con diferencia.
        pago_sin_factura: Número de pagos sin factura.
        pendiente: Número de facturas pendientes.

    Raises:
        ValueError: Si un total no es un entero no negativo.
    """

    conciliado: int
    diferencia: int
    pago_sin_factura: int
    pendiente: int

    def __post_init__(self) -> None:
        """Valida los contadores."""
        valores = (self.conciliado, self.diferencia, self.pago_sin_factura, self.pendiente)
        if any(type(valor) is not int or valor < 0 for valor in valores):
            raise ValueError("Los totales deben ser enteros no negativos.")


@dataclass
class ResultadoConciliacion:
    """Resultado completo del lote.

    Args:
        registros: Filas resultantes, posiblemente ninguna.
        resumen: Totales por estado.

    Raises:
        ValueError: Si los componentes tienen tipos incorrectos.
    """

    registros: list[RegistroResultado]
    resumen: Resumen

    def __post_init__(self) -> None:
        """Valida los componentes del resultado."""
        _lista(self.registros, RegistroResultado)
        if not isinstance(self.resumen, Resumen):
            raise ValueError("El resumen debe ser de tipo Resumen.")
