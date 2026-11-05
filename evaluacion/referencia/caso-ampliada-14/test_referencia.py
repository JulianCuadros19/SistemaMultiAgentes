"""Pruebas de aceptación de referencia del caso 14, escaneos de expedientes (ADR-0019).

Verifican solo lo que la ficha del caso dice sin ambigüedad, a través de la interfaz de
`interfaz.md`. Las mismas pruebas evalúan al sistema y a las líneas base de un solo modelo.
"""

import re

from adaptador_referencia import codigo_de_salida, renombrar, reporte, validar


def _carpeta(tmp_path, *nombres):
    for nombre in nombres:
        (tmp_path / nombre).write_bytes(b"%PDF-1.4")
    return str(tmp_path)


def _archivos(tmp_path):
    return {ruta.name for ruta in tmp_path.iterdir()}


def test_validar_lista_el_tipo_desconocido(tmp_path):
    motivos = validar(_carpeta(tmp_path, "XYZ_2019_00001.pdf"))
    assert "tipo" in motivos["XYZ_2019_00001.pdf"].lower()


def test_validar_lista_el_anio_fuera_de_rango(tmp_path):
    motivos = validar(_carpeta(tmp_path, "ESC_1949_00001.pdf"))
    assert re.search(r"a(ñ|n|ni)o", motivos["ESC_1949_00001.pdf"].lower())


def test_validar_lista_la_extension_distinta(tmp_path):
    motivos = validar(_carpeta(tmp_path, "ESC_2019_00001.doc"))
    assert "extensi" in motivos["ESC_2019_00001.doc"].lower()


def test_validar_no_lista_un_nombre_correcto(tmp_path):
    motivos = validar(_carpeta(tmp_path, "ESC_2019_00042.pdf", "XYZ_2019_00001.pdf"))
    assert "ESC_2019_00042.pdf" not in motivos


def test_renombrar_corrige_el_ejemplo(tmp_path):
    renombrar(_carpeta(tmp_path, "esc-2019-42.PDF"), False)
    assert _archivos(tmp_path) == {"ESC_2019_00042.pdf"}


def test_renombrar_corrige_los_espacios(tmp_path):
    renombrar(_carpeta(tmp_path, "cer 2020 7.pdf"), False)
    assert _archivos(tmp_path) == {"CER_2020_00007.pdf"}


def test_la_simulacion_no_cambia_nada(tmp_path):
    cambios = renombrar(_carpeta(tmp_path, "esc-2019-42.PDF"), True)
    assert _archivos(tmp_path) == {"esc-2019-42.PDF"}
    assert "ESC_2019_00042.pdf" in cambios["esc-2019-42.PDF"]


def test_renombrar_no_toca_un_tipo_desconocido(tmp_path):
    renombrar(_carpeta(tmp_path, "XYZ_2019_00001.pdf"), False)
    assert _archivos(tmp_path) == {"XYZ_2019_00001.pdf"}


def test_renombrar_reporta_el_conflicto(tmp_path):
    cambios = renombrar(_carpeta(tmp_path, "esc-2019-42.PDF", "ESC_2019_00042.pdf"), False)
    assert _archivos(tmp_path) == {"esc-2019-42.PDF", "ESC_2019_00042.pdf"}
    assert "conflicto" in cambios["esc-2019-42.PDF"].lower()


def test_reporte_cuenta_por_anio_y_por_tipo(tmp_path):
    carpeta = _carpeta(
        tmp_path, "ESC_2019_00042.pdf", "CER_2019_00001.pdf", "PAZ_2020_00001.pdf"
    )
    por_anio, por_tipo = reporte(carpeta)
    assert {str(anio): cantidad for anio, cantidad in por_anio.items()} == {"2019": 2, "2020": 1}
    assert por_tipo == {"ESC": 1, "CER": 1, "PAZ": 1}


def test_carpeta_inexistente_termina_con_error(tmp_path):
    inexistente = str(tmp_path / "no-existe")
    assert codigo_de_salida("validar", inexistente) != 0
    assert codigo_de_salida("reporte", inexistente) != 0
    assert codigo_de_salida("reporte", str(tmp_path)) == 0
