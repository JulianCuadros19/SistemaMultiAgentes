"""Pruebas de reglas, decisiones mínimas, errores y reintentos."""

import csv
import json
from pathlib import Path

import pytest

from conciliacion import Entrada, ErrorEtapa, Lote

_CABECERAS = {
    "A": "referencia;valor;fecha\n",
    "B": "REF,MONTO,FECHA_PAGO\n",
    "C": "referencia_factura,valor_pagado,fecha\n",
    "facturas": "referencia,valor,vencimiento\n",
}


def _lote(tmp_path, contenidos=None):
    contenidos = contenidos or {}
    entradas = []
    for origen, cabecera in _CABECERAS.items():
        ruta = tmp_path / f"{origen}.csv"
        ruta.write_text(contenidos.get(origen, cabecera), encoding="utf-8")
        entradas.append(Entrada(origen, ruta))
    return Lote(entradas, tmp_path / "salida")


@pytest.mark.parametrize(
    ("origen", "pago"),
    [
        ("A", "F1;100;2026-11-05\n"),
        ("B", "F1,100,05/11/2026\n"),
        ("C", "F1,100,2026/11/05\n"),
    ],
)
def test_formatos_de_los_tres_bancos(tmp_path, origen, pago):
    lote = _lote(tmp_path, {
        origen: _CABECERAS[origen] + pago,
        "facturas": _CABECERAS["facturas"] + "F1,100,2026-11-01\n",
    })
    lote.ejecutar()
    registro = lote.detalle[0]
    assert registro.estado == "conciliada"
    assert registro.valor_facturado == "100"
    assert registro.valor_pagado == "100"
    assert registro.banco == origen
    assert registro.diferencia == "0"
    assert not lote.incidencias


@pytest.mark.parametrize(
    ("pagado", "estado", "diferencia"),
    [(100, "conciliada", "0"), (80, "con_diferencia", "faltan 20"),
     (120, "con_diferencia", "sobran 20")],
)
def test_coincidencia_y_diferencias_sin_convencion_de_signo(tmp_path, pagado, estado, diferencia):
    lote = _lote(tmp_path, {
        "A": _CABECERAS["A"] + f"F1;{pagado};2026-11-05\n",
        "facturas": _CABECERAS["facturas"] + "F1,100,2026-11-01\n",
    })
    lote.ejecutar()
    assert lote.detalle[0].estado == estado
    assert lote.detalle[0].diferencia == diferencia


def test_factura_sin_pagos_pendiente(tmp_path):
    lote = _lote(tmp_path, {"facturas": _CABECERAS["facturas"] + "F1,100,2026-11-01\n"})
    lote.ejecutar()
    registro = lote.detalle[0]
    assert registro.estado == "pendiente"
    assert registro.valor_pagado == ""
    assert registro.valor_facturado == "100"
    assert registro.diferencia == ""
    assert registro.banco == ""


def test_pago_sin_factura(tmp_path):
    lote = _lote(tmp_path, {"A": _CABECERAS["A"] + "X;75;2026-11-05\n"})
    lote.ejecutar()
    registro = lote.detalle[0]
    assert registro.estado == "pago_sin_factura"
    assert registro.valor_facturado == ""
    assert registro.valor_pagado == "75"
    assert registro.diferencia == ""


@pytest.mark.parametrize("con_factura", [True, False])
def test_varios_pagos_revision_sin_sumar(tmp_path, con_factura):
    lote = _lote(tmp_path, {
        "A": _CABECERAS["A"] + "F1;40;2026-11-05\n",
        "B": _CABECERAS["B"] + "F1,60,05/11/2026\n",
        "facturas": _CABECERAS["facturas"] + (
            "F1,100,2026-11-01\n" if con_factura else ""
        ),
    })
    lote.ejecutar()
    assert len(lote.detalle) == 1
    registro = lote.detalle[0]
    assert registro.estado == "revision"
    assert json.loads(registro.valor_pagado) == ["40", "60"]
    assert registro.banco == "A|B"
    assert registro.diferencia == ""
    assert lote.resumen["revision"] == 1
    assert all(problema.fila == 2 for problema in lote.incidencias)


def test_varios_pagos_del_mismo_banco(tmp_path):
    lote = _lote(tmp_path, {
        "A": _CABECERAS["A"] + "F1;40;2026-11-05\nF1;60;2026-11-05\n",
    })
    lote.ejecutar()
    assert lote.detalle[0].estado == "revision"
    assert lote.detalle[0].banco == "A"
    assert json.loads(lote.detalle[0].valor_pagado) == ["40", "60"]


