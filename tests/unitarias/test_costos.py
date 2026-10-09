"""Pruebas del cálculo de costo: Decimal, caché y razonamiento sin doble cobro."""

from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from multiagente.llm.costos import (
    ConsumoTokens,
    ErrorTarifaNoEncontrada,
    Tarifa,
    buscar_tarifa,
    calcular_costo,
    cargar_tarifas,
)

RAIZ = Path(__file__).resolve().parents[2]
TARIFA_NANO = Tarifa(
    entrada=Decimal("0.05"), entrada_cacheada=Decimal("0.005"), salida=Decimal("0.40")
)


def test_costo_sin_cache():
    consumo = ConsumoTokens(entrada=1_000_000, salida=1_000_000)
    assert calcular_costo(consumo, TARIFA_NANO) == Decimal("0.45")


def test_costo_con_entrada_cacheada():
    consumo = ConsumoTokens(entrada=1_000_000, entrada_cacheada=400_000, salida=0)
    # 600.000 a 0,05 y 400.000 a 0,005
    assert calcular_costo(consumo, TARIFA_NANO) == Decimal("0.032")


def test_razonamiento_no_se_cobra_dos_veces():
    con_razonamiento = ConsumoTokens(entrada=20, salida=4_700, razonamiento=4_500)
    sin_desglose = ConsumoTokens(entrada=20, salida=4_700)
    assert calcular_costo(con_razonamiento, TARIFA_NANO) == calcular_costo(
        sin_desglose, TARIFA_NANO
    )
    assert con_razonamiento.salida_visible == 200


def test_costo_es_decimal_exacto():
    costo = calcular_costo(ConsumoTokens(entrada=3, salida=7), TARIFA_NANO)
    assert isinstance(costo, Decimal)
    assert costo == Decimal("0.00000295")


@pytest.mark.parametrize(
    "campos",
    [
        {"entrada": 10, "entrada_cacheada": 11, "salida": 0},
        {"entrada": 0, "salida": 10, "razonamiento": 11},
        {"entrada": -1, "salida": 0},
    ],
)
def test_consumo_rechaza_desgloses_imposibles(campos):
    with pytest.raises(ValidationError):
        ConsumoTokens(**campos)


def test_buscar_tarifa_por_prefijo_mas_largo():
    tarifas = {"gpt-5": Tarifa(entrada=1, entrada_cacheada=1, salida=1), "gpt-5-nano": TARIFA_NANO}
    assert buscar_tarifa(tarifas, "gpt-5-nano-2025-08-07") == TARIFA_NANO


def test_buscar_tarifa_de_modelo_desconocido():
    with pytest.raises(ErrorTarifaNoEncontrada):
        buscar_tarifa({"gpt-5-nano": TARIFA_NANO}, "otro-modelo")


def test_archivo_de_tarifas_versionado():
    tarifas = cargar_tarifas(RAIZ / "config" / "tarifas_modelos.toml")
    assert tarifas["gpt-5-nano"] == TARIFA_NANO


@pytest.mark.parametrize(
    ("modelo", "salida"),
    [
        ("gpt-5-nano-2025-08-07", "0.40"),
        ("gpt-5-mini-2025-08-07", "2.00"),
        # Un nombre con punto exige la clave entre comillas en TOML; sin ellas se anida.
        ("gpt-5.4-mini-2026-03-17", "4.50"),
    ],
)
def test_cada_modelo_resuelve_su_tarifa(modelo, salida):
    tarifas = cargar_tarifas(RAIZ / "config" / "tarifas_modelos.toml")
    assert buscar_tarifa(tarifas, modelo).salida == Decimal(salida)
