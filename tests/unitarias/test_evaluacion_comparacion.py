"""Comparación de los enfoques del objetivo 4 (ADR-0019), sin Docker ni costo."""

from decimal import Decimal

import pytest

from multiagente.evaluacion.comparacion import (
    Medicion,
    agrupar,
    comparar_por_caso,
    prueba_de_signos,
    resumir,
)


def _medicion(caso: str, enfoque: str, costo: str, pasan: int) -> Medicion:
    return Medicion(caso, enfoque, f"{enfoque}-{caso}", Decimal(5), Decimal(costo), pasan, 10)


def test_resumir_promedia_el_costo_y_suma_las_verificaciones():
    resumen = resumir(
        "caso",
        "sistema",
        [_medicion("caso", "sistema", "0.2", 10), _medicion("caso", "sistema", "0.4", 8)],
    )
    assert resumen.inferencia_usd == Decimal("0.3")
    assert (resumen.pasan, resumen.total) == (18, 20)
    assert resumen.tasa_errores == Decimal("0.1")


def test_resumir_exige_mediciones():
    with pytest.raises(ValueError):
        resumir("caso", "sistema", [])


def test_agrupar_da_cada_caso_y_el_total_de_cada_enfoque():
    resumenes = agrupar(
        [
            _medicion("a", "sistema", "0.2", 10),
            _medicion("b", "sistema", "0.4", 10),
            _medicion("a", "un_prompt", "0.1", 10),
        ]
    )
    assert [(r.caso, r.enfoque, r.corridas) for r in resumenes] == [
        ("a", "sistema", 1),
        ("a", "un_prompt", 1),
        ("b", "sistema", 1),
        ("todos", "sistema", 2),
        ("todos", "un_prompt", 1),
    ]


@pytest.mark.parametrize(
    ("mayor", "menor", "esperado"),
    [(9, 0, 2 / 512), (5, 4, 1.0), (8, 1, 20 / 512), (0, 0, 1.0)],
)
def test_prueba_de_signos(mayor, menor, esperado):
    assert prueba_de_signos(mayor, menor) == pytest.approx(esperado)


def test_comparar_por_caso_solo_cuenta_los_casos_comunes_y_aparta_los_empates():
    comparacion = comparar_por_caso(
        {"a": Decimal(2), "b": Decimal(1), "c": Decimal(3), "solo-uno": Decimal(9)},
        {"a": Decimal(1), "b": Decimal(1), "c": Decimal(4)},
    )
    assert (comparacion.mayor, comparacion.menor, comparacion.empates) == (1, 1, 1)
    assert comparacion.valor_p == 1.0
