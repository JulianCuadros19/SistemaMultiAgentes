"""Pruebas de operaciones independientes sobre carpetas locales."""

import os
from pathlib import Path
from typing import cast

import pytest

from escaneos import procesar
from escaneos.core import Operacion


def _crear(carpeta: Path, nombre: str, contenido: bytes = b"escaneo") -> Path:
    """Crear un archivo de prueba sin depender de un PDF real."""
    archivo = carpeta / nombre
    archivo.write_bytes(contenido)
    return archivo


def test_validar_no_modifica(tmp_path: Path) -> None:
    """Listar nombres válidos e inválidos sin cambiar archivos."""
    _crear(tmp_path, "esc-2019-42.PDF")
    _crear(tmp_path, "XYZ_2019_00001.pdf")
    _crear(tmp_path, "CER_1950_00001.pdf")
    antes = {archivo.name: archivo.read_bytes() for archivo in tmp_path.iterdir()}
    informe = procesar(tmp_path, "validar")
    assert informe.total == 3
    assert informe.totales == {"Inválido": 2, "Válido": 1}
    assert informe.codigo_salida == 1
    assert all(archivo.motivo for archivo in informe.archivos)
    assert antes == {archivo.name: archivo.read_bytes() for archivo in tmp_path.iterdir()}


def test_renombrar_ejemplo_preserva_contenido(tmp_path: Path) -> None:
    """Renombrar el ejemplo del cliente manteniendo sus bytes."""
    origen = _crear(tmp_path, "esc-2019-42.PDF", b"contenido original")
    informe = procesar(tmp_path, "renombrar")
    assert informe.totales == {"Renombrado": 1}
    assert informe.codigo_salida == 0
    assert not origen.exists()
    assert (tmp_path / "ESC_2019_00042.pdf").read_bytes() == b"contenido original"


@pytest.mark.parametrize(
    ("nombre", "motivo"),
    [
        ("XYZ_2019_00001.pdf", "Tipo desconocido"),
        ("ESC_1949_00001.pdf", "Año fuera del rango"),
        ("ESC_2019_00001.txt", "Extensión distinta de pdf"),
        ("ESC_2019_123456.pdf", "más de cinco dígitos"),
        ("documento.pdf", "Formato inválido"),
    ],
)
def test_no_renombrar_errores(tmp_path: Path, nombre: str, motivo: str) -> None:
    """Mantener intactos los nombres que no se pueden corregir."""
    origen = _crear(tmp_path, nombre)
    informe = procesar(tmp_path, "renombrar")
    assert informe.archivos[0].estado == "Inválido"
    assert motivo in informe.archivos[0].motivo
    assert origen.read_bytes() == b"escaneo"
    assert len(list(tmp_path.iterdir())) == 1


def test_renombrar_valido_sin_cambios(tmp_path: Path) -> None:
    """Dejar un nombre ya válido sin cambios."""
    origen = _crear(tmp_path, "ESC_2019_00001.pdf")
    informe = procesar(tmp_path, "renombrar")
    assert informe.totales == {"Sin cambios": 1}
    assert informe.codigo_salida == 0
    assert origen.exists()


def test_simulacion_no_modifica(tmp_path: Path) -> None:
    """Mostrar el destino sin escribir ni eliminar nada."""
    origen = _crear(tmp_path, "esc-2019-42.PDF")
    informe = procesar(tmp_path, "renombrar", simular=True)
    assert informe.archivos[0].estado == "Simulado"
    assert informe.archivos[0].destino == "ESC_2019_00042.pdf"
    assert informe.codigo_salida == 0
    assert origen.read_bytes() == b"escaneo"
    assert not (tmp_path / "ESC_2019_00042.pdf").exists()


@pytest.mark.parametrize("simular", [False, True])
def test_conflicto_destino_existente(tmp_path: Path, simular: bool) -> None:
    """No sobrescribir un destino existente ni siquiera en simulación."""
    origen = _crear(tmp_path, "esc-2019-42.PDF", b"origen")
    destino = _crear(tmp_path, "ESC_2019_00042.pdf", b"destino")
    informe = procesar(tmp_path, "renombrar", simular=simular)
    conflictos = [archivo for archivo in informe.archivos if archivo.estado == "Conflicto"]
    assert len(conflictos) == 1
    assert conflictos[0].destino == destino.name
    assert informe.codigo_salida == 1
    assert origen.read_bytes() == b"origen"
    assert destino.read_bytes() == b"destino"


@pytest.mark.parametrize("simular", [False, True])
def test_colision_entre_correcciones(tmp_path: Path, simular: bool) -> None:
    """Reservar los destinos en orden para reproducir los conflictos en simulación."""
    _crear(tmp_path, "esc-2019-42.PDF", b"primero")
    segundo = _crear(tmp_path, "esc_2019_42.pdf", b"segundo")
    informe = procesar(tmp_path, "renombrar", simular=simular)
    exito = "Simulado" if simular else "Renombrado"
    assert [archivo.estado for archivo in informe.archivos] == [exito, "Conflicto"]
    assert segundo.read_bytes() == b"segundo"
    if simular:
        assert not (tmp_path / "ESC_2019_00042.pdf").exists()
    else:
        assert (tmp_path / "ESC_2019_00042.pdf").read_bytes() == b"primero"


def test_destino_directorio_es_conflicto(tmp_path: Path) -> None:
    """Considerar ocupados también los nombres de directorios."""
    origen = _crear(tmp_path, "esc-2019-42.PDF")
    (tmp_path / "ESC_2019_00042.pdf").mkdir()
    informe = procesar(tmp_path, "renombrar")
    assert informe.total == 1
    assert informe.archivos[0].estado == "Conflicto"
    assert origen.exists()


