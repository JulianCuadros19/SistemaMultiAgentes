from datetime import date
from decimal import Decimal

import pytest

from aplicacion.calculo_avaluo import calcular_avaluo
from dominio.avaluo import (
    AreaConstruidaInvalida,
    AreaTerrenoInvalida,
    NumeroPredialInvalido,
    Predio,
    ResultadoAvaluo,
    ValoresUnitarios,
    ValoresUnitariosNoEncontrados,
    VigenciaInvalida,
)
from infraestructura import valores_unitarios_repositorio as repositorio

NUMERO = "1" * 30
ANIO = date.today().year


@pytest.fixture
def valores(monkeypatch):
    registros = {(NUMERO, ANIO): ValoresUnitarios(Decimal("500000"), Decimal("1200000"))}
    monkeypatch.setattr(repositorio, "_VALORES_UNITARIOS", registros)
    return registros


def test_rf_01_esc_01_predio_con_construccion(valores):
    resultado = calcular_avaluo(NUMERO, ANIO, Decimal("200"), Decimal("100"))
    assert resultado == ResultadoAvaluo(
        Decimal("100000000"), Decimal("120000000"), Decimal("220000000")
    )
    assert resultado.avaluo_total.as_tuple().exponent == 0


def test_rf_01_esc_02_predio_sin_construccion(valores):
    resultado = calcular_avaluo(NUMERO, ANIO, Decimal("200"), Decimal("0"))
    assert resultado.avaluo_construccion == Decimal("0")
    assert resultado.avaluo_total == resultado.avaluo_terreno


def test_rf_01_esc_03_terreno_cero(valores):
    with pytest.raises(AreaTerrenoInvalida, match="mayor que cero"):
        calcular_avaluo(NUMERO, ANIO, Decimal("0"), Decimal("100"))


@pytest.mark.parametrize("numero", ["1" * 29, "1" * 31, "a" * 30, "", None])
def test_numero_invalido(numero):
    with pytest.raises(NumeroPredialInvalido):
        Predio(numero, Decimal("1"), Decimal("0"))


@pytest.mark.parametrize("area", [Decimal("-1"), Decimal("NaN"), Decimal("Infinity"), 1.0])
def test_terreno_invalido(area):
    with pytest.raises(AreaTerrenoInvalida):
        Predio(NUMERO, area, Decimal("0"))


@pytest.mark.parametrize("area", [Decimal("-0.01"), Decimal("NaN"), Decimal("Infinity"), None])
def test_construccion_invalida(area):
    with pytest.raises(AreaConstruidaInvalida):
        Predio(NUMERO, Decimal("1"), area)


@pytest.mark.parametrize("vigencia", [999, 10000, ANIO + 2, True, "2026"])
def test_vigencia_invalida(vigencia):
    with pytest.raises(VigenciaInvalida):
        calcular_avaluo(NUMERO, vigencia, Decimal("1"), Decimal("0"))


@pytest.mark.parametrize("vigencia", [1000, ANIO + 1])
def test_limites_vigencia(valores, vigencia):
    valores[(NUMERO, vigencia)] = ValoresUnitarios(Decimal("1"), Decimal("0"))
    assert calcular_avaluo(NUMERO, vigencia, Decimal("1"), Decimal("0")).avaluo_total == 1


def test_sin_valores(monkeypatch):
    monkeypatch.setattr(repositorio, "_VALORES_UNITARIOS", {})
    with pytest.raises(ValoresUnitariosNoEncontrados):
        repositorio.obtener_valores_unitarios(NUMERO, ANIO)


def test_repositorio_numero_invalido():
    with pytest.raises(NumeroPredialInvalido):
        repositorio.obtener_valores_unitarios("1", ANIO)


def test_redondeo_y_area_positiva_minima(valores):
    valores[(NUMERO, ANIO)] = ValoresUnitarios(Decimal("50"), Decimal("0.5"))
    resultado = calcular_avaluo(NUMERO, ANIO, Decimal("0.01"), Decimal("1"))
    assert resultado == ResultadoAvaluo(Decimal("1"), Decimal("1"), Decimal("2"))


@pytest.mark.parametrize(
    ("terreno", "construccion"),
    [(Decimal("0"), Decimal("0")), (Decimal("1"), Decimal("-1")),
     (Decimal("NaN"), Decimal("0")), (1, Decimal("0"))],
)
def test_valores_unitarios_invalidos(terreno, construccion):
    with pytest.raises(ValueError):
        ValoresUnitarios(terreno, construccion)


@pytest.mark.parametrize("importe", [Decimal("-1"), Decimal("0.1"), Decimal("NaN"), 1])
def test_resultado_invalido(importe):
    with pytest.raises(ValueError):
        ResultadoAvaluo(importe, Decimal("0"), Decimal("0"))
