"""Pruebas de terminal, mensajes, resúmenes y códigos de salida."""

import runpy
from pathlib import Path

import pytest

from escaneos.cli import main


def test_cli_validar(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Emitir una línea por archivo y un resumen de validación."""
    (tmp_path / "ESC_2019_00001.pdf").write_bytes(b"a")
    (tmp_path / "XYZ_2019_00001.pdf").write_bytes(b"b")
    assert main(["validar", str(tmp_path)]) == 1
    salida = capsys.readouterr()
    assert salida.err == ""
    assert len(salida.out.splitlines()) == 3
    assert "[Válido]" in salida.out
    assert "[Inválido]" in salida.out
    assert "Tipo desconocido" in salida.out
    assert "Resumen: Total=2, Inválido=1, Válido=1" in salida.out


def test_cli_simular(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Mostrar la corrección sin aplicarla desde la terminal."""
    origen = tmp_path / "esc-2019-42.PDF"
    origen.write_bytes(b"a")
    assert main(["renombrar", str(tmp_path), "--simular"]) == 0
    salida = capsys.readouterr().out
    assert "[Simulado]" in salida
    assert "'esc-2019-42.PDF' -> 'ESC_2019_00042.pdf'" in salida
    assert "Resumen: Total=1, Simulado=1" in salida
    assert origen.exists()


def test_cli_renombrar(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Aplicar cambios sin requerir interacción para tareas programadas."""
    (tmp_path / "esc-2019-42.PDF").write_bytes(b"a")
    assert main(["renombrar", str(tmp_path)]) == 0
    assert "[Renombrado]" in capsys.readouterr().out
    assert (tmp_path / "ESC_2019_00042.pdf").exists()


def test_cli_conflicto(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Mostrar la palabra Conflicto y devolver un código no exitoso."""
    (tmp_path / "esc-2019-42.PDF").write_bytes(b"a")
    (tmp_path / "ESC_2019_00042.pdf").write_bytes(b"b")
    assert main(["renombrar", str(tmp_path)]) == 1
    assert "[Conflicto]" in capsys.readouterr().out


def test_cli_reporte(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Mostrar archivos, resumen y conteos independientes por año y tipo."""
    (tmp_path / "CER_2019_00001.pdf").write_bytes(b"a")
    (tmp_path / "PAZ_1950_00002.pdf").write_bytes(b"b")
    assert main(["reporte", str(tmp_path)]) == 0
    salida = capsys.readouterr().out
    assert len(salida.splitlines()) == 5
    assert "Resumen: Total=2, Válido=2" in salida
    assert "Por año: 1950=1, 2019=1" in salida
    assert "Por tipo: CER=1, PAZ=1" in salida


def test_cli_carpeta_inexistente(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Dar un mensaje claro en stderr y un código distinto de cero."""
    assert main(["validar", str(tmp_path / "ausente")]) == 2
    salida = capsys.readouterr()
    assert "La carpeta no existe" in salida.err
    assert salida.out == ""


def test_cli_ruta_no_directorio(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Informar cuando el argumento es un archivo y no una carpeta."""
    archivo = tmp_path / "archivo.pdf"
    archivo.write_bytes(b"a")
    assert main(["validar", str(archivo)]) == 2
    assert "no es una carpeta" in capsys.readouterr().err


@pytest.mark.parametrize(
    "argumentos", [[], ["validar"], ["renombrar"], ["reporte"], ["otra", "."]]
)
def test_cli_argumentos_obligatorios(
    argumentos: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    """Exigir la operación y la carpeta mediante argparse."""
    with pytest.raises(SystemExit) as error:
        main(argumentos)
    assert error.value.code == 2
    assert capsys.readouterr().err


@pytest.mark.parametrize("operacion", ["validar", "reporte"])
def test_cli_no_mezclar_simulacion(
    tmp_path: Path, operacion: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """Permitir --simular únicamente en renombrar."""
    with pytest.raises(SystemExit) as error:
        main([operacion, str(tmp_path), "--simular"])
    assert error.value.code == 2
    assert capsys.readouterr().err


def test_cli_reporte_vacio(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Mostrar totales cero sin producir líneas ficticias por archivo."""
    assert main(["reporte", str(tmp_path)]) == 0
    salida = capsys.readouterr().out
    assert salida.splitlines() == [
        "Resumen: Total=0",
        "Por año: (sin archivos válidos)",
        "Por tipo: (sin archivos válidos)",
    ]


def test_entrada_python_m(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verificar el punto de entrada del paquete sin lanzar subprocesos."""
    monkeypatch.setattr("sys.argv", ["escaneos", "validar", str(tmp_path)])
    with pytest.raises(SystemExit) as error:
        runpy.run_module("escaneos", run_name="__main__")
    assert error.value.code == 0
    assert "Resumen: Total=0" in capsys.readouterr().out
