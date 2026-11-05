"""Subcomandos lógicos de cuota, tabla y resumen del crédito."""

from decimal import Decimal

from dominio.credito import AmortizacionFila, Resumen
from entrada_salida.csv_salida import TablaCSV
from servicios.simulador import (
    ValidacionError,
    calcular_cuota,
    calcular_resumen,
    generar_tabla,
)


class ErrorCLI(Exception):
    """Error de uso de un subcomando con código de salida.

    Args:
        codigo_salida: Código no nulo del error.
        mensaje: Explicación para el usuario.
    """

    def __init__(self, codigo_salida: int, mensaje: str) -> None:
        """Inicialice el código y el mensaje del error.

        Args:
            codigo_salida: Código de salida no nulo.
            mensaje: Explicación del error de uso.
        """
        self.codigo_salida = codigo_salida
        self.mensaje = mensaje
        super().__init__(mensaje)


def _argumentos(
    tea: Decimal | None, monto: Decimal | None, plazo: int | None
) -> tuple[Decimal, Decimal, int]:
    if tea is None:
        raise ErrorCLI(2, "Debe ingresar la tasa efectiva anual.")
    if monto is None:
        raise ErrorCLI(2, "Debe ingresar el monto del crédito.")
    if plazo is None:
        raise ErrorCLI(2, "Debe ingresar el plazo en meses.")
    return tea, monto, plazo


def ejecutar_cuota(tea: Decimal | None, monto: Decimal | None, plazo: int | None) -> Decimal:
    """Ejecute el subcomando lógico de cálculo de cuota.

    Args:
        tea: Tasa efectiva anual porcentual, o None si falta.
        monto: Capital del crédito, o None si falta.
        plazo: Plazo en meses, o None si falta.

    Returns:
        Cuota mensual redondeada al peso.

    Raises:
        ErrorCLI: Si falta un dato o es inválido, con código de salida 2.
    """
    argumentos = _argumentos(tea, monto, plazo)
    try:
        return calcular_cuota(*argumentos)
    except ValidacionError as error:
        raise ErrorCLI(2, str(error)) from error


def ejecutar_tabla(
    tea: Decimal | None,
    monto: Decimal | None,
    plazo: int | None,
    ruta_csv: str | None,
    escritor: TablaCSV | None = None,
) -> list[AmortizacionFila]:
    """Ejecute el subcomando de tabla con exportación opcional.

    Args:
        tea: Tasa efectiva anual porcentual, o None si falta.
        monto: Capital del crédito, o None si falta.
        plazo: Plazo en meses, o None si falta.
        ruta_csv: Destino CSV, o None para no exportar.
        escritor: Escritor CSV; si falta, se crea uno con separador coma.

    Returns:
        Tabla completa con ajuste de la última cuota.

    Raises:
        ErrorCLI: Si falta un dato o es inválido, con código de salida 2.
    """
    argumentos = _argumentos(tea, monto, plazo)
    try:
        tabla = generar_tabla(*argumentos)
    except ValidacionError as error:
        raise ErrorCLI(2, str(error)) from error
    if ruta_csv is not None:
        destino = escritor if escritor is not None else TablaCSV()
        destino.guardar(tabla, ruta_csv)
    return tabla


def ejecutar_resumen(tea: Decimal | None, monto: Decimal | None, plazo: int | None) -> Resumen:
    """Ejecute el subcomando lógico de resumen del crédito.

    Args:
        tea: Tasa efectiva anual porcentual, o None si falta.
        monto: Capital del crédito, o None si falta.
        plazo: Plazo en meses, o None si falta.

    Returns:
        Totales de pagos e intereses de la tabla ajustada.

    Raises:
        ErrorCLI: Si falta un dato o es inválido, con código de salida 2.
    """
    argumentos = _argumentos(tea, monto, plazo)
    try:
        return calcular_resumen(*argumentos)
    except ValidacionError as error:
        raise ErrorCLI(2, str(error)) from error
