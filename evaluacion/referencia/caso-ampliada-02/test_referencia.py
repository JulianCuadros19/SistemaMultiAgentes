"""Pruebas de aceptación de referencia del caso 02, reajuste anual del canon (ADR-0019).

Verifican solo lo que la ficha del caso dice sin ambigüedad, a través de la interfaz de
`interfaz.md`. Las mismas pruebas evalúan al sistema, al modelo único y a la implementación manual.
"""

from datetime import date
from decimal import Decimal

from adaptador_referencia import reajustar
from referencia_comun import rechaza

INICIO = date(2025, 3, 1)
UN_ANIO_DESPUES = date(2026, 3, 1)


def test_ejemplo_con_ipc_menor_que_lo_pactado():
    nuevo, aplicado, incremento = reajustar(
        1_200_000, Decimal("10"), Decimal("5.20"), INICIO, UN_ANIO_DESPUES
    )
    assert (nuevo, aplicado, incremento) == (1_262_400, Decimal("5.20"), 62_400)


def test_ejemplo_con_pactado_menor_que_el_ipc():
    nuevo, aplicado, incremento = reajustar(
        950_000, Decimal("3"), Decimal("5.20"), INICIO, UN_ANIO_DESPUES
    )
    assert (nuevo, aplicado, incremento) == (978_500, Decimal("3"), 28_500)


def test_redondea_a_la_centena_mas_cercana():
    # 1.111.111 × 1,0111 = 1.123.444,33 y 987.654 × 1,045 = 1.032.098,43.
    nuevo, _, _ = reajustar(1_111_111, Decimal("5"), Decimal("1.11"), INICIO, UN_ANIO_DESPUES)
    assert nuevo == 1_123_400
    nuevo, _, _ = reajustar(987_654, Decimal("4.5"), Decimal("6"), INICIO, UN_ANIO_DESPUES)
    assert nuevo == 1_032_100


def test_ipc_cero_no_cambia_el_canon():
    nuevo, _, _ = reajustar(1_000_000, Decimal("5"), Decimal("0"), INICIO, UN_ANIO_DESPUES)
    assert nuevo == 1_000_000


def test_ipc_negativo_no_cambia_el_canon():
    nuevo, _, _ = reajustar(1_000_000, Decimal("5"), Decimal("-1.5"), INICIO, UN_ANIO_DESPUES)
    assert nuevo == 1_000_000


def test_rechaza_antes_de_doce_meses():
    rechaza(
        reajustar,
        1_200_000,
        Decimal("10"),
        Decimal("5.20"),
        date(2025, 6, 1),
        date(2026, 3, 1),
        mensaje="El contrato aún no cumple doce meses desde el último reajuste",
    )


def test_reajusta_al_cumplir_doce_meses():
    nuevo, _, _ = reajustar(1_200_000, Decimal("10"), Decimal("5.20"), INICIO, UN_ANIO_DESPUES)
    assert nuevo == 1_262_400


def test_rechaza_un_canon_no_positivo():
    rechaza(reajustar, 0, Decimal("10"), Decimal("5.20"), INICIO, UN_ANIO_DESPUES)


def test_rechaza_un_porcentaje_pactado_fuera_de_rango():
    rechaza(reajustar, 1_200_000, Decimal("101"), Decimal("5.20"), INICIO, UN_ANIO_DESPUES)
