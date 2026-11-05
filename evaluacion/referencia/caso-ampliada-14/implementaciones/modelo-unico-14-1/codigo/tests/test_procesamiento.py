"""Pruebas de modos, conflictos, reportes y fallos de archivos."""

from pathlib import Path

import pytest

from expedientes import CarpetaError, procesar_carpeta
from expedientes.cli import main


def crear(carpeta, nombre, contenido=b"documento"):
    archivo = carpeta / nombre
    archivo.write_bytes(contenido)
    return archivo


def test_validar_no_modifica_y_da_motivos(tmp_path):
    crear(tmp_path, "ESC_2019_00042.pdf")
    crear(tmp_path, "esc-2019-42.PDF")
    crear(tmp_path, "XYZ_2019_00001.pdf")
    antes = sorted(p.name for p in tmp_path.iterdir())
    informe = procesar_carpeta(tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir()) == antes
    assert informe.totales == {"Correcto": 1, "Error": 1, "No cumple": 1}
    assert all(r.detalle for r in informe.resultados)
    assert informe.codigo_salida == 1


def test_simulacion_muestra_cambio_sin_guardarlo(tmp_path):
    origen = crear(tmp_path, "esc-2019-42.PDF")
    informe = procesar_carpeta(tmp_path, "renombrar", simular=True)
    assert informe.resultados[0].estado == "Cambio"
    assert informe.resultados[0].destino == "ESC_2019_00042.pdf"
    assert origen.exists()
    assert not (tmp_path / "ESC_2019_00042.pdf").exists()
    assert informe.codigo_salida == 0


def test_aplicar_preserva_contenido_y_no_cambia_validos(tmp_path):
    origen = crear(tmp_path, "esc-2019-42.PDF", b"contenido exacto")
    correcto = crear(tmp_path, "PAZ_2020_00002.pdf", b"sin cambios")
    informe = procesar_carpeta(tmp_path, "renombrar")
    assert not origen.exists()
    assert (tmp_path / "ESC_2019_00042.pdf").read_bytes() == b"contenido exacto"
    assert correcto.read_bytes() == b"sin cambios"
    assert informe.totales == {"Correcto": 1, "Renombrado": 1}


@pytest.mark.parametrize("simular", [False, True])
def test_dos_correcciones_al_mismo_destino_conflicto(tmp_path, simular):
    crear(tmp_path, "esc-2019-42.PDF", b"uno")
    crear(tmp_path, "ESC_2019_42.pdf", b"dos")
    informe = procesar_carpeta(tmp_path, "renombrar", simular=simular)
    assert informe.totales == {"Conflicto": 2}
    assert all(r.detalle == "Conflicto" for r in informe.resultados)
    assert len(list(tmp_path.iterdir())) == 2
    assert not (tmp_path / "ESC_2019_00042.pdf").exists()


@pytest.mark.parametrize("simular", [False, True])
def test_destino_existente_no_se_sobrescribe(tmp_path, simular):
    origen = crear(tmp_path, "esc-2019-42.PDF", b"origen")
    destino = crear(tmp_path, "ESC_2019_00042.pdf", b"destino")
    informe = procesar_carpeta(tmp_path, "renombrar", simular=simular)
    assert informe.totales == {"Correcto": 1, "Conflicto": 1}
    assert origen.read_bytes() == b"origen"
    assert destino.read_bytes() == b"destino"
    assert informe.codigo_salida == 1


def test_directorio_destino_tambien_bloquea(tmp_path):
    crear(tmp_path, "esc-2019-42.PDF")
    (tmp_path / "ESC_2019_00042.pdf").mkdir()
    assert procesar_carpeta(tmp_path, "renombrar").totales == {"Conflicto": 1}


def test_error_no_se_renombra(tmp_path):
    origen = crear(tmp_path, "XYZ_2019_00001.pdf")
    informe = procesar_carpeta(tmp_path, "renombrar")
    assert informe.totales == {"Error": 1}
    assert origen.exists()


def test_reporte_cuenta_solo_correctos_por_anio_y_tipo(tmp_path):
    for nombre in (
        "ESC_2019_00001.pdf", "CER_2019_00002.pdf", "PAZ_2020_00003.pdf",
        "esc-2019-1.PDF", "XYZ_2019_00001.pdf",
    ):
        crear(tmp_path, nombre)
    informe = procesar_carpeta(tmp_path, "reportar")
    assert informe.por_anio == {2019: 2, 2020: 1}
    assert informe.por_tipo == {"CER": 1, "ESC": 1, "PAZ": 1}
    assert len(informe.resultados) == 5
    assert "Conflicto" not in informe.totales
    assert len(list(tmp_path.iterdir())) == 5


def test_solo_archivos_directos(tmp_path):
    subcarpeta = tmp_path / "subcarpeta"
    subcarpeta.mkdir()
    crear(subcarpeta, "XYZ_2019_00001.pdf")
    crear(tmp_path, "ESC_2019_00001.pdf")
    assert procesar_carpeta(tmp_path).totales == {"Correcto": 1}


