"""Casos sintéticos de elicitación: carga, identificadores y cobertura de arquitecturas."""

from collections import Counter
from pathlib import Path

import pytest

from multiagente.interfaces.cliente_simulado import RAIZ_EVALUACION, cargar_caso

CATALOGO = (
    Path(__file__).resolve().parents[2] / "knowledge_base" / "arquitecturas_referencia" / "catalogo"
)
ARQUITECTURAS = {archivo.name[:6] for archivo in CATALOGO.glob("ARQ-*.md")}
BASICOS = sorted((RAIZ_EVALUACION / "casos").glob("elicitacion-*.md"))
AMPLIADA = sorted((RAIZ_EVALUACION / "casos" / "ampliada").glob("elicitacion-*.md"))
CASOS_LIMITE = sorted((RAIZ_EVALUACION / "casos" / "casos-limite").glob("elicitacion-*.md"))


@pytest.mark.parametrize(
    "archivo", BASICOS + AMPLIADA + CASOS_LIMITE, ids=lambda archivo: archivo.stem
)
def test_cada_caso_carga_y_apunta_al_catalogo(archivo):
    caso = cargar_caso(archivo)
    assert set(caso.arquitecturas_esperadas) <= ARQUITECTURAS
    # El cliente simulado solo recibe lo que sabe la persona, no la arquitectura esperada.
    assert "ARQ-" not in caso.conocimiento


def test_la_corrida_ampliada_cubre_las_seis_arquitecturas():
    casos = [cargar_caso(archivo) for archivo in AMPLIADA]
    assert len(casos) == 20
    assert len({caso.id for caso in casos + [cargar_caso(a) for a in BASICOS]}) == 23
    assert all(len(caso.arquitecturas_esperadas) == 1 for caso in casos)
    objetivos = Counter(caso.arquitecturas_esperadas[0] for caso in casos)
    assert set(objetivos) == ARQUITECTURAS == {f"ARQ-0{n}" for n in range(1, 7)}
    assert min(objetivos.values()) >= 3


@pytest.mark.parametrize("archivo", CASOS_LIMITE, ids=lambda archivo: archivo.stem)
def test_los_casos_limite_traen_tres_reglas_que_el_cliente_solo_dice_si_le_preguntan(archivo):
    caso = cargar_caso(archivo)
    assert [regla.id for regla in caso.reglas_ocultas] == ["R1", "R2", "R3"]
    sabe, solo_si_preguntan = caso.conocimiento.split("## Lo que solo dices si te preguntan")
    for regla in caso.reglas_ocultas:
        # Los términos de cada regla están en lo que solo dice si le preguntan, y no antes.
        assert all(termino in solo_si_preguntan.lower() for termino in regla.terminos), regla.id
        assert not all(termino in sabe.lower() for termino in regla.terminos), regla.id
