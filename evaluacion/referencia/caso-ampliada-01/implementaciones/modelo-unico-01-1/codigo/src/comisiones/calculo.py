"""Reglas y validación del cálculo de comisiones en pesos enteros."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ResultadoComisiones:
    """Importes finales en pesos colombianos, sin decimales.

    Attributes:
        comision_inmobiliaria: Comisión bruta de la inmobiliaria, redondeada.
        comisiones_asesores: Pago final de cada asesor, en orden de posición.
    """

    comision_inmobiliaria: int
    comisiones_asesores: tuple[int, ...]


def _validar_obligatorios(
    tipo: str | None,
    valor: int | None,
    numero_asesores: int | None,
    estado: str | None,
) -> None:
    datos = (
        ("tipo", tipo),
        ("valor", valor),
        ("numero_asesores", numero_asesores),
        ("estado", estado),
    )
    for nombre, dato in datos:
        if dato is None:
            raise ValueError(f"Falta el dato obligatorio: {nombre}")


def _validar_datos(tipo: str, valor: int, numero_asesores: int, estado: str) -> None:
    if not isinstance(tipo, str) or tipo not in ("venta", "arriendo"):
        raise ValueError("El tipo de negocio debe ser venta o arriendo")
    if isinstance(valor, bool) or not isinstance(valor, int) or valor <= 0:
        raise ValueError("El valor debe ser un entero mayor que cero, en pesos colombianos")
    if (
        isinstance(numero_asesores, bool)
        or not isinstance(numero_asesores, int)
        or numero_asesores not in (1, 2)
    ):
        raise ValueError("El número de asesores debe ser 1 o 2")
    if not isinstance(estado, str) or estado not in ("cerrado", "abierto"):
        raise ValueError("El estado debe ser cerrado o abierto")


def _redondear(numerador: int, denominador: int) -> int:
    entero, resto = divmod(numerador, denominador)
    return entero + int(2 * resto >= denominador)


def calcular_comisiones(
    *,
    tipo: str | None = None,
    valor: int | None = None,
    numero_asesores: int | None = None,
    estado: str | None = None,
) -> ResultadoComisiones:
    """Calcule las comisiones de un único negocio cerrado.

    La venta genera el 3 % del valor y el arriendo el primer canon completo.
    Cada asesor recibe su parte igual del 40 %, con mínimo de 300.000 pesos.
    El cálculo usa la comisión sin redondear y redondea los resultados al peso
    más cercano; los empates de medio peso se resuelven hacia arriba.

    Args:
        tipo: Literal exacto 'venta' o 'arriendo'.
        valor: Precio de venta o primer canon mensual, entero positivo en COP.
        numero_asesores: Uno o dos asesores; no se aceptan booleanos.
        estado: Literal exacto 'cerrado' o 'abierto'.

    Returns:
        Comisión bruta de la inmobiliaria y pagos finales individuales.

    Raises:
        ValueError: Si falta un dato, un dato no es válido o el negocio está
            abierto. Los datos omitidos o None se consideran faltantes.
    """
    _validar_obligatorios(tipo, valor, numero_asesores, estado)
    # La comprobación explícita permite estrechar los tipos sin usar assert.
    if tipo is None or valor is None or numero_asesores is None or estado is None:
        raise ValueError("Faltan datos obligatorios")
    _validar_datos(tipo, valor, numero_asesores, estado)
    if estado == "abierto":
        raise ValueError("El negocio aún no está cerrado")

    numerador = valor * 3 if tipo == "venta" else valor
    denominador = 100 if tipo == "venta" else 1
    comision_inmobiliaria = _redondear(numerador, denominador)
    pago_asesor = max(
        300_000,
        _redondear(numerador * 40, denominador * 100 * numero_asesores),
    )
    return ResultadoComisiones(
        comision_inmobiliaria=comision_inmobiliaria,
        comisiones_asesores=(pago_asesor,) * numero_asesores,
    )
