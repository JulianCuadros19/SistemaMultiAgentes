"""Pruebas de tarifas, validaciones y aritmética monetaria."""

import pytest

from predial import ErrorConsulta, calcular_impuesto, consultar_tarifa


@pytest.mark.parametrize(
    ("estrato", "esperada"),
    [(1, 5), (2, 6), (3, 8), (4, 10), (5, 12), (6, 14)],
)
def test_tarifas_residenciales(estrato: int, esperada: int) -> None:
    assert consultar_tarifa("residencial", estrato) == esperada


@pytest.mark.parametrize(
    ("destino", "esperada"),
    [("comercial", 11), ("industrial", 12), ("lote urbanizable no edificado", 33)],
)
def test_tarifas_no_residenciales(destino: str, esperada: int) -> None:
    assert consultar_tarifa(destino) == esperada


@pytest.mark.parametrize(
    "destino", ["comercial", "industrial", "lote urbanizable no edificado"],
)
@pytest.mark.parametrize("estrato", [None, 0, 1, 6, 7, -10])
def test_estrato_solo_aplica_a_residencial(destino: str, estrato: int | None) -> None:
    assert consultar_tarifa(destino, estrato) == consultar_tarifa(destino)
    assert calcular_impuesto(1000, destino, estrato) == consultar_tarifa(destino)


@pytest.mark.parametrize("estrato", [-1, 0, 7, 100, None])
def test_estrato_residencial_invalido(estrato: int | None) -> None:
    with pytest.raises(ErrorConsulta, match="^Estrato inválido$"):
        consultar_tarifa("residencial", estrato)
    with pytest.raises(ErrorConsulta, match="^Estrato inválido$"):
        calcular_impuesto(1000, "residencial", estrato)


@pytest.mark.parametrize("destino", ["desconocido", "", "Residencial", " residencial"])
def test_destino_desconocido(destino: str) -> None:
    with pytest.raises(ErrorConsulta, match="^Destino económico no reconocido$"):
        consultar_tarifa(destino, 3)
    with pytest.raises(ErrorConsulta, match="^Destino económico no reconocido$"):
        calcular_impuesto(1000, destino, 3)


@pytest.mark.parametrize("avaluo", [0, -1, -120_000_000])
def test_avaluo_no_positivo(avaluo: int) -> None:
    with pytest.raises(ErrorConsulta, match="^El avalúo debe ser mayor que cero$"):
        calcular_impuesto(avaluo, "residencial", 3)


def test_ejemplo_del_cliente() -> None:
    assert consultar_tarifa("residencial", 3) == 8
    assert calcular_impuesto(120_000_000, "residencial", 3) == 960_000


@pytest.mark.parametrize(
    ("avaluo", "esperado"),
    [(1, 0), (49, 0), (50, 1), (51, 1), (149, 1), (150, 2), (151, 2)],
)
def test_redondeo_al_peso_mitades_arriba(avaluo: int, esperado: int) -> None:
    resultado = calcular_impuesto(avaluo, "residencial", 4)
    assert resultado == esperado
    assert type(resultado) is int


@pytest.mark.parametrize(
    ("destino", "estrato", "tarifa"),
    [
        ("residencial", 1, 5),
        ("residencial", 2, 6),
        ("residencial", 3, 8),
        ("residencial", 4, 10),
        ("residencial", 5, 12),
        ("residencial", 6, 14),
        ("comercial", None, 11),
        ("industrial", None, 12),
        ("lote urbanizable no edificado", None, 33),
    ],
)
def test_formula_para_cada_tarifa(destino: str, estrato: int | None, tarifa: int) -> None:
    assert calcular_impuesto(1_000_000, destino, estrato) == 1000 * tarifa


def test_importe_grande_sin_perdida_de_precision() -> None:
    assert calcular_impuesto(10**50 + 50, "residencial", 4) == 10**48 + 1


def test_booleano_no_es_avaluo_entero() -> None:
    with pytest.raises(ErrorConsulta, match="^El avalúo debe ser un entero en pesos$"):
        calcular_impuesto(True, "comercial")


def test_booleano_no_es_estrato() -> None:
    with pytest.raises(ErrorConsulta, match="^Estrato inválido$"):
        consultar_tarifa("residencial", True)
