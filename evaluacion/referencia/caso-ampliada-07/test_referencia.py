"""Pruebas de aceptación de referencia del caso 07, conciliación del recaudo (ADR-0019).

Verifican solo lo que la ficha del caso dice sin ambigüedad, a través de la interfaz de
`interfaz.md`. Las mismas pruebas evalúan al sistema y a las líneas base de un solo modelo.
"""

from adaptador_referencia import conciliar
from referencia_comun import rechaza

BANCO_A = "referencia;valor;fecha\nF-001;85000;2026-11-03\n"
BANCO_B = "REF,MONTO,FECHA_PAGO\nF-002,100000,03/11/2026\n"
BANCO_C = "referencia_factura,valor_pagado,fecha\nF-999,50000,2026/11/03\n"
FACTURAS = (
    "referencia,valor,vencimiento\n"
    "F-001,85000,2026-11-30\n"
    "F-002,120000,2026-11-30\n"
    "F-003,70000,2026-11-30\n"
)


def _rutas(carpeta, banco_a=BANCO_A, banco_b=BANCO_B, banco_c=BANCO_C, facturas=FACTURAS):
    entradas = carpeta / "entradas"
    entradas.mkdir()
    rutas = []
    for nombre, contenido in (
        ("banco_a.csv", banco_a),
        ("banco_b.csv", banco_b),
        ("banco_c.csv", banco_c),
        ("facturas.csv", facturas),
    ):
        ruta = entradas / nombre
        ruta.write_text(contenido, encoding="utf-8")
        rutas.append(str(ruta))
    salida = carpeta / "salida"
    salida.mkdir()
    return [*rutas, str(salida)]


def _por_referencia(carpeta, **archivos):
    filas, _ = conciliar(*_rutas(carpeta, **archivos))
    return {fila["referencia"]: fila for fila in filas}


def test_pago_igual_al_facturado_queda_conciliado(tmp_path):
    assert _por_referencia(tmp_path)["F-001"]["estado"] == "conciliado"


def test_pago_distinto_queda_con_diferencia(tmp_path):
    fila = _por_referencia(tmp_path)["F-002"]
    assert fila["estado"] == "diferencia"
    assert abs(int(fila["diferencia"])) == 20_000


def test_pago_sin_factura(tmp_path):
    assert _por_referencia(tmp_path)["F-999"]["estado"] == "pago sin factura"


def test_factura_sin_pago_queda_pendiente(tmp_path):
    assert _por_referencia(tmp_path)["F-003"]["estado"] == "pendiente"


def test_cada_pago_indica_su_banco(tmp_path):
    filas = _por_referencia(tmp_path)
    bancos = {ref: filas[ref]["banco"].strip().upper()[-1] for ref in ("F-001", "F-002", "F-999")}
    assert bancos == {"F-001": "A", "F-002": "B", "F-999": "C"}


def test_la_fila_trae_lo_facturado_y_lo_pagado(tmp_path):
    fila = _por_referencia(tmp_path)["F-002"]
    assert int(fila["valor_facturado"]) == 120_000
    assert int(fila["valor_pagado"]) == 100_000


def test_el_resumen_cuenta_cada_estado(tmp_path):
    _, resumen = conciliar(*_rutas(tmp_path))
    estados = {"conciliado", "diferencia", "pago sin factura", "pendiente"}
    assert {estado: resumen[estado] for estado in estados} == dict.fromkeys(estados, 1)


def test_rechaza_un_archivo_sin_una_columna(tmp_path):
    rutas = _rutas(tmp_path, banco_b="REF,FECHA_PAGO\nF-002,03/11/2026\n")
    rechaza(conciliar, *rutas, mensaje="MONTO")


def test_una_fila_con_valor_no_numerico_no_detiene_el_lote(tmp_path):
    filas = _por_referencia(tmp_path, banco_a=BANCO_A + "F-003;abc;2026-11-03\n")
    assert filas["F-001"]["estado"] == "conciliado"
    assert filas["F-002"]["estado"] == "diferencia"
