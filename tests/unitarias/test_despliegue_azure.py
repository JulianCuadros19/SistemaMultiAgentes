"""Despliegue de demostración en Azure (ADR-0020): lo expuesto hacia afuera, sin Docker ni red."""

import re
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2]
AZURE = yaml.safe_load((RAIZ / "docker-compose.azure.yml").read_text(encoding="utf-8"))
BASE = yaml.safe_load((RAIZ / "docker-compose.yml").read_text(encoding="utf-8"))
SERVICIOS = AZURE["services"]
CADDYFILE = (RAIZ / "docker" / "proxy" / "Caddyfile").read_text(encoding="utf-8")
IMAGEN_FIJADA = re.compile(r"[\w.\-/]+:[\w.\-]+@sha256:[0-9a-f]{64}")


def test_solo_el_proxy_publica_puertos_hacia_afuera():
    assert SERVICIOS["proxy"]["ports"] == ["80:80", "443:443"]
    for nombre, servicio in SERVICIOS.items():
        if nombre != "proxy":
            assert "ports" not in servicio, nombre
    for nombre, servicio in BASE["services"].items():
        for puerto in servicio.get("ports", []):
            assert puerto.startswith("127.0.0.1:"), nombre


def test_el_proxy_no_alcanza_el_docker_del_anfitrion():
    assert not any("docker.sock" in volumen for volumen in SERVICIOS["proxy"]["volumes"])


def test_la_imagen_del_proxy_tiene_version_y_digest():
    assert IMAGEN_FIJADA.fullmatch(SERVICIOS["proxy"]["image"])


def test_el_proxy_exige_contrasena_y_solo_llega_a_la_web():
    assert "basic_auth" in CADDYFILE
    assert "{$WEB_CLAVE_HASH}" in CADDYFILE
    assert re.findall(r"reverse_proxy\s+(\S+)", CADDYFILE) == ["aplicacion:8000"]


def test_los_secretos_del_proxy_no_se_versionan_ni_entran_en_la_imagen():
    assert SERVICIOS["proxy"]["env_file"] == ".env.azure"
    gitignore = (RAIZ / ".gitignore").read_text(encoding="utf-8").splitlines()
    dockerignore = (RAIZ / ".dockerignore").read_text(encoding="utf-8").splitlines()
    assert ".env.azure" in gitignore
    assert ".env.*" in dockerignore


def test_una_sesion_publica_tiene_un_presupuesto_menor_que_el_de_la_entrega():
    entorno = SERVICIOS["aplicacion"]["environment"]
    assert float(entorno["PRESUPUESTO_MAXIMO_POR_MODULO_USD"]) <= 1.0
