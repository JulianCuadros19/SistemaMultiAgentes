"""Pruebas de aceptación de referencia del caso 10, tarifa del impuesto predial (ADR-0019).

Verifican solo lo que la ficha del caso dice sin ambigüedad, a través de la interfaz de
`interfaz.md`. Las mismas pruebas evalúan al sistema y a las líneas base de un solo modelo.
"""

from adaptador_referencia import calcular_impuesto, consultar_tarifa
from referencia_comun import rechaza


def test_tarifa_del_ejemplo():
    assert consultar_tarifa("residencial", 3) == 8


def test_impuesto_del_ejemplo():
    assert calcular_impuesto(120_000_000, "residencial", 3) == 960_000


def test_tarifas_residenciales_por_estrato():
    tarifas = {estrato: consultar_tarifa("residencial", estrato) for estrato in range(1, 7)}
    assert tarifas == {1: 5, 2: 6, 3: 8, 4: 10, 5: 12, 6: 14}


def test_tarifas_de_los_demas_destinos():
    assert consultar_tarifa("comercial", None) == 11
    assert consultar_tarifa("industrial", None) == 12
    assert consultar_tarifa("lote", None) == 33


def test_impuesto_de_un_destino_sin_estrato():
    assert calcular_impuesto(10_000_000, "comercial", None) == 110_000


def test_la_mitad_se_redondea_hacia_arriba():
    assert calcular_impuesto(100_100, "residencial", 1) == 501


def test_menos_de_la_mitad_se_redondea_hacia_abajo():
    assert calcular_impuesto(100_050, "residencial", 3) == 800


def test_rechaza_un_estrato_invalido():
    rechaza(consultar_tarifa, "residencial", 7, mensaje="Estrato inválido")
    rechaza(calcular_impuesto, 120_000_000, "residencial", 0, mensaje="Estrato inválido")


def test_rechaza_un_destino_desconocido():
    rechaza(consultar_tarifa, "minero", None, mensaje="Destino económico no reconocido")


def test_rechaza_un_avaluo_no_positivo():
    rechaza(
        calcular_impuesto, 0, "comercial", None, mensaje="El avalúo debe ser mayor que cero"
    )
    rechaza(
        calcular_impuesto, -1, "comercial", None, mensaje="El avalúo debe ser mayor que cero"
    )