def test_facturas_repetidas_revision(tmp_path):
    lote = _lote(tmp_path, {
        "facturas": _CABECERAS["facturas"] + "F1,100,x\nF1,110,y\n",
        "A": _CABECERAS["A"] + "F1;100;2026-11-05\n",
    })
    lote.ejecutar()
    registro = lote.detalle[0]
    assert registro.estado == "revision"
    assert json.loads(registro.valor_facturado) == ["100", "110"]
    assert json.loads(registro.valor_pagado) == ["100"]
    assert registro.diferencia == ""
    assert {problema.fila for problema in lote.incidencias} == {2, 3}


@pytest.mark.parametrize(
    ("origen", "fecha"),
    [("A", "2026-02-30"), ("A", "2026-1-05"), ("A", ""),
     ("B", "2026-11-05"), ("C", "2026/13/05")],
)
def test_fecha_invalida_se_conserva_para_revision(tmp_path, origen, fecha):
    separador = ";" if origen == "A" else ","
    pago = separador.join(("F1", "100", fecha)) + "\n"
    lote = _lote(tmp_path, {
        origen: _CABECERAS[origen] + pago,
        "facturas": _CABECERAS["facturas"] + "F1,100,no definido\n",
    })
    lote.ejecutar()
    assert lote.detalle[0].estado == "revision"
    assert json.loads(lote.detalle[0].valor_pagado) == ["100"]
    assert lote.detalle[0].diferencia == ""
    problema = lote.incidencias[0]
    assert problema.archivo == str(tmp_path / f"{origen}.csv")
    assert problema.fila == 2
    assert "Fecha inválida" in problema.mensaje


def test_vencimiento_no_interviene_en_la_conciliacion(tmp_path):
    lote = _lote(tmp_path, {
        "A": _CABECERAS["A"] + "F1;100;2026-11-05\n",
        "facturas": _CABECERAS["facturas"] + "F1,100,formato no definido\n",
    })
    lote.ejecutar()
    assert lote.detalle[0].estado == "conciliada"
    assert not lote.incidencias


@pytest.mark.parametrize(
    ("origen", "contenido", "faltante"),
    [
        ("A", "referencia;fecha\nX;2026-11-05\n", "valor"),
        ("B", "MONTO,FECHA_PAGO\n100,05/11/2026\n", "REF"),
        ("C", "referencia_factura,valor_pagado\nX,100\n", "fecha"),
        ("facturas", "referencia,vencimiento\nX,2026-11-01\n", "valor"),
    ],
)
def test_columna_faltante_rechaza_archivo_y_sigue_lote(tmp_path, origen, contenido, faltante):
    lote = _lote(tmp_path, {origen: contenido})
    lote.ejecutar()
    assert lote.detalle == ()
    assert lote.completadas[-1] == "escritura"
    problema = lote.incidencias[0]
    assert problema.archivo == str(tmp_path / f"{origen}.csv")
    assert problema.columna == faltante
    assert problema.fila is None
    assert faltante in problema.mensaje


def test_todas_las_columnas_faltantes_se_informan(tmp_path):
    lote = _lote(tmp_path, {"A": "otra\nvalor\n"})
    lote.ejecutar()
    assert {problema.columna for problema in lote.incidencias} == {"referencia", "valor", "fecha"}


@pytest.mark.parametrize("origen", ["A", "B", "C", "facturas"])
def test_importe_no_numerico_rechaza_solo_fila(tmp_path, origen):
    separador = ";" if origen == "A" else ","
    fechas = {"A": "2026-11-05", "B": "05/11/2026", "C": "2026/11/05", "facturas": "x"}
    contenido = _CABECERAS[origen]
    contenido += separador.join(("MALA", "abc", fechas[origen])) + "\n"
    contenido += separador.join(("BUENA", "100", fechas[origen])) + "\n"
    lote = _lote(tmp_path, {origen: contenido})
    lote.ejecutar()
    assert [registro.referencia for registro in lote.detalle] == ["BUENA"]
    problema = lote.incidencias[0]
    assert problema.archivo == str(tmp_path / f"{origen}.csv")
    assert problema.fila == 2
    assert "importe no numérico" in problema.mensaje


@pytest.mark.parametrize("importe", ["100.50", "100.0", "1E2", "0", "-100"])
def test_importes_con_regla_no_definida_no_son_definitivos(tmp_path, importe):
    lote = _lote(tmp_path, {"A": _CABECERAS["A"] + f"F1;{importe};2026-11-05\n"})
    lote.ejecutar()
    assert lote.detalle[0].estado == "revision"
    assert json.loads(lote.detalle[0].valor_pagado) == [importe]
    assert lote.detalle[0].diferencia == ""
    assert lote.incidencias[0].columna == "valor"


