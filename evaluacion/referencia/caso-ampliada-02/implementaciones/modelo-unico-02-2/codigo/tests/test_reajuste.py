"""Pruebas de reglas acordadas y decisiones de implementación documentadas."""

from datetime import date, datetime
from decimal import Decimal, localcontext

import pytest

from reajuste_arriendo import ErrorReajuste, ResultadoReajuste, calcular_reajuste


@pytest.fixture
def datos() -> dict[str, object]:
    return {
        "canon_actual": "1200000",
        "ipc_anterior": "5,20",
        "porcentaje_pactado": "10",
        "fecha_base": "2025-03-15",
        "fecha_reajuste": "2026-03-15",
    }


def test_ejemplo_confirmado(datos: dict[str, object]) -> None:
    resultado = calcular_reajuste(**datos)
    assert resultado == ResultadoReajuste(
        Decimal("5.20"), Decimal("1262400"), Decimal("62400")
    )
    assert isinstance(resultado.nuevo_canon, Decimal)
    assert isinstance(resultado.incremento, Decimal)
    assert isinstance(resultado.porcentaje_aplicado, Decimal)


@pytest.mark.parametrize(
    ("ipc", "pacto", "aplicado", "nuevo", "incremento"),
    [
        ("12", "5", "5", "1260000", "60000"),
        ("5.20", "10", "5.20", "1262400", "62400"),
        ("5", "5", "5", "1260000", "60000"),
        ("150", "100", "100", "2400000", "1200000"),
    ],
)
def test_menor_porcentaje_sobre_canon_actual(
    datos: dict[str, object],
    ipc: str,
    pacto: str,
    aplicado: str,
    nuevo: str,
    incremento: str,
) -> None:
    datos.update(ipc_anterior=ipc, porcentaje_pactado=pacto)
    assert calcular_reajuste(**datos) == ResultadoReajuste(
        Decimal(aplicado), Decimal(nuevo), Decimal(incremento)
    )


@pytest.mark.parametrize(
    ("ipc", "pacto"), [("0", "10"), ("-2.50", "10"), ("5.20", "0")]
)
def test_sin_ajuste_conserva_canon_exacto(
    datos: dict[str, object], ipc: str, pacto: str
) -> None:
    datos.update(canon_actual="1234567,50", ipc_anterior=ipc, porcentaje_pactado=pacto)
    assert calcular_reajuste(**datos) == ResultadoReajuste(
        Decimal(0), Decimal("1234567.50"), Decimal(0)
    )


def test_redondeo_independiente(datos: dict[str, object]) -> None:
    datos.update(canon_actual="1234567", ipc_anterior="5")
    resultado = calcular_reajuste(**datos)
    assert resultado.nuevo_canon == Decimal("1296300")
    assert resultado.incremento == Decimal("61700")
    assert resultado.nuevo_canon - Decimal("1234567") != resultado.incremento


@pytest.mark.parametrize(
    ("canon", "ipc", "nuevo", "incremento"),
    [
        ("1234550", "100", "2469100", "1234600"),
        ("1000", "5", "1100", "100"),
        ("1000", "4.99", "1000", "0"),
        ("1000", "5.01", "1100", "100"),
    ],
)
def test_centena_mas_cercana_y_mitades_arriba(
    datos: dict[str, object], canon: str, ipc: str, nuevo: str, incremento: str
) -> None:
    datos.update(canon_actual=canon, ipc_anterior=ipc, porcentaje_pactado="100")
    resultado = calcular_reajuste(**datos)
    assert resultado.nuevo_canon == Decimal(nuevo)
    assert resultado.incremento == Decimal(incremento)


def test_redondeo_sin_correccion_posterior_del_tope(datos: dict[str, object]) -> None:
    datos.update(canon_actual=1000, ipc_anterior=10, porcentaje_pactado=5)
    assert calcular_reajuste(**datos).nuevo_canon == Decimal(1100)


@pytest.mark.parametrize("canon", [1200000, Decimal("1200000"), " 1200000,00 "])
def test_formatos_numericos_admitidos(datos: dict[str, object], canon: object) -> None:
    datos["canon_actual"] = canon
    assert calcular_reajuste(**datos).nuevo_canon == Decimal("1262400")


def test_decimales_exactos_y_contexto_independiente(datos: dict[str, object]) -> None:
    datos.update(canon_actual="1000000000000000000000000000000", ipc_anterior="0.01")
    with localcontext() as contexto:
        contexto.prec = 3
        resultado = calcular_reajuste(**datos)
    assert resultado.nuevo_canon == Decimal("1000100000000000000000000000000")
    assert resultado.incremento == Decimal("100000000000000000000000000")


@pytest.mark.parametrize(
    "campo",
    ["canon_actual", "ipc_anterior", "porcentaje_pactado", "fecha_base", "fecha_reajuste"],
)
@pytest.mark.parametrize("ausente", [None, "", "  "])
def test_datos_obligatorios(datos: dict[str, object], campo: str, ausente: object) -> None:
    datos[campo] = ausente
    with pytest.raises(ErrorReajuste) as error:
        calcular_reajuste(**datos)
    assert str(error.value) == f"Falta el dato obligatorio: {campo}"


@pytest.mark.parametrize(
    "campo",
    ["canon_actual", "ipc_anterior", "porcentaje_pactado", "fecha_base", "fecha_reajuste"],
)
def test_argumento_omitido(datos: dict[str, object], campo: str) -> None:
    del datos[campo]
    with pytest.raises(ErrorReajuste) as error:
        calcular_reajuste(**datos)
    assert str(error.value) == f"Falta el dato obligatorio: {campo}"


