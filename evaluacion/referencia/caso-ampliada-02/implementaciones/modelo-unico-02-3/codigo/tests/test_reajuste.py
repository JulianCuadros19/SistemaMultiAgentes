"""Pruebas de reglas acordadas y decisiones documentadas."""

import re
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
        "fecha_base": "2023-06-15",
        "fecha_reajuste": "2024-06-15",
    }


def test_ejemplo_cliente(datos):
    resultado = calcular_reajuste(**datos)
    assert resultado == ResultadoReajuste(
        Decimal("1262400"), Decimal("62400"), Decimal("5.20")
    )


def test_limite_pactado(datos):
    datos.update(porcentaje_pactado="3", ipc_anterior="5.20")
    resultado = calcular_reajuste(**datos)
    assert resultado.porcentaje_aplicado == Decimal("3")
    assert resultado.nuevo_canon == Decimal("1236000")
    assert resultado.incremento == Decimal("36000")


def test_porcentajes_iguales(datos):
    datos.update(porcentaje_pactado="5.20")
    assert calcular_reajuste(**datos).porcentaje_aplicado == Decimal("5.20")


@pytest.mark.parametrize("ipc", ["0", "-0.01", "-999999999999999999999999.99"])
def test_ipc_no_positivo_conserva_canon_sin_redondear(datos, ipc):
    datos.update(canon_actual="1234567.89", ipc_anterior=ipc)
    assert calcular_reajuste(**datos) == ResultadoReajuste(
        Decimal("1234567.89"), Decimal(0), Decimal(0)
    )


def test_ejemplo_redondeo_cliente(datos):
    datos.update(canon_actual="1234567", porcentaje_pactado="0")
    resultado = calcular_reajuste(**datos)
    assert resultado.nuevo_canon == Decimal("1234600")
    assert resultado.incremento == Decimal("33")
    assert resultado.porcentaje_aplicado == 0


@pytest.mark.parametrize(
    ("canon", "esperado"),
    [("1234549.99", "1234500"), ("1234550", "1234600"), ("1234567", "1234600")],
)
def test_redondeo_centena_y_empate(datos, canon, esperado):
    datos.update(canon_actual=canon, porcentaje_pactado="0")
    resultado = calcular_reajuste(**datos)
    assert resultado.nuevo_canon == Decimal(esperado)
    assert resultado.incremento == Decimal(esperado) - Decimal(canon)


def test_no_se_aplica_tope_adicional_despues_del_redondeo(datos):
    datos.update(canon_actual="1000001", porcentaje_pactado="5", ipc_anterior="8")
    assert calcular_reajuste(**datos).nuevo_canon == Decimal("1050000")
    datos.update(canon_actual="1000040")
    assert calcular_reajuste(**datos).nuevo_canon == Decimal("1050100")


@pytest.mark.parametrize("pactado", ["0", "100"])
def test_extremos_porcentaje_pactado(datos, pactado):
    datos.update(porcentaje_pactado=pactado, ipc_anterior="1000")
    assert calcular_reajuste(**datos).porcentaje_aplicado == Decimal(pactado)


def test_ipc_sin_limite_superior(datos):
    datos.update(ipc_anterior="999999999999999999999999999999.99")
    assert calcular_reajuste(**datos).porcentaje_aplicado == Decimal("10")


@pytest.mark.parametrize(
    "fecha", ["2024-06-14", "2023-06-15", "2023-01-01"]
)
def test_plazo_insuficiente_o_fecha_anterior(datos, fecha):
    datos.update(fecha_reajuste=fecha)
    with pytest.raises(ErrorReajuste) as error:
        calcular_reajuste(**datos)
    assert str(error.value) == (
        "El contrato aún no cumple doce meses desde el último reajuste"
    )


def test_plazo_se_valida_aun_con_ipc_negativo(datos):
    datos.update(ipc_anterior="-1", fecha_reajuste="2024-06-14")
    with pytest.raises(ErrorReajuste, match="aún no cumple doce meses"):
        calcular_reajuste(**datos)


@pytest.mark.parametrize("fecha", ["2024-06-15", "2024-06-16", "2026-06-15"])
def test_aniversario_o_fecha_posterior(datos, fecha):
    datos.update(fecha_reajuste=fecha)
    # Un intervalo mayor no acumula aumentos de años omitidos.
    assert calcular_reajuste(**datos).nuevo_canon == Decimal("1262400")


