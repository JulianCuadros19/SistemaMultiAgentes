"""Casos sintéticos de elicitación que usa el cliente simulado en el flujo de extremo a extremo."""

import pytest

from multiagente.interfaces.cliente_simulado import RAIZ_EVALUACION, cargar_caso

CASOS = sorted((RAIZ_EVALUACION / "casos").glob("elicitacion-*.md"))


@pytest.mark.parametrize("archivo", CASOS, ids=[caso.stem for caso in CASOS])
def test_cada_caso_carga_con_su_cabecera_y_lo_que_sabe_el_cliente(archivo):
    caso = cargar_caso(archivo)
    assert "## Lo que sabes" in caso.conocimiento
    assert "## Lo que no sabes" in caso.conocimiento


def test_los_casos_tienen_identificadores_unicos():
    identificadores = [cargar_caso(archivo).id for archivo in CASOS]
    assert len(identificadores) >= 3
    assert len(set(identificadores)) == len(identificadores)
