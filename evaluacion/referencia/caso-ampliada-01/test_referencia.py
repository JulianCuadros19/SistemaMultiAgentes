"""Pruebas de aceptación de referencia del caso 01, comisiones de corretaje (ADR-0019).

Verifican solo lo que la ficha del caso dice sin ambigüedad, a través de la interfaz de
`interfaz.md`. Las mismas pruebas evalúan al sistema y a las líneas base de un solo modelo.
"""

from adaptador_referencia import liquidar
from referencia_comun import rechaza


def test_ejemplo_de_venta_con_un_asesor():
    assert liquidar("venta", 300_000_000, 1, "cerrado") == (9_000_000, 3_600_000)


def test_ejemplo_de_arriendo_con_dos_asesores():
    assert liquidar("arriendo", 1_000_000, 2, "cerrado") == (1_000_000, 300_000)


def test_dos_asesores_reparten_el_cuarenta_por_ciento():
    assert liquidar("venta", 300_000_000, 2, "cerrado") == (9_000_000, 1_800_000)


def test_arriendo_con_un_asesor():
    assert liquidar("arriendo", 2_000_000, 1, "cerrado") == (2_000_000, 800_000)


def test_el_minimo_aplica_a_un_asesor():
    assert liquidar("arriendo", 500_000, 1, "cerrado") == (500_000, 300_000)


def test_redondea_al_peso_mas_cercano():
    assert liquidar("venta", 100_000_020, 1, "cerrado") == (3_000_001, 1_200_000)


def test_rechaza_un_negocio_no_cerrado():
    rechaza(liquidar, "venta", 300_000_000, 1, "abierto", mensaje="El negocio aún no está cerrado")


def test_rechaza_un_valor_no_positivo():
    rechaza(liquidar, "venta", 0, 1, "cerrado")
    rechaza(liquidar, "arriendo", -1_000_000, 1, "cerrado")


def test_rechaza_mas_de_dos_asesores():
    rechaza(liquidar, "venta", 300_000_000, 3, "cerrado")