@pytest.mark.parametrize("valor", [0, -1, "-0.01"])
def test_canon_fuera_de_rango(datos: dict[str, object], valor: object) -> None:
    datos["canon_actual"] = valor
    with pytest.raises(ErrorReajuste) as error:
        calcular_reajuste(**datos)
    assert str(error.value) == "canon_actual: debe ser mayor que cero"


@pytest.mark.parametrize("valor", ["-0.01", "100.01", -1, 101])
def test_pacto_fuera_de_rango(datos: dict[str, object], valor: object) -> None:
    datos["porcentaje_pactado"] = valor
    with pytest.raises(ErrorReajuste) as error:
        calcular_reajuste(**datos)
    assert str(error.value) == "porcentaje_pactado: debe estar entre 0 y 100"


@pytest.mark.parametrize("campo", ["canon_actual", "ipc_anterior", "porcentaje_pactado"])
@pytest.mark.parametrize(
    "valor",
    [
        True,
        5.2,
        "abc",
        "1.234.567",
        "1.234,50",
        "5%",
        "1e2",
        [],
        Decimal("NaN"),
        Decimal("sNaN"),
        Decimal("Infinity"),
        Decimal("-Infinity"),
    ],
)
def test_numero_invalido(datos: dict[str, object], campo: str, valor: object) -> None:
    datos[campo] = valor
    with pytest.raises(ErrorReajuste) as error:
        calcular_reajuste(**datos)
    assert str(error.value) == f"{campo}: debe ser un número decimal válido"


@pytest.mark.parametrize("campo", ["ipc_anterior", "porcentaje_pactado"])
@pytest.mark.parametrize("valor", ["5,201", "5.200", Decimal("0.001")])
def test_porcentajes_maximo_dos_decimales(
    datos: dict[str, object], campo: str, valor: object
) -> None:
    datos[campo] = valor
    with pytest.raises(ErrorReajuste) as error:
        calcular_reajuste(**datos)
    assert str(error.value) == f"{campo}: debe tener como máximo dos decimales"


@pytest.mark.parametrize("valor", [5, "5,2", "5,20", Decimal("5.20")])
def test_porcentajes_hasta_dos_decimales(datos: dict[str, object], valor: object) -> None:
    datos.update(ipc_anterior=valor, porcentaje_pactado=valor)
    assert calcular_reajuste(**datos).porcentaje_aplicado == Decimal(str(valor).replace(",", "."))


@pytest.mark.parametrize(
    "fecha", ["2026-03-15", "2026-03-16", "2028-03-15", date(2026, 3, 15)]
)
def test_desde_aniversario_inclusive(datos: dict[str, object], fecha: object) -> None:
    datos["fecha_reajuste"] = fecha
    assert calcular_reajuste(**datos).nuevo_canon == Decimal("1262400")


@pytest.mark.parametrize("fecha", ["2026-03-14", "2025-03-15", "2024-03-15"])
def test_plazo_insuficiente_o_fecha_anterior(datos: dict[str, object], fecha: str) -> None:
    datos["fecha_reajuste"] = fecha
    with pytest.raises(ErrorReajuste) as error:
        calcular_reajuste(**datos)
    assert str(error.value) == "El contrato aún no cumple doce meses desde el último reajuste"


def test_plazo_se_exige_aunque_no_haya_incremento(datos: dict[str, object]) -> None:
    datos.update(ipc_anterior="0", fecha_reajuste="2026-03-14")
    with pytest.raises(ErrorReajuste) as error:
        calcular_reajuste(**datos)
    assert str(error.value) == "El contrato aún no cumple doce meses desde el último reajuste"


@pytest.mark.parametrize(
    ("base", "reajuste"),
    [("2024-02-29", "2025-02-28"), (date(2023, 2, 28), date(2024, 2, 28))],
)
def test_aniversario_febrero(datos: dict[str, object], base: object, reajuste: object) -> None:
    datos.update(fecha_base=base, fecha_reajuste=reajuste)
    assert calcular_reajuste(**datos).nuevo_canon == Decimal("1262400")


def test_antes_del_aniversario_bisiesto(datos: dict[str, object]) -> None:
    datos.update(fecha_base="2024-02-29", fecha_reajuste="2025-02-27")
    with pytest.raises(ErrorReajuste) as error:
        calcular_reajuste(**datos)
    assert str(error.value) == "El contrato aún no cumple doce meses desde el último reajuste"


@pytest.mark.parametrize("campo", ["fecha_base", "fecha_reajuste"])
@pytest.mark.parametrize(
    "valor",
    ["2025-02-29", "15/03/2025", "20250315", "2025-3-15", 20250315, datetime(2025, 3, 15)],
)
def test_fecha_invalida(datos: dict[str, object], campo: str, valor: object) -> None:
    datos[campo] = valor
    with pytest.raises(ErrorReajuste) as error:
        calcular_reajuste(**datos)
    assert str(error.value) == f"{campo}: debe ser una fecha válida en formato AAAA-MM-DD"


def test_extremo_de_fechas_sin_aniversario_posible(datos: dict[str, object]) -> None:
    datos.update(fecha_base=date.max, fecha_reajuste=date.max)
    with pytest.raises(ErrorReajuste) as error:
        calcular_reajuste(**datos)
    assert str(error.value) == "El contrato aún no cumple doce meses desde el último reajuste"
