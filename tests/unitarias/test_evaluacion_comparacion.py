"""Comparación de los enfoques del objetivo 4 (ADR-0019), sin Docker ni costo."""

from decimal import Decimal

import pytest

from multiagente.evaluacion.comparacion import (
    Medicion,
    agrupar,
    costo_total,
    minutos_de_tiempos,
    resumir,
)


def _medicion(caso: str, enfoque: str, costo: str, pasan: int, horas: str = "0") -> Medicion:
    return Medicion(
        caso, enfoque, f"{enfoque}-{caso}", Decimal(5), Decimal(horas), Decimal(costo), pasan, 10
    )


def test_los_minutos_salen_de_la_columna_o_de_las_horas_sin_contar_las_pausas():
    texto = (
        "fase,inicio,fin,minutos,notas\n"
        "analisis,2026-11-05 14:00,2026-11-05 14:10,,\n"
        "codigo,2026-11-05 14:30,2026-11-05 15:15,,con una pausa antes\n"
        "pruebas,,,20,anotado a mano\n"
    )
    assert minutos_de_tiempos(texto) == Decimal(75)


def test_una_fila_sin_minutos_ni_horas_no_se_cuenta_en_silencio():
    with pytest.raises(ValueError):
        minutos_de_tiempos("fase,inicio,fin,minutos,notas\ncodigo,,,,\n")


def test_el_costo_es_la_inferencia_mas_las_horas_por_la_tarifa():
    assert costo_total(Decimal("0.37"), Decimal("0.5"), Decimal(9)) == Decimal("4.87")


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
            _medicion("a", "manual", "0", 10, "2"),
        ]
    )
    assert [(r.caso, r.enfoque, r.corridas) for r in resumenes] == [
        ("a", "manual", 1),
        ("a", "sistema", 1),
        ("b", "sistema", 1),
        ("todos", "manual", 1),
        ("todos", "sistema", 2),
    ]
