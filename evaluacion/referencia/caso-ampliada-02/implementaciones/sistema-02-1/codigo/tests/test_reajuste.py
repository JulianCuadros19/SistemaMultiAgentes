"""Pruebas del recorrido público del reajuste anual."""

from datetime import date, datetime
from decimal import Decimal

import pytest

from aplicacion.reajuste import realizar_reajuste
from dominio.reajuste import MesesInsuficientesError, ReajusteResultado, calcular_reajuste


def test_rf_01_esc_01_ipc_menor_al_pactado():
    resultado = realizar_reajuste(
        Decimal("1200000"), Decimal("10"), Decimal("5.20"),
        date(2023, 6, 15), date(2024, 6, 15),
    )
    assert resultado == ReajusteResultado(
        Decimal("1262400"), Decimal("5.20"), Decimal("62400"),
    )


def test_rf_01_esc_02_porcentaje_pactado_como_tope():
    resultado = realizar_reajuste(
        Decimal("950000"), Decimal("3"), Decimal("5.20"),
        date(2023, 6, 15), date(2025, 6, 15),
    )
    assert resultado == ReajusteResultado(
        Decimal("978500"), Decimal("3"), Decimal("28500"),
    )


@pytest.mark.parametrize("ipc", ["0", "-0.01", "-5.20"])
def test_rf_01_esc_03_ipc_no_positivo(ipc):
    resultado = realizar_reajuste(
        Decimal("850000"), Decimal("8"), Decimal(ipc),
        date(2023, 6, 15), date(2024, 6, 15),
    )
    assert resultado == ReajusteResultado(Decimal("850000"), Decimal(0), Decimal(0))


@pytest.mark.xfail(
    strict=True,
    reason="ESC-04 exige 1234600, pero la fórmula de diseño produce 1298800",
)
def test_rf_01_esc_04_redondeo_a_centena():
    resultado = realizar_reajuste(
        Decimal("1234567"), Decimal("10"), Decimal("5.20"),
        date(2023, 6, 15), date(2024, 6, 15),
    )
    assert resultado.nuevo_canon == Decimal("1234600")


@pytest.mark.parametrize("fecha", [date(2024, 6, 14), date(2023, 6, 14)])
def test_rf_01_esc_05_plazo_insuficiente(fecha):
    with pytest.raises(MesesInsuficientesError) as error:
        realizar_reajuste(
            Decimal("1200000"), Decimal("10"), Decimal("5.20"),
            date(2023, 6, 15), fecha,
        )
    assert str(error.value) == "El contrato aún no cumple doce meses desde el último reajuste"


@pytest.mark.parametrize(
    ("canon", "pactado", "ipc"),
    [
        (Decimal("0"), Decimal("10"), Decimal("5.20")),
        (Decimal("-0.01"), Decimal("10"), Decimal("5.20")),
        (Decimal("NaN"), Decimal("10"), Decimal("5.20")),
        (Decimal("Infinity"), Decimal("10"), Decimal("5.20")),
        (Decimal("1000"), Decimal("-0.01"), Decimal("5.20")),
        (Decimal("1000"), Decimal("100.01"), Decimal("5.20")),
        (Decimal("1000"), Decimal("1.001"), Decimal("5.20")),
        (Decimal("1000"), Decimal("10"), Decimal("0.001")),
        (Decimal("1000"), Decimal("10"), Decimal("-0.001")),
        (Decimal("1000"), Decimal("NaN"), Decimal("5.20")),
        (Decimal("1000"), Decimal("10"), Decimal("Infinity")),
        (1000, Decimal("10"), Decimal("5.20")),
    ],
)
def test_entradas_numericas_invalidas(canon, pactado, ipc):
    with pytest.raises(MesesInsuficientesError):
        realizar_reajuste(canon, pactado, ipc, date(2023, 1, 1), date(2024, 1, 1))


@pytest.mark.parametrize(
    ("inicio", "fin"),
    [
        (None, date(2024, 1, 1)),
        (date(2023, 1, 1), None),
        (datetime(2023, 1, 1), date(2024, 1, 1)),
    ],
)
def test_fechas_invalidas(inicio, fin):
    with pytest.raises(MesesInsuficientesError):
        realizar_reajuste(Decimal("1000"), Decimal("10"), Decimal("5"), inicio, fin)


@pytest.mark.parametrize(
    ("pactado", "ipc", "esperado"),
    [("0", "5", "1000"), ("100", "100", "2000"), ("5.20", "5.20", "1100")],
)
def test_limites_y_porcentajes_iguales(pactado, ipc, esperado):
    resultado = realizar_reajuste(
        Decimal("1000"), Decimal(pactado), Decimal(ipc),
        date(2023, 1, 1), date(2024, 1, 1),
    )
    assert resultado.nuevo_canon == Decimal(esperado)
    assert resultado.porcentaje_aplicado == Decimal(pactado)


@pytest.mark.parametrize(
    ("canon", "esperado"),
    [("1049", "1000"), ("1050", "1100"), ("1051", "1100"), ("0.01", "0")],
)
def test_redondeo_a_centena_y_canon_minimo(canon, esperado):
    resultado = realizar_reajuste(
        Decimal(canon), Decimal("0"), Decimal("5"),
        date(2023, 1, 1), date(2024, 1, 1),
    )
    assert resultado.nuevo_canon == Decimal(esperado)
    assert resultado.valor_del_incremento == Decimal(esperado) - Decimal(canon)


def test_ipc_no_positivo_conserva_canon_sin_redondear():
    resultado = realizar_reajuste(
        Decimal("1234567.89"), Decimal("8"), Decimal("0"),
        date(2023, 1, 1), date(2024, 1, 1),
    )
    assert resultado.nuevo_canon == Decimal("1234567.89")
    assert resultado.valor_del_incremento == Decimal(0)


def test_aniversario_de_fecha_bisiesta():
    resultado = realizar_reajuste(
        Decimal("1000"), Decimal("10"), Decimal("5"),
        date(2024, 2, 29), date(2025, 2, 28),
    )
    assert resultado.nuevo_canon == Decimal("1100")


def test_ultimo_ano_representable_no_cumple_plazo():
    with pytest.raises(MesesInsuficientesError):
        realizar_reajuste(
            Decimal("1000"), Decimal("10"), Decimal("5"), date.max, date.max,
        )


def test_dominio_calcula_directamente_y_admite_ceros_finales():
    resultado = calcular_reajuste(
        Decimal("1200000"), Decimal("10.000"), Decimal("5.200"),
        date(2023, 1, 1), date(2024, 1, 1),
    )
    assert resultado == ReajusteResultado(
        Decimal("1262400"), Decimal("5.20"), Decimal("62400"),
    )
