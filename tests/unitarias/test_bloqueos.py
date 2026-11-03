"""Bloqueos de sesión en memoria: una corrida a la vez por sesión (ADR-0014)."""

import pytest

from multiagente.persistencia.bloqueos import BloqueosEnMemoria, SesionOcupada, clave


def test_la_clave_es_estable_y_cabe_en_31_bits():
    sesion = "5f5d2739-427b-4c2a-b549-6bd0c6b249e2"
    assert clave(sesion) == clave(sesion)
    assert 0 <= clave(sesion) < 2**31
    assert clave(sesion) != clave("61e1e121-f297-41bb-b7e1-43b7bf5d51ba")


def test_una_sesion_tomada_no_se_vuelve_a_tomar_hasta_soltarla():
    bloqueos = BloqueosEnMemoria()
    with bloqueos.exclusivo("s1"):
        assert bloqueos.ocupadas() == {clave("s1")}
        with pytest.raises(SesionOcupada, match="s1"), bloqueos.exclusivo("s1"):
            pass
        with bloqueos.exclusivo("s2"):
            assert bloqueos.ocupadas() == {clave("s1"), clave("s2")}
    assert bloqueos.ocupadas() == set()


def test_un_error_dentro_del_bloque_suelta_la_sesion():
    bloqueos = BloqueosEnMemoria()
    with pytest.raises(ValueError, match="falla del nodo"), bloqueos.exclusivo("s1"):
        raise ValueError("falla del nodo")
    assert bloqueos.ocupadas() == set()