@pytest.mark.parametrize(
    ("fecha", "permitido"), [("2025-02-27", False), ("2025-02-28", True)]
)
def test_aniversario_del_29_de_febrero(datos, fecha, permitido):
    datos.update(fecha_base="2024-02-29", fecha_reajuste=fecha)
    if permitido:
        assert calcular_reajuste(**datos).nuevo_canon == Decimal("1262400")
    else:
        with pytest.raises(ErrorReajuste, match="aún no cumple doce meses"):
            calcular_reajuste(**datos)


def test_ultimo_anio_representable(datos):
    datos.update(fecha_base="9999-01-01", fecha_reajuste="9999-12-31")
    with pytest.raises(ErrorReajuste, match="aún no cumple doce meses"):
        calcular_reajuste(**datos)


@pytest.mark.parametrize(
    "campo",
    ["canon_actual", "porcentaje_pactado", "ipc_anterior", "fecha_base", "fecha_reajuste"],
)
@pytest.mark.parametrize("omitir", [True, False])
def test_datos_obligatorios(datos, campo, omitir):
    if omitir:
        del datos[campo]
    else:
        datos[campo] = None
    with pytest.raises(ErrorReajuste) as error:
        calcular_reajuste(**datos)
    assert str(error.value) == f"Falta el dato obligatorio: {campo}"


@pytest.mark.parametrize("canon", ["0", "-1", "-0.01"])
def test_canon_debe_ser_positivo(datos, canon):
    datos.update(canon_actual=canon)
    with pytest.raises(ErrorReajuste, match="canon_actual debe ser mayor que cero"):
        calcular_reajuste(**datos)


@pytest.mark.parametrize("pactado", ["-0.01", "100.01"])
def test_porcentaje_fuera_de_rango(datos, pactado):
    datos.update(porcentaje_pactado=pactado)
    with pytest.raises(ErrorReajuste, match="porcentaje_pactado debe estar entre 0 y 100"):
        calcular_reajuste(**datos)


@pytest.mark.parametrize("campo", ["porcentaje_pactado", "ipc_anterior"])
@pytest.mark.parametrize("valor", ["5.201", "0.001"])
def test_porcentajes_con_mas_de_dos_decimales(datos, campo, valor):
    datos[campo] = valor
    with pytest.raises(ErrorReajuste, match=f"{campo} debe tener hasta dos decimales"):
        calcular_reajuste(**datos)


def test_ceros_finales_no_cuentan_como_precision_adicional(datos):
    datos.update(porcentaje_pactado="10.0000", ipc_anterior="5.2000")
    assert calcular_reajuste(**datos).nuevo_canon == Decimal("1262400")


@pytest.mark.parametrize("campo", ["canon_actual", "porcentaje_pactado", "ipc_anterior"])
@pytest.mark.parametrize("valor", ["", "texto", "5,20", "NaN", "Infinity", True, 5.2])
def test_formato_numerico_invalido(datos, campo, valor):
    datos[campo] = valor
    with pytest.raises(ErrorReajuste) as error:
        calcular_reajuste(**datos)
    assert str(error.value) == f"{campo} debe ser un número decimal válido"


@pytest.mark.parametrize("campo", ["fecha_base", "fecha_reajuste"])
@pytest.mark.parametrize(
    "valor", ["", "2024-02-30", "15/06/2024", "20240615", 20240615, datetime(2024, 6, 15)]
)
def test_fechas_invalidas(datos, campo, valor):
    datos[campo] = valor
    mensaje = f"{campo} debe ser una fecha válida en formato AAAA-MM-DD"
    with pytest.raises(ErrorReajuste, match=re.escape(mensaje)):
        calcular_reajuste(**datos)


def test_formatos_python_admitidos(datos):
    datos.update(
        canon_actual=1200000,
        porcentaje_pactado=Decimal("10"),
        ipc_anterior=Decimal("5.20"),
        fecha_base=date(2023, 6, 15),
        fecha_reajuste=date(2024, 6, 15),
    )
    assert calcular_reajuste(**datos).nuevo_canon == Decimal("1262400")


def test_precision_independiente_del_contexto_decimal(datos):
    datos.update(canon_actual="123456789012345678901234567890.12")
    with localcontext() as contexto:
        contexto.prec = 6
        resultado = calcular_reajuste(**datos)
    assert resultado.nuevo_canon == Decimal("129876542040987654204098765400")
    assert resultado.incremento == Decimal("6419753028641975302864197509.88")


def test_canon_positivo_pequeno_no_tiene_limite_inventado(datos):
    datos.update(canon_actual="0.01")
    resultado = calcular_reajuste(**datos)
    assert resultado.nuevo_canon == Decimal(0)
    assert resultado.incremento == Decimal("-0.01")
