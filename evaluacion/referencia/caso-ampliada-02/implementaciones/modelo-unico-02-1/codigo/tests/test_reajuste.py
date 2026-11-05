"""Pruebas de las reglas acordadas y las decisiones documentadas."""

from datetime import date, datetime
from decimal import Decimal, localcontext

import pytest

from reajuste_arriendo import ErrorReajuste, ResultadoReajuste, calcular_reajuste


@pytest.fixture
def datos():
    return {
        "canon_actual": "1200000",
        "porcentaje_pactado": "10",
        "ipc_anterior": "5.20",
        "fecha_referencia": "2024-06-15",
        "fecha_reajuste": "2025-06-15",
    }


def test_ejemplo_cliente(datos):
    resultado = calcular_reajuste(**datos)
    assert resultado == ResultadoReajuste(Decimal("5.20"), Decimal(1262400), Decimal(62400))
    assert isinstance(resultado.porcentaje_aplicado, Decimal)
    assert isinstance(resultado.nuevo_canon, Decimal)
    assert isinstance(resultado.incremento, Decimal)


@pytest.mark.parametrize(
    ("pactado", "ipc", "aplicado", "nuevo"),
    [
        ("10", "5.20", "5.20", "1262400"),
        ("3", "5.20", "3", "1236000"),
        ("5.20", "5.20", "5.20", "1262400"),
        ("100", "150", "100", "2400000"),
    ],
)
def test_aplica_menor_porcentaje(datos, pactado, ipc, aplicado, nuevo):
    datos.update(porcentaje_pactado=pactado, ipc_anterior=ipc)
    resultado = calcular_reajuste(**datos)
    assert resultado.porcentaje_aplicado == Decimal(aplicado)
    assert resultado.nuevo_canon == Decimal(nuevo)
    assert resultado.incremento == Decimal(nuevo) - Decimal(datos["canon_actual"])


@pytest.mark.parametrize(("pactado", "ipc"), [("10", "0"), ("10", "-5.20"), ("0", "5.20")])
def test_sin_aumento_no_redondea(datos, pactado, ipc):
    datos.update(canon_actual="1001", porcentaje_pactado=pactado, ipc_anterior=ipc)
    assert calcular_reajuste(**datos) == ResultadoReajuste(
        Decimal(0), Decimal(1001), Decimal(0)
    )


def test_ejemplo_cliente_con_centenas(datos):
    datos["canon_actual"] = "1001"
    assert calcular_reajuste(**datos) == ResultadoReajuste(
        Decimal("5.20"), Decimal(1100), Decimal(99)
    )


def test_no_limita_importe_despues_del_redondeo(datos):
    datos.update(canon_actual="1001", porcentaje_pactado="5.20")
    resultado = calcular_reajuste(**datos)
    assert resultado.nuevo_canon == Decimal(1100)
    assert resultado.incremento > Decimal(1001) * Decimal("0.052")


@pytest.mark.parametrize(
    ("canon", "ipc", "nuevo", "incremento"),
    [
        ("1001", "0.01", "1000", "-1"),
        ("1000", "5", "1100", "100"),
        ("1000", "4.99", "1000", "0"),
        ("1000", "5.01", "1100", "100"),
        ("1000", "25", "1300", "300"),
    ],
)
def test_redondeo_incluye_disminucion_y_empate(datos, canon, ipc, nuevo, incremento):
    datos.update(canon_actual=canon, porcentaje_pactado="100", ipc_anterior=ipc)
    resultado = calcular_reajuste(**datos)
    assert resultado.nuevo_canon == Decimal(nuevo)
    assert resultado.incremento == Decimal(incremento)


@pytest.mark.parametrize("fecha", ["2025-06-14", "2024-06-15", "2024-01-01"])
def test_rechazo_antes_de_doce_meses(datos, fecha):
    datos["fecha_reajuste"] = fecha
    with pytest.raises(ErrorReajuste) as error:
        calcular_reajuste(**datos)
    assert str(error.value) == (
        "El contrato aún no cumple doce meses desde el último reajuste"
    )


@pytest.mark.parametrize("fecha", ["2025-06-15", "2025-06-16", "2027-06-15"])
def test_aniversario_y_fechas_posteriores(datos, fecha):
    datos["fecha_reajuste"] = fecha
    assert calcular_reajuste(**datos).nuevo_canon == Decimal(1262400)


def test_plazo_se_valida_incluso_sin_aumento(datos):
    datos.update(ipc_anterior="0", fecha_reajuste="2025-06-14")
    with pytest.raises(ErrorReajuste, match="^El contrato aún no cumple doce meses"):
        calcular_reajuste(**datos)


@pytest.mark.parametrize(
    "campo",
    ["canon_actual", "porcentaje_pactado", "ipc_anterior", "fecha_referencia", "fecha_reajuste"],
)
def test_dato_omitido(datos, campo):
    del datos[campo]
    with pytest.raises(ErrorReajuste) as error:
        calcular_reajuste(**datos)
    assert str(error.value) == f"Falta el dato obligatorio: {campo}"


