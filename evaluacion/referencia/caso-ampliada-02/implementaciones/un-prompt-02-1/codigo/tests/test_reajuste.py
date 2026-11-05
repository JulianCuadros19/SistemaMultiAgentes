"""Pruebas de las reglas, ejemplos, decisiones y errores del reajuste."""

from datetime import date, datetime
from decimal import Decimal

import pytest

from reajuste_arriendo import ResultadoReajuste, calcular_reajuste


@pytest.mark.parametrize(
    ("canon", "pactado", "ipc", "porcentaje", "nuevo", "incremento"),
    [
        ("1200000", "10", "5.20", "5.20", "1262400", "62400"),
        ("950000", "3", "5.20", "3", "978500", "28500"),
    ],
)
def test_ejemplos_del_cliente(canon, pactado, ipc, porcentaje, nuevo, incremento):
    resultado = calcular_reajuste(canon, pactado, ipc, date(2023, 6, 1), date(2024, 6, 1))
    assert resultado == ResultadoReajuste(
        Decimal(nuevo), Decimal(porcentaje), Decimal(incremento)
    )


@pytest.mark.parametrize(
    ("pactado", "ipc", "aplicado"),
    [(10, "5.20", "5.20"), (3, "5.20", "3"), (5, 5, "5"), (0, 5, "0")],
)
def test_aplica_el_menor_porcentaje(pactado, ipc, aplicado):
    resultado = calcular_reajuste(100000, pactado, ipc, date(2023, 1, 1), date(2024, 1, 1))
    assert resultado.porcentaje_aplicado == Decimal(aplicado)
    assert resultado.nuevo_canon == Decimal(100000) * (1 + Decimal(aplicado) / 100)
    assert resultado.incremento == resultado.nuevo_canon - Decimal(100000)


@pytest.mark.parametrize(
    ("canon", "nuevo"),
    [("1234567", "1234600"), ("1234549", "1234500"), ("1234550", "1234600")],
)
def test_redondeo_a_centena_y_empate_hacia_arriba(canon, nuevo):
    resultado = calcular_reajuste(canon, 0, 5, date(2023, 1, 1), date(2024, 1, 1))
    assert resultado.nuevo_canon == Decimal(nuevo)
    assert resultado.incremento == Decimal(nuevo) - Decimal(canon)


@pytest.mark.parametrize("ipc", [0, "-0.01", "-5.20", "-150"])
def test_ipc_no_positivo_conserva_canon_sin_redondear(ipc):
    resultado = calcular_reajuste("1234567.25", 10, ipc, date(2023, 1, 1), date(2024, 1, 1))
    assert resultado == ResultadoReajuste(Decimal("1234567.25"), Decimal(0), Decimal(0))


@pytest.mark.parametrize(
    ("base", "reajuste"),
    [
        (date(2023, 6, 15), date(2024, 6, 15)),
        (date(2023, 6, 15), date(2024, 6, 16)),
        (date(2020, 6, 15), date(2024, 1, 1)),
        (date(2024, 2, 29), date(2025, 2, 28)),
        (date(2023, 2, 28), date(2024, 2, 28)),
    ],
)
def test_acepta_al_menos_doce_meses_calendario(base, reajuste):
    resultado = calcular_reajuste(100000, 10, 5, base, reajuste)
    assert resultado.nuevo_canon == Decimal(105000)


@pytest.mark.parametrize(
    ("base", "reajuste"),
    [
        (date(2023, 6, 15), date(2024, 6, 14)),
        (date(2023, 1, 1), date(2023, 12, 31)),
        (date(2024, 1, 1), date(2024, 1, 1)),
        (date(2024, 1, 1), date(2023, 1, 1)),
        (date(2024, 2, 29), date(2025, 2, 27)),
        (date(9999, 1, 1), date(9999, 12, 31)),
    ],
)
def test_rechaza_plazo_insuficiente_con_mensaje_exacto(base, reajuste):
    with pytest.raises(ValueError) as error:
        calcular_reajuste(100000, 10, 5, base, reajuste)
    assert str(error.value) == "El contrato aún no cumple doce meses desde el último reajuste"


@pytest.mark.parametrize("ipc", [0, -5])
def test_plazo_obligatorio_incluso_si_ipc_no_es_positivo(ipc):
    with pytest.raises(ValueError, match="El contrato aún no cumple doce meses"):
        calcular_reajuste(100000, 10, ipc, date(2024, 1, 1), date(2024, 6, 1))


