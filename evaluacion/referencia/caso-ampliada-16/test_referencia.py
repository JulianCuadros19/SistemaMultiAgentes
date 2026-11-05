"""Pruebas de aceptación de referencia del caso 16, amortización de créditos (ADR-0019).

Verifican solo lo que la ficha del caso dice sin ambigüedad, a través de la interfaz de
`interfaz.md`. Las mismas pruebas evalúan al sistema, al modelo único y a la implementación manual.
"""

import re
from decimal import Decimal

from adaptador_referencia import codigo_de_salida, cuota, guardar_tabla_csv, resumen, tabla
from referencia_comun import rechaza

MONTO, PLAZO, TASA = 100_000_000, 120, Decimal("12")
CUOTA = 1_399_472


def test_cuota_del_ejemplo():
    assert cuota(MONTO, PLAZO, TASA) == CUOTA


def test_primer_mes_del_ejemplo():
    assert tabla(MONTO, PLAZO, TASA)[0] == (CUOTA, 948_879, 450_593, 99_549_407)


def test_la_tabla_termina_en_cero_con_la_ultima_cuota_ajustada():
    filas = tabla(MONTO, PLAZO, TASA)
    assert len(filas) == PLAZO
    assert filas[-1][3] == 0
    assert {fila[0] for fila in filas[:-1]} == {CUOTA}


def test_el_resumen_cuadra_con_la_tabla():
    total_pagado, total_intereses = resumen(MONTO, PLAZO, TASA)
    assert total_pagado == sum(fila[0] for fila in tabla(MONTO, PLAZO, TASA))
    assert total_intereses == total_pagado - MONTO


def test_cuota_con_tasa_de_dos_decimales():
    assert cuota(25_000_000, 36, Decimal("9.75")) == 798_951


def test_rechaza_un_monto_fuera_de_rango():
    rechaza(cuota, 9_000_000, PLAZO, TASA)
    rechaza(cuota, 600_000_000, PLAZO, TASA)


def test_rechaza_un_plazo_fuera_de_rango():
    rechaza(cuota, MONTO, 6, TASA)
    rechaza(cuota, MONTO, 300, TASA)


def test_rechaza_una_tasa_fuera_de_rango():
    rechaza(cuota, MONTO, PLAZO, Decimal("0.5"))
    rechaza(cuota, MONTO, PLAZO, Decimal("35"))


def test_guarda_la_tabla_en_un_csv(tmp_path):
    ruta = tmp_path / "tabla.csv"
    guardar_tabla_csv(MONTO, PLAZO, TASA, str(ruta))
    lineas = [linea for linea in ruta.read_text(encoding="utf-8").splitlines() if linea.strip()]
    assert len(lineas) >= PLAZO
    cifras = [re.sub(r"[.,\s$]", "", linea) for linea in lineas]
    assert any("948879" in linea and "450593" in linea for linea in cifras)


def test_la_herramienta_termina_con_error_ante_datos_invalidos():
    assert codigo_de_salida("cuota", "100000000", "120", "12") == 0
    assert codigo_de_salida("cuota", "5000000", "120", "12") != 0