def test_carpeta_vacia(tmp_path):
    informe = procesar_carpeta(tmp_path, "reportar")
    assert informe.resultados == ()
    assert informe.totales == {}
    assert informe.por_anio == informe.por_tipo == {}
    assert informe.codigo_salida == 0


def test_carpeta_inexistente_termina_con_mensaje(tmp_path, capsys):
    assert main(["validar", str(tmp_path / "ausente")]) == 2
    salida = capsys.readouterr()
    assert "La carpeta no existe" in salida.err
    assert salida.out == ""


def test_ruta_no_es_carpeta(tmp_path):
    archivo = crear(tmp_path, "archivo.pdf")
    with pytest.raises(CarpetaError, match="no es una carpeta"):
        procesar_carpeta(archivo)


def test_error_lectura_termina(tmp_path, monkeypatch):
    def fallar(_ruta):
        raise PermissionError("lectura denegada")

    monkeypatch.setattr("expedientes.core.os.scandir", fallar)
    with pytest.raises(CarpetaError, match="No se puede leer"):
        procesar_carpeta(tmp_path)


def test_fallo_renombrado_continua(tmp_path, monkeypatch):
    crear(tmp_path, "esc-2019-1.PDF")
    crear(tmp_path, "paz-2019-2.PDF")
    from expedientes import core

    mover = core._mover_sin_sobrescribir

    def fallar_uno(origen, destino):
        if origen.name.startswith("esc"):
            raise PermissionError("permiso denegado")
        mover(origen, destino)

    monkeypatch.setattr(core, "_mover_sin_sobrescribir", fallar_uno)
    informe = procesar_carpeta(tmp_path, "renombrar")
    assert informe.totales == {"Error": 1, "Renombrado": 1}
    assert "permiso denegado" in informe.resultados[0].detalle
    assert (tmp_path / "esc-2019-1.PDF").exists()
    assert (tmp_path / "PAZ_2019_00002.pdf").exists()


def test_destino_aparece_durante_cambio_no_sobrescribe(tmp_path, monkeypatch):
    crear(tmp_path, "esc-2019-1.PDF")
    from expedientes import core

    mover = core._mover_sin_sobrescribir

    def crear_destino_antes(origen, destino):
        destino.write_bytes(b"otro archivo")
        mover(origen, destino)

    monkeypatch.setattr(core, "_mover_sin_sobrescribir", crear_destino_antes)
    informe = procesar_carpeta(tmp_path, "renombrar")
    assert informe.totales == {"Conflicto": 1}
    assert (tmp_path / "ESC_2019_00001.pdf").read_bytes() == b"otro archivo"
    assert (tmp_path / "esc-2019-1.PDF").exists()


def test_fallo_borrado_origen_revierte_enlace(tmp_path, monkeypatch):
    origen = crear(tmp_path, "esc-2019-1.PDF")
    unlink = Path.unlink

    def fallar_origen(archivo, missing_ok=False):
        if archivo == origen:
            raise PermissionError("no se puede quitar el origen")
        unlink(archivo, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", fallar_origen)
    assert procesar_carpeta(tmp_path, "renombrar").totales == {"Error": 1}
    assert origen.exists()
    assert not (tmp_path / "ESC_2019_00001.pdf").exists()


def test_terminal_linea_por_archivo_resumen_y_reporte(tmp_path, capsys):
    crear(tmp_path, "ESC_2019_00001.pdf")
    crear(tmp_path, "CER_2020_00002.pdf")
    assert main(["reportar", str(tmp_path)]) == 0
    lineas = capsys.readouterr().out.splitlines()
    assert len(lineas) == 5
    assert "CER_2020_00002.pdf" in lineas[0]
    assert "ESC_2019_00001.pdf" in lineas[1]
    assert "Resumen: archivos: 2" in lineas[2]
    assert lineas[3] == "Por año: 2019: 1, 2020: 1"
    assert lineas[4] == "Por tipo: CER: 1, ESC: 1"


def test_terminal_simulacion(tmp_path, capsys):
    crear(tmp_path, "esc-2019-42.PDF")
    assert main(["renombrar", str(tmp_path), "--simular"]) == 0
    assert "Cambio" in capsys.readouterr().out
    assert (tmp_path / "esc-2019-42.PDF").exists()


@pytest.mark.parametrize("modo", ["validar", "reportar"])
def test_simulacion_incompatible(tmp_path, modo):
    with pytest.raises(ValueError, match="solo se admite"):
        procesar_carpeta(tmp_path, modo, simular=True)
    with pytest.raises(SystemExit) as error:
        main([modo, str(tmp_path), "--simular"])
    assert error.value.code == 2


def test_modo_desconocido(tmp_path):
    with pytest.raises(ValueError, match="Modo desconocido"):
        procesar_carpeta(tmp_path, "otro")