@pytest.mark.parametrize(
    "campo",
    ["canon_actual", "porcentaje_pactado", "ipc_anterior", "fecha_referencia", "fecha_reajuste"],
)
def test_dato_nulo(datos, campo):
    datos[campo] = None
    with pytest.raises(ErrorReajuste) as error:
        calcular_reajuste(**datos)
    assert str(error.value) == f"Falta el dato obligatorio: {campo}"


@pytest.mark.parametrize("canon", ["0", "-1", "-0.01"])
def test_canon_debe_ser_positivo(datos, canon):
    datos["canon_actual"] = canon
    with pytest.raises(ErrorReajuste, match="^El canon actual debe ser mayor que cero$"):
        calcular_reajuste(**datos)


@pytest.mark.parametrize("pactado", ["-0.01", "100.01"])
def test_pactado_fuera_de_rango(datos, pactado):
    datos["porcentaje_pactado"] = pactado
    with pytest.raises(ErrorReajuste, match="^El porcentaje pactado debe estar entre 0 y 100$"):
        calcular_reajuste(**datos)


@pytest.mark.parametrize("campo", ["porcentaje_pactado", "ipc_anterior"])
@pytest.mark.parametrize("valor", ["5.201", "0.001", "-0.001"])
def test_porcentajes_con_mas_de_dos_decimales(datos, campo, valor):
    datos[campo] = valor
    with pytest.raises(ErrorReajuste) as error:
        calcular_reajuste(**datos)
    assert str(error.value) == f"El {campo} debe tener como máximo dos decimales"


@pytest.mark.parametrize("campo", ["canon_actual", "porcentaje_pactado", "ipc_anterior"])
@pytest.mark.parametrize(
    "valor", ["", "abc", "5,20", "NaN", "sNaN", "Infinity", "-Infinity", True, 5.2, []]
)
def test_numeros_invalidos(datos, campo, valor):
    datos[campo] = valor
    with pytest.raises(ErrorReajuste) as error:
        calcular_reajuste(**datos)
    assert str(error.value) == f"Dato inválido: {campo}"


@pytest.mark.parametrize("campo", ["fecha_referencia", "fecha_reajuste"])
@pytest.mark.parametrize(
    "valor",
    ["", "15/06/2025", "2025-02-29", "20250615", "2025-W24-7", 20250615,
     datetime(2025, 6, 15), "2025-06-15T00:00:00"],
)
def test_fechas_invalidas(datos, campo, valor):
    datos[campo] = valor
    with pytest.raises(ErrorReajuste) as error:
        calcular_reajuste(**datos)
    assert str(error.value) == f"Dato inválido: {campo}"


def test_acepta_enteros_decimales_y_fechas(datos):
    datos.update(
        canon_actual=1200000,
        porcentaje_pactado=Decimal("10"),
        ipc_anterior=Decimal("5.20"),
        fecha_referencia=date(2024, 6, 15),
        fecha_reajuste=date(2025, 6, 15),
    )
    assert calcular_reajuste(**datos).nuevo_canon == Decimal(1262400)


def test_admite_canon_fraccionario(datos):
    datos["canon_actual"] = "1001.50"
    resultado = calcular_reajuste(**datos)
    assert resultado.nuevo_canon == Decimal(1100)
    assert resultado.incremento == Decimal("98.50")


def test_ceros_decimales_adicionales_y_notacion_cientifica(datos):
    datos.update(canon_actual="1.2E6", porcentaje_pactado="10.000", ipc_anterior=" 5.2000 ")
    assert calcular_reajuste(**datos).nuevo_canon == Decimal(1262400)


@pytest.mark.parametrize(("fecha", "aceptado"), [("2025-02-27", False), ("2025-02-28", True)])
def test_aniversario_del_29_de_febrero(datos, fecha, aceptado):
    datos.update(fecha_referencia="2024-02-29", fecha_reajuste=fecha)
    if aceptado:
        assert calcular_reajuste(**datos).nuevo_canon == Decimal(1262400)
    else:
        with pytest.raises(ErrorReajuste, match="^El contrato aún no cumple doce meses"):
            calcular_reajuste(**datos)


def test_referencia_en_ultimo_anio_representable(datos):
    datos.update(fecha_referencia="9999-01-01", fecha_reajuste="9999-12-31")
    with pytest.raises(ErrorReajuste, match="^El contrato aún no cumple doce meses"):
        calcular_reajuste(**datos)


def test_calculo_no_depende_de_precision_decimal_del_llamador(datos):
    with localcontext() as contexto:
        contexto.prec = 4
        resultado = calcular_reajuste(**datos)
    assert resultado.nuevo_canon == Decimal(1262400)
    assert resultado.incremento == Decimal(62400)


def test_canon_grande_no_pierde_precision(datos):
    datos.update(canon_actual="1000000000000000000000000000001", ipc_anterior="10")
    resultado = calcular_reajuste(**datos)
    assert resultado.nuevo_canon == Decimal("1100000000000000000000000000000")
    assert resultado.incremento == Decimal("99999999999999999999999999999")