@pytest.mark.parametrize("canon", [0, -1, "-0.01"])
def test_canon_debe_ser_mayor_que_cero(canon):
    with pytest.raises(ValueError, match="canon_actual debe ser mayor que cero"):
        calcular_reajuste(canon, 10, 5, date(2023, 1, 1), date(2024, 1, 1))


@pytest.mark.parametrize("pactado", ["-0.01", "100.01"])
def test_porcentaje_pactado_fuera_de_rango(pactado):
    with pytest.raises(ValueError, match="porcentaje_pactado debe estar entre 0 y 100"):
        calcular_reajuste(100000, pactado, 5, date(2023, 1, 1), date(2024, 1, 1))


@pytest.mark.parametrize("pactado", [0, 100])
def test_limites_del_porcentaje_pactado_son_inclusivos(pactado):
    resultado = calcular_reajuste(100000, pactado, 150, date(2023, 1, 1), date(2024, 1, 1))
    assert resultado.porcentaje_aplicado == Decimal(pactado)


@pytest.mark.parametrize("campo", ["porcentaje_pactado", "ipc_anterior"])
@pytest.mark.parametrize("valor", ["5.201", "-0.001"])
def test_porcentajes_rechazan_mas_de_dos_decimales(campo, valor):
    datos = {
        "canon_actual": 100000,
        "porcentaje_pactado": 10,
        "ipc_anterior": 5,
        "fecha_base": date(2023, 1, 1),
        "fecha_reajuste": date(2024, 1, 1),
    }
    datos[campo] = valor
    with pytest.raises(ValueError, match=f"{campo} debe tener hasta dos decimales"):
        calcular_reajuste(**datos)


@pytest.mark.parametrize("campo", ["canon_actual", "porcentaje_pactado", "ipc_anterior"])
@pytest.mark.parametrize("valor", [None, "", "texto", True, "NaN", "Infinity", "-Infinity"])
def test_numeros_obligatorios_validos_y_finitos(campo, valor):
    datos = {
        "canon_actual": 100000,
        "porcentaje_pactado": 10,
        "ipc_anterior": 5,
        "fecha_base": date(2023, 1, 1),
        "fecha_reajuste": date(2024, 1, 1),
    }
    datos[campo] = valor
    with pytest.raises(ValueError, match=f"{campo} debe ser un número finito obligatorio"):
        calcular_reajuste(**datos)


@pytest.mark.parametrize("campo", ["fecha_base", "fecha_reajuste"])
@pytest.mark.parametrize("valor", [None, "2024-01-01", datetime(2024, 1, 1), 0])
def test_fechas_obligatorias_de_tipo_date(campo, valor):
    datos = {
        "canon_actual": 100000,
        "porcentaje_pactado": 10,
        "ipc_anterior": 5,
        "fecha_base": date(2023, 1, 1),
        "fecha_reajuste": date(2024, 1, 1),
    }
    datos[campo] = valor
    with pytest.raises(ValueError, match=f"{campo} debe ser una fecha obligatoria de tipo date"):
        calcular_reajuste(**datos)


@pytest.mark.parametrize(
    "campo",
    ["canon_actual", "porcentaje_pactado", "ipc_anterior", "fecha_base", "fecha_reajuste"],
)
def test_todos_los_argumentos_son_obligatorios(campo):
    datos = {
        "canon_actual": 100000,
        "porcentaje_pactado": 10,
        "ipc_anterior": 5,
        "fecha_base": date(2023, 1, 1),
        "fecha_reajuste": date(2024, 1, 1),
    }
    del datos[campo]
    with pytest.raises(TypeError):
        calcular_reajuste(**datos)


@pytest.mark.parametrize("ipc", [5.2, Decimal("5.20"), "5.2000"])
def test_formatos_numericos_y_ceros_finales(ipc):
    resultado = calcular_reajuste(1200000, 10, ipc, date(2023, 1, 1), date(2024, 1, 1))
    assert resultado == ResultadoReajuste(Decimal(1262400), Decimal("5.20"), Decimal(62400))


def test_canon_decimal_e_incremento_exactos():
    resultado = calcular_reajuste("100000.25", 5, 5, date(2023, 1, 1), date(2024, 1, 1))
    assert resultado.nuevo_canon == Decimal(105000)
    assert resultado.incremento == Decimal("4999.75")


def test_precision_independiente_de_importes_grandes():
    canon = "1000000000000000000000000000000"
    resultado = calcular_reajuste(canon, 1, 1, date(2023, 1, 1), date(2024, 1, 1))
    assert resultado.nuevo_canon == Decimal("1010000000000000000000000000000")
    assert resultado.incremento == Decimal("10000000000000000000000000000")
