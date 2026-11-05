"""Validación y servicios de simulación del crédito de vivienda."""

from decimal import Decimal, localcontext

from dominio.credito import AmortizacionFila, Resumen, cuota_fija, redondear_peso, tasa_mensual


class ValidacionError(ValueError):
    """Error de validación de los datos de un crédito.

    Args:
        mensaje: Explicación del dato inválido.
    """

    def __init__(self, mensaje: str) -> None:
        """Inicialice el error de validación.

        Args:
            mensaje: Explicación para el usuario.
        """
        super().__init__(mensaje)


def _validar_decimal(valor: Decimal, nombre: str, minimo: int, maximo: int) -> None:
    if not isinstance(valor, Decimal) or not valor.is_finite():
        raise ValidacionError(f"{nombre} debe ser un número Decimal finito.")
    if not Decimal(minimo) <= valor <= Decimal(maximo):
        raise ValidacionError(f"{nombre} debe estar entre {minimo} y {maximo}.")


def _validar(tea: Decimal, monto: Decimal, plazo: int) -> None:
    _validar_decimal(tea, "La tasa efectiva anual", 1, 30)
    if tea != tea.quantize(Decimal('0.01')):
        raise ValidacionError("La tasa efectiva anual admite hasta dos decimales.")
    _validar_decimal(monto, "El monto", 10_000_000, 500_000_000)
    if isinstance(plazo, bool) or not isinstance(plazo, int) or not 12 <= plazo <= 240:
        raise ValidacionError("El plazo debe ser un entero entre 12 y 240 meses.")


def calcular_cuota(tea: Decimal, monto: Decimal, plazo: int) -> Decimal:
    """Calcule la cuota mensual redondeada al peso.

    Args:
        tea: Tasa efectiva anual porcentual, entre 1 y 30, con hasta dos decimales.
        monto: Capital entre 10.000.000 y 500.000.000 pesos.
        plazo: Plazo entero entre 12 y 240 meses.

    Returns:
        Cuota mensual redondeada al peso.

    Raises:
        ValidacionError: Si algún dato es obligatorio, inválido o está fuera de rango.
    """
    with localcontext() as contexto:
        contexto.prec = 40
        _validar(tea, monto, plazo)
        tasa = tasa_mensual(tea / Decimal(100))
        return redondear_peso(cuota_fija(monto, plazo, tasa))


def generar_tabla(tea: Decimal, monto: Decimal, plazo: int) -> list[AmortizacionFila]:
    """Genere los pagos mensuales y ajuste el último para cerrar el saldo.

    Args:
        tea: Tasa efectiva anual porcentual, entre 1 y 30, con hasta dos decimales.
        monto: Capital entre 10.000.000 y 500.000.000 pesos.
        plazo: Plazo entero entre 12 y 240 meses.

    Returns:
        Una fila por mes, con saldo final exactamente cero en el último mes.

    Raises:
        ValidacionError: Si algún dato es obligatorio, inválido o está fuera de rango.
    """
    with localcontext() as contexto:
        contexto.prec = 40
        _validar(tea, monto, plazo)
        tasa = tasa_mensual(tea / Decimal(100))
        cuota = redondear_peso(cuota_fija(monto, plazo, tasa))
        saldo = redondear_peso(monto)
        tabla = []
        for mes in range(1, plazo + 1):
            interes = redondear_peso(saldo * tasa)
            capital = saldo if mes == plazo else cuota - interes
            pago = capital + interes
            saldo_final = saldo - capital
            tabla.append(AmortizacionFila(mes, saldo, interes, capital, pago, saldo_final))
            saldo = saldo_final
        return tabla


def calcular_resumen(tea: Decimal, monto: Decimal, plazo: int) -> Resumen:
    """Sume las cuotas y los intereses de la tabla ajustada.

    Args:
        tea: Tasa efectiva anual porcentual, entre 1 y 30, con hasta dos decimales.
        monto: Capital entre 10.000.000 y 500.000.000 pesos.
        plazo: Plazo entero entre 12 y 240 meses.

    Returns:
        Total pagado y total de intereses redondeados al peso.

    Raises:
        ValidacionError: Si algún dato es obligatorio, inválido o está fuera de rango.
    """
    tabla = generar_tabla(tea, monto, plazo)
    with localcontext() as contexto:
        contexto.prec = 40
        return Resumen(
            redondear_peso(sum((fila.cuota for fila in tabla), Decimal(0))),
            redondear_peso(sum((fila.interes for fila in tabla), Decimal(0))),
        )
