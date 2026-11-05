"""Empaquetado del sistema en contenedores (paso 14, ADR-0017), sin Docker.

Lee la composición, las imágenes y `.dockerignore` y protege lo que promete la entrega:
- nada se publica fuera de la máquina;
- la aplicación recibe las direcciones internas y arranca con la base, el corpus y el entorno
  aislado listos;
- los secretos y los datos locales no entran en la imagen;
- cada imagen queda fijada por versión y digest, con las dependencias con que pasan las pruebas.
"""

import re
import sys
import tomllib
from pathlib import Path

import pytest
import yaml
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from multiagente.core.configuracion import ConfiguracionSandbox

RAIZ = Path(__file__).resolve().parents[2]
SERVICIOS = yaml.safe_load((RAIZ / "docker-compose.yml").read_text(encoding="utf-8"))["services"]
DOCKERFILES = sorted((RAIZ / "docker").glob("*/Dockerfile"))
IMAGEN_FIJADA = re.compile(r"[\w.\-/]+:[\w.\-]+@sha256:[0-9a-f]{64}")
SOCKET = "/var/run/docker.sock:/var/run/docker.sock"


def test_ningun_puerto_se_publica_fuera_de_la_maquina():
    publicados = {nombre: s["ports"] for nombre, s in SERVICIOS.items() if "ports" in s}
    assert set(publicados) == {"db", "embeddings", "aplicacion"}
    for nombre, puertos in publicados.items():
        for puerto in puertos:
            assert puerto.startswith("127.0.0.1:"), (nombre, puerto)


@pytest.mark.parametrize("servicio", ["aplicacion", "ingesta"])
def test_la_aplicacion_usa_las_direcciones_internas_de_la_composicion(servicio):
    configuracion = SERVICIOS[servicio]
    assert configuracion["env_file"] == ".env"
    assert configuracion["environment"] == {
        "POSTGRES_HOST": "db",
        "POSTGRES_PORT": "5432",
        "EMBEDDINGS_URL": "http://embeddings:80",
        "INTERFAZ_HOST_WEB": "0.0.0.0",
        "INTERFAZ_PUERTO_WEB": "8000",
    }


def test_la_web_escucha_en_el_contenedor_y_se_publica_solo_en_la_maquina():
    aplicacion = SERVICIOS["aplicacion"]
    assert aplicacion["command"] == ["multiagente", "web"]
    assert aplicacion["ports"] == ["127.0.0.1:${INTERFAZ_PUERTO_WEB:-8000}:8000"]
    assert "./data/local:/app/data/local" in aplicacion["volumes"]


def test_la_aplicacion_arranca_con_la_base_el_corpus_y_el_entorno_aislado_listos():
    assert SERVICIOS["aplicacion"]["depends_on"] == {
        "db": {"condition": "service_healthy"},
        "embeddings": {"condition": "service_healthy"},
        "ingesta": {"condition": "service_completed_successfully"},
        "sandbox": {"condition": "service_completed_successfully"},
    }
    assert SERVICIOS["ingesta"]["command"] == ["python", "scripts/ingestar_conocimiento.py"]


def test_solo_la_aplicacion_alcanza_el_docker_del_anfitrion():
    con_socket = {n for n, s in SERVICIOS.items() if SOCKET in s.get("volumes", [])}
    assert con_socket == {"aplicacion"}


def test_la_composicion_construye_la_imagen_que_usa_el_entorno_aislado():
    sandbox = SERVICIOS["sandbox"]
    assert sandbox["image"] == ConfiguracionSandbox.model_fields["imagen"].default
    assert sandbox["network_mode"] == "none"
    assert sandbox["read_only"] is True


def test_los_secretos_y_los_datos_locales_no_entran_en_la_imagen():
    lineas = (RAIZ / ".dockerignore").read_text(encoding="utf-8").splitlines()
    ignorados = {linea.strip() for linea in lineas if linea.strip() and not linea.startswith("#")}
    assert {
        ".env",
        ".env.*",
        ".venv/",
        ".git/",
        "data/",
        "docs/anexos/",
        "evaluacion/resultados/",
    } <= ignorados


@pytest.mark.parametrize("dockerfile", DOCKERFILES, ids=lambda ruta: ruta.parent.name)
def test_cada_imagen_base_tiene_version_y_digest(dockerfile):
    bases = re.findall(r"^FROM\s+(\S+)", dockerfile.read_text(encoding="utf-8"), re.MULTILINE)
    assert bases
    for base in bases:
        assert IMAGEN_FIJADA.fullmatch(base), base


def test_cada_imagen_descargada_de_la_composicion_tiene_version_y_digest():
    descargadas = {n: s["image"] for n, s in SERVICIOS.items() if "build" not in s}
    assert set(descargadas) == {"db", "descarga-modelo", "embeddings"}
    for nombre, imagen in descargadas.items():
        assert IMAGEN_FIJADA.fullmatch(imagen), nombre


def test_la_imagen_usa_la_version_de_python_de_las_pruebas():
    texto = (RAIZ / "docker" / "aplicacion" / "Dockerfile").read_text(encoding="utf-8")
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    assert re.search(rf"^FROM python:{re.escape(version)}\.\d+-slim", texto, re.MULTILINE)


def test_las_versiones_congeladas_cubren_cada_dependencia_del_sistema():
    texto = (RAIZ / "docker" / "aplicacion" / "versiones.txt").read_text(encoding="utf-8")
    congeladas = dict(
        linea.split("==", 1) for linea in texto.splitlines() if linea and not linea.startswith("#")
    )
    congeladas = {canonicalize_name(nombre): version for nombre, version in congeladas.items()}
    proyecto = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    for dependencia in proyecto["dependencies"]:
        requisito = Requirement(dependencia)
        version = congeladas.get(canonicalize_name(requisito.name))
        assert version is not None, requisito.name
        assert requisito.specifier.contains(version), (requisito.name, version)
