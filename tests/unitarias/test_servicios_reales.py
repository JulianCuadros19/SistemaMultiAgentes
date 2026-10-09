"""Fábrica de los servicios con los cuatro agentes reales, sin llamar a ningún servicio externo."""

import pytest

from multiagente.agentes.arquitecto.servicio import AgenteArquitecto
from multiagente.agentes.desarrollador.servicio import AgenteDesarrollador
from multiagente.agentes.elicitador.servicio import AgenteElicitador
from multiagente.agentes.servicios import crear_servicios
from multiagente.agentes.tester.servicio import AgenteTester
from multiagente.llm.traza import RegistroEnMemoria
from multiagente.rag.colecciones import Agente
from multiagente.sandbox.ejecutor import EntornoAislado

MODELOS = {
    "MODELO_N3_DIALOGO": "modelo-n3",
    "MODELO_N5_SINTESIS": "modelo-n5",
    "MODELO_N8_ARQUITECTURA": "modelo-n8",
    "MODELO_N10_GENERACION": "modelo-n10",
    "MODELO_N14_VEREDICTO": "modelo-n14",
}


@pytest.fixture
def servicios(monkeypatch, cliente_falso, vectorizador_prueba):
    for variable, valor in MODELOS.items():
        monkeypatch.setenv(variable, valor)
    conexion = object()
    entorno = EntornoAislado()
    resultado = crear_servicios(
        conexion, RegistroEnMemoria(), cliente_falso(), vectorizador_prueba, entorno
    )
    return resultado, conexion, entorno


def test_crea_los_cuatro_agentes_reales(servicios):
    resultado, conexion, entorno = servicios
    elicitador, arquitecto, tester = resultado.elicitador, resultado.arquitecto, resultado.tester

    assert isinstance(elicitador, AgenteElicitador)
    assert isinstance(arquitecto, AgenteArquitecto)
    assert isinstance(resultado.desarrollador, AgenteDesarrollador)
    assert isinstance(tester, AgenteTester)
    assert tester.entorno is entorno

    # Cada agente que recupera lo hace sobre la misma conexión y solo como él mismo (RF-29).
    for agente, esperado in [
        (elicitador, Agente.ELICITADOR),
        (arquitecto, Agente.ARQUITECTO),
        (tester, Agente.TESTER),
    ]:
        assert agente.recuperador.conexion is conexion
        assert agente.recuperador.agente is esperado


def test_cada_nodo_usa_su_modelo_y_el_mismo_cliente(servicios):
    resultado, _, _ = servicios
    invocadores = {
        "N3": resultado.elicitador.extraccion,
        "N5": resultado.elicitador.sintesis,
        "N8": resultado.arquitecto.seleccion,
        "N10": resultado.desarrollador.generacion,
        "N14": resultado.tester.juez,
    }

    assert {nodo: i.parametros.despliegue for nodo, i in invocadores.items()} == {
        "N3": "modelo-n3",
        "N5": "modelo-n5",
        "N8": "modelo-n8",
        "N10": "modelo-n10",
        "N14": "modelo-n14",
    }
    assert len({id(invocador.cliente) for invocador in invocadores.values()}) == 1


def test_el_desarrollador_no_recibe_recuperador(servicios):
    # Decisión 1: el desarrollador no consulta bases de conocimiento.
    desarrollador = servicios[0].desarrollador
    assert not any(hasattr(desarrollador, nombre) for nombre in ("recuperador", "conexion"))
