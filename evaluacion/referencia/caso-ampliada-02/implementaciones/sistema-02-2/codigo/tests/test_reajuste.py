"""Pruebas de aceptación, restricciones y reglas de reajuste."""

from datetime import date
from decimal import Decimal

import pytest

from aplicacion.calculo_reajuste import calcular_reajuste
from dominio.reajuste import (
    DatosObligatoriosFaltantes,
    PeriodoInsuficienteDoceMeses,
    ResultadoReajuste,
    ValorInvalido,
    calcular_porcentaje_aplicable,
    redondear_a_centena_mas_cercana,
    validar_periodo_doce_meses,
)


def test_rf_01_esc_01_ipc_dentro_del_pacto():
    resultado = calcular_reajuste(
        Decimal("1000000"), Decimal("5.20"), Decimal("7.00"),
        date(2024, 1, 15), date(2025, 1, 15),
    )
    assert resultado.porcentaje_aplicado == Decimal("5.20")
    assert resultado.valor_incremento == Decimal("52000")
    assert resultado.canon_reajustado == Decimal("1052000")


def test_rf_01_esc_02_limite_pactado():
    resultado = calcular_reajuste(
        Decimal("1000000"), Decimal("8.50"), Decimal("5.00"),
        date(2024, 1, 15), date(2025, 1, 15),
    )
    assert resultado.porcentaje_aplicado == Decimal("5.00")
    assert resultado.valor_incremento == Decimal("50000")
    assert resultado.canon_reajustado == Decimal("1050000")


def test_rf_01_esc_03_ipc_cero():
    resultado = calcular_reajuste(
        Decimal("1000000"), Decimal("0.00"), Decimal("7.00"),
        date(2024, 1, 15), date(2025, 1, 15),
    )
    assert resultado.porcentaje_aplicado == Decimal("0.00")
    assert resultado.valor_incremento == Decimal("0")
    assert resultado.canon_reajustado == Decimal("1000000")


def test_rf_01_esc_04_periodo_insuficiente():
    inicio = date(2025, 1, 1)
    reajuste = date(2025, 10, 1)
    with pytest.raises(PeriodoInsuficienteDoceMeses):
        calcular_reajuste(
            Decimal("1000000"), Decimal("5.20"), Decimal("7.00"), inicio, reajuste,
        )
    with pytest.raises(PeriodoInsuficienteDoceMeses):
        validar_periodo_doce_meses(inicio, reajuste)


def test_rf_01_esc_05_canon_faltante():
    with pytest.raises(DatosObligatoriosFaltantes):
        calcular_reajuste(
            None, Decimal("5.20"), Decimal("7.00"),
            date(2024, 1, 15), date(2025, 1, 15),
        )


def test_ipc_faltante():
    with pytest.raises(DatosObligatoriosFaltantes):
        calcular_reajuste(
            Decimal("1000000"), None, Decimal("7"),
            date(2024, 1, 15), date(2025, 1, 15),
        )
    with pytest.raises(DatosObligatoriosFaltantes):
        calcular_porcentaje_aplicable(None, Decimal("7"))


@pytest.mark.parametrize(
    ("canon", "ipc", "pacto"),
    [
        ("0", "5.20", "7"),
        ("-0.01", "5.20", "7"),
        ("100", "5.20", "-0.01"),
        ("100", "5.20", "100.01"),
        ("100", "5.201", "7"),
        ("100", "5.20", "7.001"),
        ("NaN", "5.20", "7"),
        ("100", "Infinity", "7"),
        ("100", "5.20", "NaN"),
    ],
)
def test_valores_invalidos(canon, ipc, pacto):
    with pytest.raises(ValorInvalido):
        calcular_reajuste(
            Decimal(canon), Decimal(ipc), Decimal(pacto),
            date(2024, 1, 15), date(2025, 1, 15),
        )


@pytest.mark.parametrize("pacto", ["0", "100"])
def test_limites_inclusivos_del_pacto(pacto):
    resultado = calcular_reajuste(
        Decimal("100"), Decimal("100.00"), Decimal(pacto),
        date(2024, 1, 15), date(2025, 1, 15),
    )
    assert resultado.porcentaje_aplicado == Decimal(pacto)
    assert resultado.canon_reajustado == (Decimal("100") if pacto == "0" else Decimal("200"))


def test_canon_positivo_minimo_sin_limite_inferior_adicional():
    resultado = calcular_reajuste(
        Decimal("0.01"), Decimal("5.20"), Decimal("7"),
        date(2024, 1, 15), date(2025, 1, 15),
    )
    assert resultado.canon_reajustado == Decimal("0")
    assert resultado.valor_incremento == Decimal("-0.01")


def test_ipc_negativo_y_ceros_decimales_adicionales():
    resultado = calcular_reajuste(
        Decimal("1000000"), Decimal("-1.2000"), Decimal("7.000"),
        date(2024, 1, 15), date(2025, 1, 15),
    )
    assert resultado.porcentaje_aplicado == Decimal("0")
    assert resultado.canon_reajustado == Decimal("1000000")
    assert resultado.valor_incremento == Decimal("0")


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [("1049.99", "1000"), ("1050", "1100"), ("1050.01", "1100"), ("1000", "1000")],
)
def test_redondeo_a_centenas(valor, esperado):
    assert redondear_a_centena_mas_cercana(Decimal(valor)) == Decimal(esperado)


def test_incremento_efectivo_tras_redondear():
    resultado = calcular_reajuste(
        Decimal("1000"), Decimal("5"), Decimal("7"),
        date(2024, 1, 15), date(2025, 1, 15),
    )
    assert resultado.canon_reajustado == Decimal("1100")
    assert resultado.valor_incremento == Decimal("100")
    assert resultado.porcentaje_aplicado == Decimal("5")


def test_dia_anterior_al_aniversario():
    with pytest.raises(PeriodoInsuficienteDoceMeses):
        validar_periodo_doce_meses(date(2024, 1, 15), date(2025, 1, 14))
    assert validar_periodo_doce_meses(date(2024, 1, 15), date(2025, 1, 15)) is None


def test_aniversario_bisiesto():
    with pytest.raises(PeriodoInsuficienteDoceMeses):
        validar_periodo_doce_meses(date(2024, 2, 29), date(2025, 2, 27))
    assert validar_periodo_doce_meses(date(2024, 2, 29), date(2025, 2, 28)) is None


def test_fecha_anterior_al_inicio():
    with pytest.raises(PeriodoInsuficienteDoceMeses):
        validar_periodo_doce_meses(date(2025, 1, 15), date(2024, 1, 15))


def test_porcentaje_auxiliar():
    assert calcular_porcentaje_aplicable(Decimal("-1"), Decimal("7")) == Decimal("0")
    assert calcular_porcentaje_aplicable(Decimal("8.50"), Decimal("5")) == Decimal("5")


def test_resultado_valida_sus_campos():
    resultado = ResultadoReajuste(Decimal("1100"), Decimal("5"), Decimal("100"))
    assert resultado.canon_reajustado == Decimal("1100")
    with pytest.raises(ValorInvalido):
        ResultadoReajuste(Decimal("1050"), Decimal("5"), Decimal("50"))
    with pytest.raises(ValorInvalido):
        ResultadoReajuste(Decimal("1100"), Decimal("5.001"), Decimal("100"))