def test_reporte_por_anio_y_tipo(tmp_path: Path) -> None:
    """Contar solo nombres conformes y listar también los excluidos."""
    for nombre in (
        "ESC_1950_00001.pdf",
        "ESC_2019_00002.pdf",
        "CER_2019_00003.pdf",
        "PAZ_2019_00004.pdf",
        "esc-2019-42.PDF",
        "XYZ_2019_00001.pdf",
    ):
        _crear(tmp_path, nombre)
    antes = sorted(archivo.name for archivo in tmp_path.iterdir())
    informe = procesar(tmp_path, "reporte")
    assert informe.total == 6
    assert informe.por_anio == {1950: 1, 2019: 3}
    assert informe.por_tipo == {"CER": 1, "ESC": 2, "PAZ": 1}
    assert informe.totales == {"Inválido": 2, "Válido": 4}
    assert antes == sorted(archivo.name for archivo in tmp_path.iterdir())


@pytest.mark.parametrize("operacion", ["validar", "renombrar", "reporte"])
def test_carpeta_vacia(tmp_path: Path, operacion: Operacion) -> None:
    """Completar las tres operaciones con totales cero."""
    informe = procesar(tmp_path, operacion)
    assert informe.total == 0
    assert informe.totales == {}
    assert informe.por_anio == {}
    assert informe.por_tipo == {}
    assert informe.codigo_salida == 0


def test_carpeta_inexistente(tmp_path: Path) -> None:
    """Producir una excepción con un mensaje claro."""
    with pytest.raises(FileNotFoundError, match="La carpeta no existe"):
        procesar(tmp_path / "ausente", "validar")


def test_ruta_no_directorio(tmp_path: Path) -> None:
    """Rechazar un archivo como argumento de carpeta."""
    archivo = _crear(tmp_path, "archivo.pdf")
    with pytest.raises(NotADirectoryError, match="no es una carpeta"):
        procesar(archivo, "validar")


def test_no_recorrer_subcarpetas(tmp_path: Path) -> None:
    """No examinar ni modificar archivos anidados."""
    subcarpeta = tmp_path / "subcarpeta"
    subcarpeta.mkdir()
    origen = _crear(subcarpeta, "esc-2019-42.PDF")
    assert procesar(tmp_path, "renombrar").total == 0
    assert origen.exists()


def test_enlaces_simbolicos(tmp_path: Path) -> None:
    """Ignorar enlaces como entradas y respetarlos como destinos ocupados."""
    origen = _crear(tmp_path, "esc-2019-42.PDF")
    enlace = tmp_path / "ESC_2019_00042.pdf"
    try:
        enlace.symlink_to(tmp_path / "ausente")
    except (OSError, NotImplementedError):
        pytest.skip("El sistema no permite crear enlaces simbólicos")
    informe = procesar(tmp_path, "renombrar")
    assert informe.total == 1
    assert informe.archivos[0].estado == "Conflicto"
    assert origen.exists()
    assert enlace.is_symlink()


def test_error_de_enlace_no_pierde_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Informar fallos de E/S y conservar el archivo de origen."""
    origen = _crear(tmp_path, "esc-2019-42.PDF")

    def _fallar(
        origen: Path, destino: Path, *, follow_symlinks: bool = True
    ) -> None:
        raise OSError("Sistema de archivos sin enlaces duros")

    monkeypatch.setattr("escaneos.core.os.link", _fallar)
    informe = procesar(tmp_path, "renombrar")
    assert informe.archivos[0].estado == "Error"
    assert informe.codigo_salida == 2
    assert origen.read_bytes() == b"escaneo"
    assert not (tmp_path / "ESC_2019_00042.pdf").exists()


def test_conflicto_aparecido_durante_el_renombrado(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No sobrescribir un destino creado después de listar la carpeta."""
    origen = _crear(tmp_path, "esc-2019-42.PDF", b"origen")
    enlazar = os.link

    def _crear_destino_y_enlazar(
        origen: Path, destino: Path, *, follow_symlinks: bool = True
    ) -> None:
        destino.write_bytes(b"otro archivo")
        enlazar(origen, destino, follow_symlinks=follow_symlinks)

    monkeypatch.setattr("escaneos.core.os.link", _crear_destino_y_enlazar)
    informe = procesar(tmp_path, "renombrar")
    assert informe.archivos[0].estado == "Conflicto"
    assert origen.read_bytes() == b"origen"
    assert (tmp_path / "ESC_2019_00042.pdf").read_bytes() == b"otro archivo"


def test_error_al_eliminar_original_revierte_enlace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Deshacer el destino cuando no se puede eliminar el nombre original."""
    origen = _crear(tmp_path, "esc-2019-42.PDF")
    eliminar = Path.unlink

    def _eliminar(self: Path, missing_ok: bool = False) -> None:
        if self == origen:
            raise PermissionError("No se puede eliminar el original")
        eliminar(self, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", _eliminar)
    informe = procesar(tmp_path, "renombrar")
    assert informe.archivos[0].estado == "Error"
    assert origen.exists()
    assert not (tmp_path / "ESC_2019_00042.pdf").exists()


def test_operacion_desconocida(tmp_path: Path) -> None:
    """Rechazar operaciones ajenas a la API."""
    with pytest.raises(ValueError, match="Operación desconocida"):
        procesar(tmp_path, cast(Operacion, "otra"))


@pytest.mark.parametrize("operacion", ["validar", "reporte"])
def test_simulacion_solo_para_renombrar(tmp_path: Path, operacion: Operacion) -> None:
    """No mezclar simulación con operaciones de solo lectura."""
    with pytest.raises(ValueError, match="solo está disponible para renombrar"):
        procesar(tmp_path, operacion, simular=True)
