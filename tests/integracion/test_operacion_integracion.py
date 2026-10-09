"""Capa de operación con PostgreSQL y con el entorno aislado real, sin modelos de lenguaje.

- `pytest -m integracion`: la lista de sesiones se lee de los puntos de control en PostgreSQL.
- `pytest -m sandbox`: las pruebas propias de la persona corren en el entorno aislado contra el
  módulo base del corpus de defectos (RF-38).
"""

from datetime import date

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from multiagente.core.configuracion import ConfiguracionOrquestador
from multiagente.interfaces.defectos import cargar_corpus_de_defectos
from multiagente.interfaces.operacion import Operador, observaciones_de_pruebas
from multiagente.orquestador.estado import Decision, ResultadoPrueba
from multiagente.orquestador.grafo import construir_grafo
from multiagente.orquestador.servicios import Servicios
from multiagente.orquestador.simulacion import (
    ArquitectoFijo,
    DesarrolladorFijo,
    ElicitadorFijo,
    ServiciosSimulados,
)
from multiagente.persistencia.puntos_control import abrir_checkpointer, serializador

CONFIGURACION = ConfiguracionOrquestador(_env_file=None)


@pytest.mark.integracion
def test_lista_las_sesiones_guardadas_en_postgresql():
    with abrir_checkpointer() as checkpointer:
        simulacion = ServiciosSimulados()
        app = construir_grafo(simulacion.como_servicios(), CONFIGURACION).compile(
            checkpointer=checkpointer
        )
        operador = Operador(app)
        primera = operador.iniciar("Cliente A", "Proyecto", "Registrar mutaciones")
        segunda = operador.iniciar("Cliente B", "Proyecto", "Liquidar el impuesto")
        try:
            sesiones = [vista.id_sesion for vista in operador.sesiones()]
            assert sesiones.index(segunda) < sesiones.index(primera)
            assert operador.vista(segunda).cliente == "Cliente B"
        finally:
            for id_sesion in (primera, segunda):
                checkpointer.delete_thread(id_sesion)


PRUEBA_PROPIA = f"""from decimal import Decimal

import pytest

from aplicacion.calculo_avaluo import calcular_avaluo
from dominio.avaluo import ValoresUnitarios
from infraestructura import valores_unitarios_repositorio as repositorio

NUMERO = "2" * 30


@pytest.fixture
def valores(monkeypatch):
    registros = {{(NUMERO, {date.today().year}): ValoresUnitarios(Decimal("1000"), Decimal("0"))}}
    monkeypatch.setattr(repositorio, "_VALORES_UNITARIOS", registros)


def test_lote_sin_construccion(valores):
    resultado = calcular_avaluo(NUMERO, {date.today().year}, Decimal("50"), Decimal("0"))
    assert resultado.avaluo_total == Decimal("50000")


def test_expectativa_equivocada(valores):
    resultado = calcular_avaluo(NUMERO, {date.today().year}, Decimal("50"), Decimal("0"))
    assert resultado.avaluo_total == Decimal("1")
"""


@pytest.mark.sandbox
def test_las_pruebas_propias_corren_en_el_entorno_aislado(entorno_aislado):
    corpus = next(c for c in cargar_corpus_de_defectos() if c.nombre == "avaluo")
    simulacion = ServiciosSimulados(fallos_veredicto=0)
    servicios = Servicios(
        elicitador=ElicitadorFijo(corpus.caso.sintesis),
        arquitecto=ArquitectoFijo(corpus.caso.diseno),
        desarrollador=DesarrolladorFijo(
            versiones=[next(v for v in corpus.variantes() if v.es_control).archivos]
        ),
        tester=simulacion,
    )
    app = construir_grafo(servicios, CONFIGURACION).compile(
        checkpointer=InMemorySaver(serde=serializador())
    )
    operador = Operador(app, entorno_aislado)
    id_sesion = operador.iniciar(corpus.caso.cliente, corpus.caso.proyecto, "Avalúo")
    operador.decidir(id_sesion, Decision.APROBADO, "Analista")
    operador.decidir(id_sesion, Decision.APROBADO, "Arquitecto")
    assert operador.vista(id_sesion).pausa.punto == "final"

    pruebas = operador.probar_propias(id_sesion, {"tests/test_persona.py": PRUEBA_PROPIA})

    resultados = {p.nombre: p.resultado for p in pruebas.ejecucion.pruebas}
    assert resultados == {
        "test_lote_sin_construccion": ResultadoPrueba.PASO,
        "test_expectativa_equivocada": ResultadoPrueba.FALLO,
    }
    assert pruebas.ejecucion.errores_recoleccion == ()
    assert "test_expectativa_equivocada no pasa (fallo)" in observaciones_de_pruebas(pruebas)
