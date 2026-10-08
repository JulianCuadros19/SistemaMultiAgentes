"""Condición de terminado del paso 4 para el Anexo B: el esquema valida el ejemplo de referencia.

El Anexo B no trae ejemplo; el de referencia está en la plantilla de la base de conocimiento.
"""

import copy
import json
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from multiagente.core.esquemas.especificacion_diseno import EspecificacionDiseno, buscar_ciclo

RAIZ = Path(__file__).resolve().parents[2]
PLANTILLA = RAIZ / "knowledge_base" / "arquitecturas_referencia" / "02-especificacion-de-diseno.md"


def json_de_markdown(ruta: Path) -> dict:
    bloque = re.search(r"```json\n(.*?)\n```", ruta.read_text(encoding="utf-8"), re.S)
    return json.loads(bloque.group(1))


@pytest.fixture
def especificacion() -> dict:
    return json_de_markdown(PLANTILLA)


def agregar_modulo(datos: dict, nombre: str, dependencias: list[str]) -> None:
    modulo = copy.deepcopy(datos["modulos"][0])
    modulo["nombre"] = nombre
    modulo["ruta"] = "src/" + nombre.replace(".", "/") + ".py"
    modulo["dependencias_permitidas"] = dependencias
    datos["modulos"].append(modulo)


def test_ejemplo_de_referencia_del_anexo_b(especificacion):
    validada = EspecificacionDiseno.model_validate(especificacion)
    assert validada.id_especificacion == "ED-003"
    assert validada.arquitectura_base == "ARQ-02"


@pytest.mark.parametrize(
    "campo",
    [
        "id_especificacion",
        "version",
        "arquitectura_base",
        "requerimientos_cubiertos",
        "modulos",
        "modelo_datos",
        "dependencias_externas",
        "reglas_de_dependencia",
    ],
)
def test_rechaza_campo_obligatorio_faltante(especificacion, campo):
    del especificacion[campo]
    with pytest.raises(ValidationError, match=campo):
        EspecificacionDiseno.model_validate(especificacion)


@pytest.mark.parametrize(
    "campo", ["modelo_datos", "dependencias_externas", "reglas_de_dependencia"]
)
def test_acepta_listas_obligatorias_vacias(especificacion, campo):
    especificacion[campo] = []
    EspecificacionDiseno.model_validate(especificacion)


def test_dependencias_permitidas_omitidas_valen_ninguna(especificacion):
    del especificacion["modulos"][0]["dependencias_permitidas"]
    validada = EspecificacionDiseno.model_validate(especificacion)
    assert validada.modulos[0].dependencias_permitidas == []


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("id_especificacion", "CD-003"),
        ("arquitectura_base", "ARQ-7"),
        ("requerimientos_cubiertos", []),
        ("modulos", []),
    ],
)
def test_rechaza_valor_invalido(especificacion, campo, valor):
    especificacion[campo] = valor
    with pytest.raises(ValidationError):
        EspecificacionDiseno.model_validate(especificacion)


def test_modulo_sin_interfaces(especificacion):
    especificacion["modulos"][0]["interfaces_publicas"] = []
    with pytest.raises(ValidationError, match="interfaces_publicas"):
        EspecificacionDiseno.model_validate(especificacion)


def test_tipo_de_interfaz_desconocido(especificacion):
    especificacion["modulos"][0]["interfaces_publicas"][0]["tipo"] = "macro"
    with pytest.raises(ValidationError):
        EspecificacionDiseno.model_validate(especificacion)


def test_ruta_que_no_es_archivo_python(especificacion):
    especificacion["modulos"][0]["ruta"] = "src/dominio/predio.txt"
    with pytest.raises(ValidationError):
        EspecificacionDiseno.model_validate(especificacion)


def test_dependencia_a_modulo_no_declarado(especificacion):
    especificacion["modulos"][0]["dependencias_permitidas"] = ["infraestructura.base_datos"]
    with pytest.raises(ValidationError, match="no declarados"):
        EspecificacionDiseno.model_validate(especificacion)


def test_dependencias_circulares(especificacion):
    especificacion["modulos"][0]["dependencias_permitidas"] = ["aplicacion.avaluo"]
    agregar_modulo(especificacion, "aplicacion.avaluo", ["dominio.predio"])
    with pytest.raises(ValidationError, match="circulares"):
        EspecificacionDiseno.model_validate(especificacion)


def test_dependencia_de_un_modulo_consigo_mismo(especificacion):
    especificacion["modulos"][0]["dependencias_permitidas"] = ["dominio.predio"]
    with pytest.raises(ValidationError, match="circulares"):
        EspecificacionDiseno.model_validate(especificacion)


def test_dependencias_en_cadena_sin_ciclo(especificacion):
    agregar_modulo(especificacion, "aplicacion.avaluo", ["dominio.predio"])
    agregar_modulo(especificacion, "interfaces.cli", ["aplicacion.avaluo", "dominio.predio"])
    EspecificacionDiseno.model_validate(especificacion)


def test_requerimiento_de_modulo_no_cubierto(especificacion):
    especificacion["modulos"][0]["requerimientos"] = ["RF-099"]
    with pytest.raises(ValidationError, match="RF-099"):
        EspecificacionDiseno.model_validate(especificacion)


def test_modulos_repetidos(especificacion):
    especificacion["modulos"].append(copy.deepcopy(especificacion["modulos"][0]))
    with pytest.raises(ValidationError, match="repetid"):
        EspecificacionDiseno.model_validate(especificacion)


def test_buscar_ciclo_devuelve_el_recorrido():
    ciclo = buscar_ciclo({"a": ["b"], "b": ["c"], "c": ["a"], "d": []})
    assert ciclo == ["a", "b", "c", "a"]
    assert buscar_ciclo({"a": ["b"], "b": [], "c": ["a", "b"]}) is None