@pytest.mark.parametrize("importe", ["", "$100", "1,000", "NaN", "Infinity"])
def test_formatos_no_interpretables_no_se_convierten_en_dinero(tmp_path, importe):
    lote = _lote(tmp_path, {"A": _CABECERAS["A"] + f"F1;{importe};2026-11-05\n"})
    lote.ejecutar()
    assert lote.detalle == ()
    assert "importe no numérico" in lote.incidencias[0].mensaje


def test_referencia_vacia_revision_y_no_asociacion_automatica(tmp_path):
    lote = _lote(tmp_path, {
        "A": _CABECERAS["A"] + ";100;2026-11-05\n",
        "facturas": _CABECERAS["facturas"] + ",100,x\n",
    })
    lote.ejecutar()
    assert len(lote.detalle) == 2
    assert all(registro.estado == "revision" for registro in lote.detalle)


def test_espacios_se_recortan_y_referencias_distinguen_mayusculas(tmp_path):
    lote = _lote(tmp_path, {
        "A": _CABECERAS["A"] + " F1 ; 100 ; 2026-11-05 \nf1;25;2026-11-05\n",
        "facturas": _CABECERAS["facturas"] + "F1,100,x\n",
    })
    lote.ejecutar()
    assert [(registro.referencia, registro.estado) for registro in lote.detalle] == [
        ("F1", "conciliada"), ("f1", "pago_sin_factura"),
    ]


def test_reportes_y_resumen_cuentan_registros_no_importes(tmp_path):
    lote = _lote(tmp_path, {
        "A": _CABECERAS["A"] + (
            "F1;100;2026-11-05\nF2;80;2026-11-05\n"
            "X;500;2026-11-05\nR;40;2026-11-05\nR;60;2026-11-05\n"
        ),
        "facturas": _CABECERAS["facturas"] + "F1,100,x\nF2,100,x\nF3,100,x\n",
    })
    lote.ejecutar()
    assert lote.resumen == {
        "conciliada": 1, "con_diferencia": 1, "pendiente": 1,
        "pago_sin_factura": 1, "revision": 1,
    }
    salida = tmp_path / "salida"
    with (salida / "detalle.csv").open(encoding="utf-8", newline="") as archivo:
        lector = csv.DictReader(archivo)
        assert lector.fieldnames == [
            "referencia", "valor_facturado", "valor_pagado", "banco", "estado", "diferencia",
        ]
        assert len(list(lector)) == 5
    assert json.loads((salida / "resumen.json").read_text(encoding="utf-8")) == lote.resumen
    problemas = json.loads((salida / "incidencias.json").read_text(encoding="utf-8"))
    assert len(problemas) == 2
    assert problemas[0]["fila"] == 5


def test_lote_vacio_y_estados_en_cero(tmp_path):
    lote = _lote(tmp_path)
    lote.ejecutar()
    assert lote.detalle == ()
    assert all(cantidad == 0 for cantidad in lote.resumen.values())


def test_orden_y_nombres_de_etapas(tmp_path):
    lote = _lote(tmp_path)
    with pytest.raises(ValueError, match="Etapa desconocida"):
        lote.ejecutar_etapa("otra")
    with pytest.raises(ValueError, match="primero la etapa lectura"):
        lote.ejecutar_etapa("conciliacion")
    with pytest.raises(ValueError, match="todavía"):
        _ = lote.detalle
    with pytest.raises(ValueError, match="todavía"):
        _ = lote.resumen
    assert lote.completadas == ()
    assert lote.etapa_fallida is None


def test_origen_desconocido(tmp_path):
    with pytest.raises(ValueError, match="Origen desconocido"):
        Lote([Entrada("D", tmp_path / "D.csv")], tmp_path / "salida")


def test_error_lectura_y_reintento_despues_de_corregir_archivo(tmp_path):
    ruta = tmp_path / "faltante.csv"
    lote = Lote([Entrada("A", ruta)], tmp_path / "salida")
    with pytest.raises(ErrorEtapa) as capturado:
        lote.ejecutar()
    assert capturado.value.etapa == "lectura"
    assert isinstance(capturado.value.__cause__, FileNotFoundError)
    assert lote.completadas == ()
    assert lote.etapa_fallida == "lectura"
    ruta.write_text(_CABECERAS["A"] + "X;100;2026-11-05\n", encoding="utf-8")
    lote.ejecutar_etapa("lectura")
    assert lote.completadas == ("lectura",)
    assert lote.etapa_fallida is None
    lote.ejecutar()
    assert lote.detalle[0].estado == "pago_sin_factura"


@pytest.mark.parametrize("contenido", [
    _CABECERAS["A"] + '"sin cierre;100;2026-11-05\n',
    _CABECERAS["A"] + "X;100;2026-11-05;extra\n",
])
def test_csv_malformado_falla_lectura_con_causa(tmp_path, contenido):
    lote = _lote(tmp_path, {"A": contenido})
    with pytest.raises(ErrorEtapa) as capturado:
        lote.ejecutar()
    assert capturado.value.etapa == "lectura"
    assert capturado.value.__cause__ is not None
    assert lote.completadas == ()
    assert lote.incidencias == ()


