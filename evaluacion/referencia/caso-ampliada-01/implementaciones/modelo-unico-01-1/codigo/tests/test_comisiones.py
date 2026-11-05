"""Pruebas de reglas, ejemplos y decisiones documentadas."""

from dataclasses import FrozenInstanceError

import pytest

from comisiones import ResultadoComisiones, calcular_comisiones


@pytest.mark.parametrize(
    ("tipo", "valor", "numero", "inmobiliaria", "pagos"),
    [
        ("venta", 300_000_000, 1, 9_000_000, (3_600_000,)),
        ("arriendo", 1_000_000, 2, 1_000_000, (300_000, 300_000)),
        ("venta", 300_000_000, 2, 9_000_000, (1_800_000, 1_800_000)),
        ("arriendo", 2_000_000, 1, 2_000_000, (800_000,)),
        ("arriendo", 2_000_000, 2, 2_000_000, (400_000, 400_000)),
        ("venta", 1, 1, 0, (300_000,)),
        ("venta", 1, 2, 0, (300_000, 300_000)),
        ("arriendo", 1, 1, 1, (300_000,)),
        ("arriendo", 750_000, 1, 750_000, (300_000,)),
        ("arriendo", 1_500_000, 2, 1_500_000, (300_000, 300_000)),
    ],
)
def test_reglas_y_ejemplos(tipo, valor, numero, inmobiliaria, pagos) -> None:
    resultado = calcular_comisiones(
        tipo=tipo, valor=valor, numero_asesores=numero, estado="cerrado"
    )
    assert resultado == ResultadoComisiones(inmobiliaria, pagos)
    assert isinstance(resultado.comision_inmobiliaria, int)
    assert all(isinstance(pago, int) for pago in resultado.comisiones_asesores)


@pytest.mark.parametrize(
    ("valor", "inmobiliaria", "pago"),
    [
        (100_000_014, 3_000_000, 1_200_000),
        (100_000_016, 3_000_000, 1_200_000),
        (100_000_017, 3_000_001, 1_200_000),
        (100_000_050, 3_000_002, 1_200_001),
        (25_000_041, 750_001, 300_000),
        (25_000_042, 750_001, 300_001),
        (25_000_125, 750_004, 300_002),
    ],
)
def test_redondeo_y_calculo_sobre_comision_sin_redondear(valor, inmobiliaria, pago) -> None:
    resultado = calcular_comisiones(
        tipo="venta", valor=valor, numero_asesores=1, estado="cerrado"
    )
    assert resultado == ResultadoComisiones(inmobiliaria, (pago,))


def test_redondeo_individual_con_dos_asesores() -> None:
    resultado = calcular_comisiones(
        tipo="arriendo", valor=1_500_003, numero_asesores=2, estado="cerrado"
    )
    assert resultado.comisiones_asesores == (300_001, 300_001)


def test_enteros_grandes_sin_perdida_de_precision() -> None:
    valor = 10**100
    resultado = calcular_comisiones(
        tipo="venta", valor=valor, numero_asesores=2, estado="cerrado"
    )
    assert resultado == ResultadoComisiones(valor * 3 // 100, (valor * 6 // 1000,) * 2)


@pytest.mark.parametrize("tipo", ["venta", "arriendo"])
def test_negocio_abierto(tipo) -> None:
    with pytest.raises(ValueError) as error:
        calcular_comisiones(tipo=tipo, valor=1_000_000, numero_asesores=1, estado="abierto")
    assert str(error.value) == "El negocio aún no está cerrado"


@pytest.mark.parametrize("campo", ["tipo", "valor", "numero_asesores", "estado"])
@pytest.mark.parametrize("omitir", [True, False])
def test_datos_obligatorios(campo, omitir) -> None:
    datos = {"tipo": "venta", "valor": 300_000_000, "numero_asesores": 1, "estado": "cerrado"}
    if omitir:
        del datos[campo]
    else:
        datos[campo] = None
    with pytest.raises(ValueError) as error:
        calcular_comisiones(**datos)
    assert str(error.value) == f"Falta el dato obligatorio: {campo}"


def test_sin_ningun_dato() -> None:
    with pytest.raises(ValueError) as error:
        calcular_comisiones()
    assert str(error.value) == "Falta el dato obligatorio: tipo"


@pytest.mark.parametrize("tipo", ["", "Venta", "compra", 1, [], True])
def test_tipo_invalido(tipo) -> None:
    with pytest.raises(ValueError) as error:
        calcular_comisiones(tipo=tipo, valor=1, numero_asesores=1, estado="cerrado")
    assert str(error.value) == "El tipo de negocio debe ser venta o arriendo"


@pytest.mark.parametrize("valor", [0, -1, -300_000_000, 1.5, 1.0, "1000", True, False, []])
def test_valor_invalido(valor) -> None:
    with pytest.raises(ValueError) as error:
        calcular_comisiones(tipo="venta", valor=valor, numero_asesores=1, estado="cerrado")
    assert str(error.value) == (
        "El valor debe ser un entero mayor que cero, en pesos colombianos"
    )


@pytest.mark.parametrize("numero", [0, -1, 3, 1.0, "2", True, False, []])
def test_numero_asesores_invalido(numero) -> None:
    with pytest.raises(ValueError) as error:
        calcular_comisiones(tipo="venta", valor=1, numero_asesores=numero, estado="cerrado")
    assert str(error.value) == "El número de asesores debe ser 1 o 2"


@pytest.mark.parametrize("estado", ["", "Cerrado", "pendiente", 1, [], True])
def test_estado_invalido(estado) -> None:
    with pytest.raises(ValueError) as error:
        calcular_comisiones(tipo="venta", valor=1, numero_asesores=1, estado=estado)
    assert str(error.value) == "El estado debe ser cerrado o abierto"


def test_validacion_de_datos_antes_de_rechazar_abierto() -> None:
    with pytest.raises(ValueError) as error:
        calcular_comisiones(tipo="venta", valor=0, numero_asesores=1, estado="abierto")
    assert str(error.value) == (
        "El valor debe ser un entero mayor que cero, en pesos colombianos"
    )


def test_resultado_inmutable() -> None:
    resultado = calcular_comisiones(
        tipo="venta", valor=300_000_000, numero_asesores=1, estado="cerrado"
    )
    with pytest.raises(FrozenInstanceError):
        resultado.comision_inmobiliaria = 0
