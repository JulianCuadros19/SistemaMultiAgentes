"""Pruebas de la fusión por rango recíproco de la recuperación híbrida (RF-31)."""

import pytest

from multiagente.rag.recuperacion import K_FUSION, fusionar


def test_fusion_por_rango_reciproco():
    puntajes = fusionar({1: 1, 2: 2, 3: 3}, {3: 1, 4: 2}, k=60)
    assert puntajes[3] == pytest.approx(1 / 63 + 1 / 61)
    assert max(puntajes, key=puntajes.get) == 3
    assert puntajes[4] == pytest.approx(1 / 62)


def test_coincidir_en_ambas_busquedas_supera_a_liderar_una_sola():
    puntajes = fusionar({"a": 1, "b": 5}, {"b": 5})
    assert puntajes["b"] > puntajes["a"]
    assert K_FUSION == 60
