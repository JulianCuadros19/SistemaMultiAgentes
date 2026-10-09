"""Entorno aislado sin Docker: invocación, empaquetado y lectura del resultado."""

import io
import subprocess
import tarfile

import pytest

from multiagente.core.configuracion import ConfiguracionSandbox
from multiagente.sandbox import ejecutor
from multiagente.sandbox.ejecutor import (
    MARCA_RESULTADO,
    EntornoAislado,
    ErrorEntornoAislado,
    empaquetar,
    es_ruta_segura,
)

CONFIGURACION = ConfiguracionSandbox(_env_file=None)


def test_la_invocacion_aisla_red_archivos_y_privilegios():
    argumentos = EntornoAislado(CONFIGURACION).argumentos("c1", ["python", "-c", "pass"])
    for opcion in (
        "--rm",
        "--pull=never",
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--user=10001:10001",
        "--pids-limit=128",
        "--memory=512m",
        "--cpus=1",
    ):
        assert opcion in argumentos
    # Ningún volumen, montaje ni puerto del anfitrión.
    prohibidas = ("-v", "--volume", "--mount", "-p", "--publish")
    assert not any(argumento.startswith(prohibidas) for argumento in argumentos)
    imagen = argumentos.index(CONFIGURACION.imagen)
    assert argumentos[imagen + 1 : imagen + 3] == ["sh", "-c"]
    assert argumentos[-3:] == ["python", "-c", "pass"]


@pytest.mark.parametrize(
    "ruta, segura",
    [
        ("src/dominio/predio.py", True),
        ("tests/test_predio.py", True),
        ("USO.md", True),
        ("/etc/passwd", False),
        ("../fuera.py", False),
        ("src/../../fuera.py", False),
        ("src//doble.py", False),
        ("src\\windows.py", False),
        ("src/", False),
        ("", False),
        ("./src/a.py", False),
    ],
)
def test_rutas_seguras(ruta, segura):
    assert es_ruta_segura(ruta) is segura


def test_empaqueta_en_orden_y_rechaza_rutas_inseguras():
    datos = empaquetar({"src/b.py": "B = 2\n", "src/a.py": "A = 'ñ'\n"})
    with tarfile.open(fileobj=io.BytesIO(datos)) as tar:
        assert tar.getnames() == ["src/a.py", "src/b.py"]
        assert tar.extractfile("src/a.py").read().decode("utf-8") == "A = 'ñ'\n"
    with pytest.raises(ValueError, match="no admitidas"):
        empaquetar({"../fuera.py": ""})


def completado(salida: str = "", errores: str = "", codigo: int = 0):
    def ejecutar(argumentos, **opciones):
        assert opciones["input"]  # el código entra por la entrada estándar
        return subprocess.CompletedProcess(
            argumentos, codigo, salida.encode("utf-8"), errores.encode("utf-8")
        )

    return ejecutar


def test_importar_lee_la_linea_marcada(monkeypatch):
    salida = f'impreso por el módulo\n{MARCA_RESULTADO}{{"dominio.malo": "ModuleNotFoundError"}}\n'
    monkeypatch.setattr(ejecutor.subprocess, "run", completado(salida))
    resultado = EntornoAislado(CONFIGURACION).importar(
        {"src/dominio/malo.py": "import x\n"}, ["dominio.malo"]
    )
    assert resultado.errores == {"dominio.malo": "ModuleNotFoundError"}
    assert not resultado.exito


def test_importar_sin_resultado_marca_todos_los_modulos(monkeypatch):
    monkeypatch.setattr(ejecutor.subprocess, "run", completado(errores="Killed", codigo=137))
    resultado = EntornoAislado(CONFIGURACION).importar({"src/a.py": ""}, ["a", "b"])
    assert set(resultado.errores) == {"a", "b"}
    assert "Killed" in resultado.errores["a"]


def test_error_de_docker_es_un_error_del_entorno(monkeypatch):
    monkeypatch.setattr(ejecutor.subprocess, "run", completado(errores="No such image", codigo=125))
    with pytest.raises(ErrorEntornoAislado, match="build sandbox"):
        EntornoAislado(CONFIGURACION).ejecutar({}, ["true"])


def test_tiempo_vencido_mata_el_contenedor(monkeypatch):
    invocaciones = []

    def ejecutar(argumentos, **opciones):
        invocaciones.append(argumentos)
        if argumentos[1] == "run":
            raise subprocess.TimeoutExpired(argumentos, 1, output=b"parcial")
        return subprocess.CompletedProcess(argumentos, 0, b"", b"")

    monkeypatch.setattr(ejecutor.subprocess, "run", ejecutar)
    resultado = EntornoAislado(CONFIGURACION).ejecutar({}, ["sleep", "9"], tiempo_limite_s=1)
    assert resultado.vencido and not resultado.exito
    assert resultado.salida == "parcial"
    nombre = next(a.removeprefix("--name=") for a in invocaciones[0] if a.startswith("--name="))
    assert invocaciones[1] == ["docker", "kill", nombre]
