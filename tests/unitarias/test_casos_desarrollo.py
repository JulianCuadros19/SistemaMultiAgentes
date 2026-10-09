"""Casos de desarrollo y arquitecto fijo: diseños aprobados que llegan a N10 sin diseñar."""

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import ValidationError

from multiagente.agentes.arquitecto.catalogo import (
    cargar_catalogo_tecnologico,
    titulos_del_catalogo,
)
from multiagente.agentes.arquitecto.validacion import validar_especificacion
from multiagente.core.configuracion import ConfiguracionOrquestador
from multiagente.interfaces.casos import (
    CasoDesarrollo,
    cargar_caso_desarrollo,
    cargar_caso_diseno,
    exportar_caso_desarrollo,
)
from multiagente.interfaces.cliente_simulado import RAIZ_EVALUACION
from multiagente.orquestador.ejecucion import avanzar, configuracion_hilo, iniciar_sesion
from multiagente.orquestador.estado import Arquitectura, Contexto, Requerimientos
from multiagente.orquestador.grafo import Nodo, construir_grafo
from multiagente.orquestador.servicios import Servicios
from multiagente.orquestador.simulacion import (
    ArquitectoFijo,
    ElicitadorFijo,
    ServiciosSimulados,
    aprobar,
)
from multiagente.persistencia.puntos_control import serializador

CASOS = sorted((RAIZ_EVALUACION / "casos").glob("desarrollo-*.json"))


def test_hay_un_caso_de_desarrollo_por_caso_de_diseno():
    disenos = {
        c.stem.removeprefix("diseno-") for c in (RAIZ_EVALUACION / "casos").glob("diseno-*.json")
    }
    assert {caso.stem.removeprefix("desarrollo-") for caso in CASOS} == disenos


@pytest.mark.parametrize("archivo", CASOS, ids=[caso.stem for caso in CASOS])
def test_el_diseno_del_caso_pasa_el_anexo_b(archivo):
    caso = cargar_caso_desarrollo(archivo)
    requerimientos = Requerimientos(
        historias=caso.sintesis.historias, requerimientos=caso.sintesis.requerimientos
    )
    errores = validar_especificacion(
        caso.especificacion,
        requerimientos,
        cargar_catalogo_tecnologico(),
        frozenset(titulos_del_catalogo()),
    )
    assert errores == []
    assert caso.especificacion.arquitectura_base in caso.candidatas
    assert caso.id.startswith("caso-desarrollo-")


def test_exportar_conserva_el_caso_y_agrega_el_diseno(tmp_path):
    caso = cargar_caso_diseno(RAIZ_EVALUACION / "casos" / "diseno-avaluo.json")
    diseno = ServiciosSimulados().disenar(
        Requerimientos(requerimientos=caso.sintesis.requerimientos), Contexto(), Arquitectura()
    )
    destino = tmp_path / "desarrollo-avaluo.json"
    exportado = exportar_caso_desarrollo(caso, diseno, destino)
    assert exportado.id == "caso-desarrollo-avaluo"
    assert cargar_caso_desarrollo(destino) == exportado
    assert exportado.diseno == diseno


def test_la_especificacion_debe_cubrir_los_requerimientos_del_caso():
    caso = cargar_caso_desarrollo(CASOS[0])
    datos = caso.model_dump(mode="json")
    datos["especificacion"]["requerimientos_cubiertos"] = ["RF-99"]
    for modulo in datos["especificacion"]["modulos"]:
        modulo["requerimientos"] = ["RF-99"]
    with pytest.raises(ValidationError, match="exactamente los requerimientos del caso"):
        CasoDesarrollo.model_validate(datos)


def test_arquitecto_fijo_lleva_la_sesion_hasta_n10():
    caso = cargar_caso_desarrollo(CASOS[0])
    simulados = ServiciosSimulados(fallos_veredicto=0)
    servicios = Servicios(
        elicitador=ElicitadorFijo(caso.sintesis),
        arquitecto=ArquitectoFijo(caso.diseno),
        desarrollador=simulados,
        tester=simulados,
    )
    app = construir_grafo(servicios, ConfiguracionOrquestador(_env_file=None)).compile(
        checkpointer=InMemorySaver(serde=serializador())
    )
    id_sesion, _ = iniciar_sesion(app, caso.cliente, caso.proyecto, caso.necesidad)
    avanzar(app, id_sesion, aprobar())
    avance = avanzar(app, id_sesion, aprobar())
    assert Nodo.N10 in avance.nodos
    arquitectura = app.get_state(configuracion_hilo(id_sesion)).values["arquitectura"]
    assert arquitectura.especificacion == caso.especificacion
