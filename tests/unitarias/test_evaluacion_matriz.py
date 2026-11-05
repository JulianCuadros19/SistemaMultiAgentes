"""Matriz de confusión del tester frente al oráculo (paso 15, ADR-0019), sin Docker ni costo."""

import pytest

from multiagente.evaluacion.matriz import (
    MatrizConfusion,
    ReporteSinVeredicto,
    VersionEvaluada,
    matriz_de_versiones,
    rechazada_por_el_tester,
)


def _version(rechazada: bool, pasan: int, total: int = 10) -> VersionEvaluada:
    return VersionEvaluada("caso", "sistema", 1, rechazada, pasan, total)


def test_lee_el_veredicto_del_reporte():
    assert rechazada_por_el_tester("# Reporte\n\n**Veredicto: RECHAZADO** · 4 de 5 casos")
    assert not rechazada_por_el_tester("# Reporte\n\n**Veredicto: APROBADO** · 5 de 5 casos")


def test_un_reporte_sin_veredicto_no_se_interpreta():
    with pytest.raises(ReporteSinVeredicto):
        rechazada_por_el_tester("# Reporte sin dictamen")


def test_cada_version_cae_en_su_celda():
    matriz = matriz_de_versiones(
        [
            _version(True, 8),
            _version(True, 10),
            _version(False, 9),
            _version(False, 10),
            _version(False, 10),
        ]
    )
    assert matriz == MatrizConfusion(
        verdaderos_positivos=1,
        falsos_positivos=1,
        falsos_negativos=1,
        verdaderos_negativos=2,
    )
    assert matriz.total == 5


def test_las_metricas_siguen_la_tabla_13_de_la_tesis():
    matriz = MatrizConfusion(6, 2, 2, 10)
    assert matriz.exactitud == pytest.approx(16 / 20)
    assert matriz.precision == pytest.approx(0.75)
    assert matriz.sensibilidad == pytest.approx(0.75)
    assert matriz.f1 == pytest.approx(0.75)


def test_una_metrica_sin_denominador_no_se_calcula():
    matriz = MatrizConfusion(0, 0, 0, 4)
    assert matriz.exactitud == 1.0
    assert matriz.precision is None
    assert matriz.sensibilidad is None
    assert matriz.f1 is None
