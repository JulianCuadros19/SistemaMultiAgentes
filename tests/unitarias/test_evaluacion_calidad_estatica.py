"""Detectores de calidad estática del objetivo 4 (ADR-0019), con ejemplos pequeños."""

import ast

import pytest

from multiagente.evaluacion.calidad_estatica import (
    Metricas,
    complejidades,
    contar_no_deterministas,
    contar_nombres_privados,
    contar_pruebas,
    contar_recursos_sin_with,
    contar_sentencias_global,
    es_de_pruebas,
    leer_archivos,
    lineas_no_vacias,
    medir,
)


def _arbol(codigo: str) -> ast.Module:
    return ast.parse(codigo)


def test_distingue_las_pruebas_del_codigo():
    assert es_de_pruebas("tests/test_a.py")
    assert es_de_pruebas("src/modulo/tests/test_a.py")
    assert not es_de_pruebas("src/modulo/a.py")
    assert not es_de_pruebas("tests.py")


def test_cuenta_las_lineas_con_contenido():
    assert lineas_no_vacias("a = 1\n\n   \nb = 2\n") == 2


def test_cuenta_las_sentencias_global():
    assert contar_sentencias_global(_arbol("def f():\n    global a\n    a = 1\n")) == 1
    assert contar_sentencias_global(_arbol("a = 1\n")) == 0


def test_solo_cuenta_los_nombres_con_un_guion_bajo():
    assert contar_nombres_privados(_arbol("from x import _y, z\n")) == 1
    assert contar_nombres_privados(_arbol("from x import __version__\n")) == 0
    assert contar_nombres_privados(_arbol("import _x\n")) == 0


@pytest.mark.parametrize(
    ("codigo", "esperado"),
    [
        ("a = open('x')\n", 1),
        ("a = ruta.open()\n", 1),
        ("a = sqlite3.connect('x')\n", 1),
        ("a = urlopen('x')\n", 1),
        ("a = socket.socket()\n", 1),
        ("with open('x') as a:\n    pass\n", 0),
        ("with ruta.open() as a:\n    pass\n", 0),
        ("with closing(sqlite3.connect('x')) as a:\n    pass\n", 0),
        ("a = cerrar('x')\n", 0),
    ],
)
def test_cuenta_los_recursos_fuera_de_with(codigo, esperado):
    assert contar_recursos_sin_with(_arbol(codigo)) == esperado


def test_un_recurso_abierto_dentro_del_cuerpo_de_un_with_cuenta():
    codigo = "with bloqueo:\n    a = open('x')\n"
    assert contar_recursos_sin_with(_arbol(codigo)) == 1


@pytest.mark.parametrize(
    ("codigo", "esperado"),
    [
        ("datetime.now()\n", 1),
        ("datetime.utcnow()\n", 1),
        ("date.today()\n", 1),
        ("time.time()\n", 1),
        ("time.sleep(1)\n", 1),
        ("from time import sleep\nsleep(1)\n", 1),
        ("random.randint(1, 2)\n", 1),
        ("from random import randint\nrandint(1, 2)\n", 1),
        ("random.seed(1)\n", 0),
        ("uuid.uuid4()\n", 1),
        ("uuid4()\n", 1),
        ("os.urandom(4)\n", 1),
        ("secrets.token_hex()\n", 1),
        ("date(2026, 1, 1)\n", 0),
        ("time.strftime('%Y')\n", 0),
        ("now()\n", 0),
    ],
)
def test_cuenta_los_usos_no_deterministas(codigo, esperado):
    assert contar_no_deterministas(_arbol(codigo)) == esperado


def test_cuenta_las_pruebas_que_esperan_un_rechazo():
    codigo = """
def test_lanza():
    with pytest.raises(ValueError):
        f()

def test_lanza_con_raises_importado():
    with raises(ValueError):
        f()

def test_http():
    assert cliente.get("/").status_code == 404

def test_http_correcto():
    assert cliente.get("/").status_code == 200

def test_normal():
    assert f() == 1

def ayudante():
    with pytest.raises(ValueError):
        f()
"""
    assert contar_pruebas(_arbol(codigo)) == (5, 3)


def test_calcula_la_complejidad_de_cada_funcion():
    codigo = {
        "a.py": "def f(x):\n    if x:\n        return 1\n    return 2\n",
        "src/b.py": "def g():\n    return 1\n",
    }
    assert sorted(complejidades(codigo)) == [1, 2]


def test_mide_una_implementacion_sin_mezclar_codigo_y_pruebas():
    archivos = {
        "src/__init__.py": "",
        "src/dinero.py": (
            "from x import _y\n"
            "\n"
            "def total(precio: float) -> None:\n"
            "    global contador\n"
            "    contador = open('a')\n"
        ),
        "tests/test_a.py": (
            "def test_a():\n"
            "    assert date.today()\n"
            "\n"
            "def test_b():\n"
            "    with pytest.raises(ValueError):\n"
            "        f()\n"
        ),
    }
    assert medir(archivos) == Metricas(
        usos_float_monetario=1,
        credenciales=0,
        complejidad_media=1.0,
        complejidad_maxima=1,
        nombres_privados=1,
        sentencias_global=1,
        recursos_sin_with=1,
        no_deterministas=1,
        pruebas_de_rechazo=1,
        funciones_de_prueba=2,
        modulos=1,
        lineas_codigo=4,
        lineas_pruebas=5,
    )


def test_las_pruebas_no_cuentan_como_codigo():
    archivos = {"tests/test_a.py": "def test_a():\n    global a\n    a = open('x')\n"}
    metricas = medir(archivos)
    assert metricas.sentencias_global == 0
    assert metricas.recursos_sin_with == 0
    assert metricas.funciones_de_prueba == 1


def test_detecta_una_credencial_en_el_codigo_y_no_en_las_pruebas():
    secreto = "clave_api = 'sk-abcdefghijklmnopqrstuvwxyz123456'\n"
    assert medir({"src/a.py": secreto}).credenciales == 1
    assert medir({"tests/a.py": secreto}).credenciales == 0


def test_la_proporcion_de_rechazo_sin_pruebas_es_cero():
    assert medir({"src/a.py": "a = 1\n"}).proporcion_de_rechazo == 0.0
    assert medir({"tests/a.py": "def test_a():\n    pytest.raises(E)\n"}).proporcion_de_rechazo == 1


def test_lee_solo_los_archivos_python(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("a = 1\n", encoding="utf-8")
    (tmp_path / "USO.md").write_text("uso\n", encoding="utf-8")
    assert leer_archivos(tmp_path) == {"src/a.py": "a = 1\n"}