def test_codificacion_invalida_falla_lectura(tmp_path):
    lote = _lote(tmp_path)
    (tmp_path / "A.csv").write_bytes(b"\xff\xfe")
    with pytest.raises(ErrorEtapa) as capturado:
        lote.ejecutar()
    assert isinstance(capturado.value.__cause__, UnicodeError)


@pytest.mark.parametrize("etapa", ["normalizacion", "conciliacion", "escritura"])
def test_reintento_solo_etapa_fallida_conserva_anteriores(tmp_path, monkeypatch, etapa):
    lote = _lote(tmp_path, {
        "A": _CABECERAS["A"] + "F1;100;2026-11-05\n",
        "facturas": _CABECERAS["facturas"] + "F1,100,x\n",
    })
    etapas = ("lectura", "normalizacion", "conciliacion", "escritura")
    llamadas = dict.fromkeys(etapas, 0)

    def envolver(nombre, original):
        def ejecutar():
            llamadas[nombre] += 1
            if nombre == etapa and llamadas[nombre] == 1:
                raise OSError("Fallo transitorio de prueba")
            original()
        return ejecutar

    for nombre in etapas:
        atributo = f"_hacer_{nombre}"
        monkeypatch.setattr(lote, atributo, envolver(nombre, getattr(lote, atributo)))
    with pytest.raises(ErrorEtapa, match=etapa):
        lote.ejecutar()
    indice = etapas.index(etapa)
    assert lote.completadas == etapas[:indice]
    assert lote.etapa_fallida == etapa
    # Cambiar fuentes no debe modificar lo leído en una etapa anterior completada.
    (tmp_path / "A.csv").write_text(_CABECERAS["A"], encoding="utf-8")
    incidencias_anteriores = lote.incidencias
    lote.ejecutar_etapa(etapa)
    assert lote.completadas == etapas[:indice + 1]
    assert lote.incidencias == incidencias_anteriores
    for nombre in etapas[:indice]:
        assert llamadas[nombre] == 1
    assert llamadas[etapa] == 2
    for nombre in etapas[indice + 1:]:
        assert llamadas[nombre] == 0
    lote.ejecutar()
    assert lote.detalle[0].estado == "conciliada"
    assert lote.etapa_fallida is None
    llamadas_finales = llamadas.copy()
    lote.ejecutar()
    assert llamadas == llamadas_finales


def test_error_real_escritura_y_reintento(tmp_path):
    lote = _lote(tmp_path, {"A": _CABECERAS["A"] + "X;100;2026-11-05\n"})
    destino = tmp_path / "salida"
    destino.write_text("obstáculo", encoding="utf-8")
    with pytest.raises(ErrorEtapa) as capturado:
        lote.ejecutar()
    assert capturado.value.etapa == "escritura"
    assert lote.completadas == ("lectura", "normalizacion", "conciliacion")
    detalle = lote.detalle
    resumen = lote.resumen
    destino.unlink()
    lote.ejecutar_etapa("escritura")
    assert lote.detalle is detalle
    assert lote.resumen == resumen
    assert (destino / "detalle.csv").is_file()


def test_utf8_bom_y_columnas_no_requeridas(tmp_path):
    lote = _lote(tmp_path, {"A": "\ufeffreferencia;valor;fecha;nota\nFñ;100;2026-11-05;x\n"})
    lote.ejecutar()
    assert lote.detalle[0].referencia == "Fñ"
    assert not lote.incidencias


def test_resumen_devuelto_no_modifica_el_lote(tmp_path):
    lote = _lote(tmp_path)
    lote.ejecutar()
    resumen = lote.resumen
    resumen["conciliada"] = 99
    assert lote.resumen["conciliada"] == 0


def test_lectura_fallida_no_conserva_resultados_parciales(tmp_path):
    primera = tmp_path / "primera.csv"
    segunda = tmp_path / "segunda.csv"
    primera.write_text("referencia;fecha\nX;2026-11-05\n", encoding="utf-8")
    lote = Lote([Entrada("A", primera), Entrada("B", segunda)], tmp_path / "salida")
    with pytest.raises(ErrorEtapa):
        lote.ejecutar_etapa("lectura")
    assert lote.incidencias == ()
    primera.write_text(_CABECERAS["A"] + "X;100;2026-11-05\n", encoding="utf-8")
    segunda.write_text(_CABECERAS["B"], encoding="utf-8")
    lote.ejecutar()
    assert not lote.incidencias
    assert len(lote.detalle) == 1
