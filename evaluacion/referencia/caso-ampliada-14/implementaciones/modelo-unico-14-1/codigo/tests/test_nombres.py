"""Pruebas de la convención y de sus únicas correcciones permitidas."""

from datetime import date

import pytest

from expedientes import evaluar_nombre


@pytest.mark.parametrize("tipo", ["ESC", "CER", "PAZ"])
def test_tipos_permitidos(tipo):
    resultado = evaluar_nombre(f"{tipo}_2019_00042.pdf", anio_actual=2026)
    assert resultado.correcto
    assert resultado.motivos == ()


def test_ejemplo_corregible():
    resultado = evaluar_nombre("esc-2019-42.PDF", anio_actual=2026)
    assert resultado.destino == "ESC_2019_00042.pdf"
    assert not resultado.correcto
    assert len(resultado.motivos) == 4


@pytest.mark.parametrize(
    ("nombre", "destino"),
    [
        ("esc_2019_00042.pdf", "ESC_2019_00042.pdf"),
        ("ESC-2019-00042.pdf", "ESC_2019_00042.pdf"),
        ("ESC_2019_42.pdf", "ESC_2019_00042.pdf"),
        ("ESC_2019_00042.PDF", "ESC_2019_00042.pdf"),
        ("cEr-2019_1.PdF", "CER_2019_00001.pdf"),
    ],
)
def test_correcciones_individuales_y_combinadas(nombre, destino):
    assert evaluar_nombre(nombre, anio_actual=2026).destino == destino


@pytest.mark.parametrize("anio", [1950, 2026])
def test_limites_inclusivos_del_anio(anio):
    assert evaluar_nombre(f"ESC_{anio}_00001.pdf", anio_actual=2026).correcto


def test_anio_actual_por_defecto():
    anio = date.today().year
    assert evaluar_nombre(f"ESC_{anio}_00001.pdf").correcto
    assert evaluar_nombre(f"ESC_{anio + 1}_00001.pdf").destino is None


@pytest.mark.parametrize(
    ("nombre", "motivo"),
    [
        ("XYZ_2019_00001.pdf", "Tipo desconocido"),
        ("ESC_1949_00001.pdf", "Año fuera de rango"),
        ("ESC_2027_00001.pdf", "Año fuera de rango"),
        ("ESC_2019_00001.jpg", "extensión"),
        ("ESC_2019_00001", "extensión"),
        ("ESC_2019_123456.pdf", "más de cinco"),
        ("ESC_2019_12A45.pdf", "Formato inválido"),
        ("ESC_2019.pdf", "Formato inválido"),
        ("ESC__00001.pdf", "Formato inválido"),
        ("ESC_2019_.pdf", "Formato inválido"),
        ("ESC_19_00001.pdf", "Formato inválido"),
        (" ESC_2019_00001.pdf", "Formato inválido"),
        ("ESC 2019 00001.pdf", "Formato inválido"),
        ("ESC_2019_１２３４５.pdf", "Formato inválido"),
    ],
)
def test_errores_sin_correccion(nombre, motivo):
    resultado = evaluar_nombre(nombre, anio_actual=2026)
    assert resultado.destino is None
    assert motivo in "; ".join(resultado.motivos)


def test_cero_admitido_por_decision_documentada():
    assert evaluar_nombre("ESC_2019_00000.pdf").correcto
    assert evaluar_nombre("ESC_2019_0.pdf").destino == "ESC_2019_00000.pdf"
