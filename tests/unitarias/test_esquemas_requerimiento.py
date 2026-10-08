"""Condición de terminado del paso 4 para el Anexo A: los esquemas validan sus ejemplos."""

import copy
import json
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from multiagente.core.esquemas.requerimiento import BacklogHistorias, RequerimientoFormal

RAIZ = Path(__file__).resolve().parents[2]
DATOS = RAIZ / "tests" / "datos" / "anexos"
PLANTILLA = RAIZ / "knowledge_base" / "elicitacion" / "03-plantilla-requerimiento-funcional.md"


def cargar_ejemplo(nombre: str) -> dict:
    datos = json.loads((DATOS / nombre).read_text(encoding="utf-8"))
    datos.pop("_fuente")
    return datos


def json_de_markdown(ruta: Path) -> dict:
    bloque = re.search(r"```json\n(.*?)\n```", ruta.read_text(encoding="utf-8"), re.S)
    return json.loads(bloque.group(1))


def test_backlog_del_anexo_a():
    backlog = BacklogHistorias.model_validate(cargar_ejemplo("anexo_a_backlog.json"))
    assert len(backlog.historias) == 11
    assert backlog.historias[0].enunciado.como == "Profesor"


def test_rf27_del_anexo_a():
    requerimiento = RequerimientoFormal.model_validate(cargar_ejemplo("anexo_a_rf27.json"))
    assert requerimiento.id_requerimiento == "RF-27"
    assert [escenario.id for escenario in requerimiento.criterios_aceptacion] == [
        "ESC-01",
        "ESC-02",
        "ESC-03",
    ]


def test_ejemplo_de_la_plantilla_de_la_base_de_conocimiento():
    requerimiento = RequerimientoFormal.model_validate(json_de_markdown(PLANTILLA))
    assert requerimiento.id_requerimiento == "RF-014"


@pytest.fixture
def rf27() -> dict:
    return cargar_ejemplo("anexo_a_rf27.json")


@pytest.mark.parametrize(
    "campo", ["proyecto", "tipo_solicitud", "impacto", "autor", "area_funcional", "titulo"]
)
def test_rechaza_campo_obligatorio_faltante(rf27, campo):
    del rf27[campo]
    with pytest.raises(ValidationError, match=campo):
        RequerimientoFormal.model_validate(rf27)


@pytest.mark.parametrize(
    "campo", ["riesgo", "funcional_responsable", "requerimientos_relacionados"]
)
def test_acepta_campo_opcional_faltante(rf27, campo):
    del rf27[campo]
    RequerimientoFormal.model_validate(rf27)


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("tipo_solicitud", "Nuevo"),
        ("impacto", "critico"),
        ("prioridad", "urgente"),
        ("id_requerimiento", "RQ-27"),
        ("version", "uno"),
        ("autor", "   "),
    ],
)
def test_rechaza_valor_invalido(rf27, campo, valor):
    rf27[campo] = valor
    with pytest.raises(ValidationError):
        RequerimientoFormal.model_validate(rf27)


def test_rechaza_campo_no_declarado(rf27):
    rf27["estado"] = "aprobado"
    with pytest.raises(ValidationError, match="estado"):
        RequerimientoFormal.model_validate(rf27)


def test_exige_al_menos_un_escenario(rf27):
    rf27["criterios_aceptacion"] = []
    with pytest.raises(ValidationError, match="criterios_aceptacion"):
        RequerimientoFormal.model_validate(rf27)


def test_rechaza_escenarios_repetidos(rf27):
    rf27["criterios_aceptacion"][1]["id"] = "ESC-01"
    with pytest.raises(ValidationError, match="ESC-01"):
        RequerimientoFormal.model_validate(rf27)


def test_rechaza_autorreferencia(rf27):
    rf27["requerimientos_relacionados"].append("RF-27")
    with pytest.raises(ValidationError, match="consigo mismo"):
        RequerimientoFormal.model_validate(rf27)


def test_rechaza_datos_de_entrada_repetidos(rf27):
    entrada = rf27["descripcion"]["datos_entrada"]
    entrada.append(copy.deepcopy(entrada[0]))
    with pytest.raises(ValidationError, match="veredicto_por_criterio"):
        RequerimientoFormal.model_validate(rf27)


def test_rechaza_historias_repetidas():
    backlog = cargar_ejemplo("anexo_a_backlog.json")
    backlog["historias"][1]["id"] = "HU-01"
    with pytest.raises(ValidationError, match="HU-01"):
        BacklogHistorias.model_validate(backlog)


def test_rechaza_historia_sin_beneficio():
    backlog = cargar_ejemplo("anexo_a_backlog.json")
    del backlog["historias"][0]["enunciado"]["para"]
    with pytest.raises(ValidationError, match="para"):
        BacklogHistorias.model_validate(backlog)
