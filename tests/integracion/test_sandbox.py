"""Entorno aislado con Docker real: aislamiento, importación y tiempo límite (RF-20, RNF-03).

Requiere Docker y la imagen: `docker compose --profile sandbox build sandbox`, y luego
`pytest -m sandbox`.
"""

import subprocess

import pytest

pytestmark = pytest.mark.sandbox


def test_imagen_con_python_311_y_el_catalogo(entorno_aislado):
    resultado = entorno_aislado.ejecutar(
        {},
        [
            "python",
            "-c",
            "import sys, pydantic, typer, fastapi, uvicorn, sqlalchemy, psycopg, pandas, numpy,"
            " pytest; print(sys.version_info[:2])",
        ],
    )
    assert resultado.exito, resultado.errores
    assert resultado.salida.strip() == "(3, 11)"


def test_importa_los_modulos_y_reporta_los_que_fallan(entorno_aislado):
    archivos = {
        "src/dominio/predio.py": '"""Predio."""\n\nAREA = 1\n',
        "src/aplicacion/avaluo.py": "from dominio.predio import AREA\n\nTOTAL = AREA * 2\n",
        "src/aplicacion/rota.py": "import modulo_inexistente\n",
        "src/aplicacion/sintaxis.py": "def f(:\n",
    }
    resultado = entorno_aislado.importar(
        archivos,
        ["dominio.predio", "aplicacion.avaluo", "aplicacion.rota", "aplicacion.sintaxis"],
    )
    assert set(resultado.errores) == {"aplicacion.rota", "aplicacion.sintaxis"}
    assert "ModuleNotFoundError" in resultado.errores["aplicacion.rota"]
    assert "SyntaxError" in resultado.errores["aplicacion.sintaxis"]


def test_sin_red(entorno_aislado):
    resultado = entorno_aislado.ejecutar(
        {},
        ["python", "-c", "import socket; socket.create_connection(('1.1.1.1', 53), timeout=3)"],
    )
    assert resultado.codigo_salida != 0
    assert "unreachable" in resultado.errores.lower()


def test_sin_root_y_sin_escritura_fuera_de_tmp(entorno_aislado):
    resultado = entorno_aislado.ejecutar(
        {},
        [
            "python",
            "-c",
            "import os\nassert os.getuid() != 0\n"
            "for ruta in ('/codigo.txt', '/opt/sandbox/x', '/usr/local/lib/x'):\n"
            "    try:\n        open(ruta, 'w')\n    except OSError:\n        continue\n"
            "    raise SystemExit(f'escribió en {ruta}')\n"
            "open('/tmp/codigo/permitido.txt', 'w').write('ok')",
        ],
    )
    assert resultado.exito, resultado.errores


def test_tiempo_vencido_mata_y_elimina_el_contenedor(entorno_aislado):
    resultado = entorno_aislado.ejecutar(
        {}, ["python", "-c", "import time; time.sleep(60)"], tiempo_limite_s=3
    )
    assert resultado.vencido
    restantes = subprocess.run(
        ["docker", "ps", "-a", "--filter", "name=multiagente-sandbox-", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert restantes.stdout.strip() == ""
