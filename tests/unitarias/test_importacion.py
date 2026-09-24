"""Prueba de humo del paso 1: el paquete multiagente y sus subpaquetes se importan."""

import importlib
import importlib.metadata

import pytest

import multiagente

SUBPAQUETES = [
    "multiagente.agentes",
    "multiagente.agentes.elicitador",
    "multiagente.agentes.arquitecto",
    "multiagente.agentes.desarrollador",
    "multiagente.agentes.tester",
    "multiagente.core",
    "multiagente.core.esquemas",
    "multiagente.interfaces",
    "multiagente.llm",
    "multiagente.observabilidad",
    "multiagente.orquestador",
    "multiagente.persistencia",
    "multiagente.rag",
]


def test_version_coincide_con_metadatos_instalados():
    assert multiagente.__version__ == importlib.metadata.version("multiagente")


@pytest.mark.parametrize("nombre", SUBPAQUETES)
def test_subpaquete_se_importa_y_esta_documentado(nombre):
    modulo = importlib.import_module(nombre)
    assert modulo.__doc__
