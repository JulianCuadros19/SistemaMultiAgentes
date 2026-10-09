"""Tester determinístico con Docker real sobre el corpus de defectos: N11, N12 y N14 sin modelo.

Sin juez, N14 dictamina solo lo verificable en código. Los 13 defectos determinísticos deben
rechazarse con su regla y los controles aprobarse. Los 3 defectos que solo ve el juez pasan sin
él, y eso muestra para qué está. También recorre el ciclo N10–N15 del grafo con el tester real.

Requiere Docker y la imagen del entorno aislado:
`pytest -m sandbox tests/integracion/test_tester_sandbox.py`.
"""

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from multiagente.agentes.tester.analisis import analizar_version
from multiagente.agentes.tester.ejecucion import ejecutar_version
from multiagente.agentes.tester.reglas import cargar_reglas_calidad
from multiagente.agentes.tester.servicio import AgenteTester
from multiagente.agentes.tester.veredicto import dictaminar_version
from multiagente.core.configuracion import ConfiguracionOrquestador, ConfiguracionTester
from multiagente.interfaces.defectos import cargar_corpus_de_defectos
from multiagente.orquestador.ejecucion import avanzar, configuracion_hilo, iniciar_sesion
from multiagente.orquestador.estado import (
    CasoPrueba,
    Contexto,
    Requerimientos,
    Validacion,
    Veredicto,
    VersionCodigo,
)
from multiagente.orquestador.grafo import construir_grafo
from multiagente.orquestador.servicios import Servicios
from multiagente.orquestador.simulacion import (
    ArquitectoFijo,
    DesarrolladorFijo,
    ElicitadorFijo,
    aprobar,
)
from multiagente.persistencia.puntos_control import serializador
from multiagente.rag.colecciones import Agente
from multiagente.rag.recuperacion import ResultadoRecuperacion

pytestmark = pytest.mark.sandbox

REGLAS = cargar_reglas_calidad()
CORPUS = cargar_corpus_de_defectos()
VARIANTES = [(corpus, variante) for corpus in CORPUS for variante in corpus.variantes()]


def plan_de(requerimientos: Requerimientos) -> tuple[CasoPrueba, ...]:
    return tuple(
        CasoPrueba(
            id=f"CP-{r.id_requerimiento}-{e.id}",
            id_requerimiento=r.id_requerimiento,
            id_escenario=e.id,
            dado_que=e.dado_que,
            cuando=e.cuando,
            entonces=e.entonces,
        )
        for r in requerimientos.requerimientos
        for e in r.criterios_aceptacion
    )


@pytest.mark.parametrize(("corpus", "variante"), VARIANTES, ids=[v.id for _, v in VARIANTES])
def test_tester_sin_juez_sobre_el_corpus(entorno_aislado, corpus, variante):
    caso = corpus.caso
    requerimientos = Requerimientos(
        historias=caso.sintesis.historias, requerimientos=caso.sintesis.requerimientos
    )
    version = VersionCodigo(numero=1, archivos=variante.archivos)
    plan = plan_de(requerimientos)
    ejecucion = ejecutar_version(entorno_aislado, version, caso.especificacion, 120)
    analisis = analizar_version(version, caso.especificacion, requerimientos, REGLAS)
    validacion = Validacion(
        plan_pruebas=plan,
        ejecucion=ejecucion,
        hallazgos=analisis.hallazgos,
        conformidad=analisis.conformidad,
        no_evaluadas=analisis.no_evaluadas,
    )
    dictamen = dictaminar_version(plan, validacion, Contexto(), version, REGLAS, 0, None)
    reglas = {h.regla for h in dictamen.hallazgos}
    print(f"{variante.id}: {dictamen.veredicto.value} · {sorted(reglas)}")

    if variante.es_control:
        assert dictamen.veredicto is Veredicto.APROBADO, dictamen.reporte
        assert dictamen.hallazgos == ()
    elif variante.defecto.solo_juez:
        # Sin el juez, la prueba que pasa sin verificar su escenario no se detecta.
        assert dictamen.veredicto is Veredicto.APROBADO
    else:
        assert dictamen.veredicto is Veredicto.RECHAZADO
        assert set(variante.esperado.reglas) <= reglas, dictamen.reporte


class RecuperadorVacio:
    def recuperar(self, consulta, colecciones=None, k=None):
        return ResultadoRecuperacion(
            agente=Agente.TESTER,
            consulta=consulta,
            colecciones=tuple(colecciones),
            fragmentos=(),
            descartados=(),
        )


def test_ciclo_de_correccion_con_el_tester_real(entorno_aislado):
    corpus = next(c for c in CORPUS if c.nombre == "avaluo")
    variantes = {v.id: v for v in corpus.variantes()}
    desarrollador = DesarrolladorFijo(
        versiones=[variantes["avaluo-D04"].archivos, variantes["avaluo-control"].archivos]
    )
    tester = AgenteTester(
        entorno_aislado,
        RecuperadorVacio(),
        None,
        REGLAS,
        ConfiguracionTester(_env_file=None),
    )
    servicios = Servicios(
        elicitador=ElicitadorFijo(corpus.caso.sintesis),
        arquitecto=ArquitectoFijo(corpus.caso.diseno),
        desarrollador=desarrollador,
        tester=tester,
    )
    app = construir_grafo(servicios, ConfiguracionOrquestador(_env_file=None)).compile(
        checkpointer=InMemorySaver(serde=serializador())
    )
    id_sesion, _ = iniciar_sesion(app, corpus.caso.cliente, corpus.caso.proyecto, "Avalúo")
    avanzar(app, id_sesion, aprobar())
    avance = avanzar(app, id_sesion, aprobar())

    # La versión 1 trae eval: N14 la rechaza y N15 la devuelve a N10; la 2 es la base limpia.
    assert avance.pausa.punto == "final"
    assert avance.pausa.datos["version"] == 2
    assert avance.pausa.datos["veredicto"] == "aprobado"
    estado = app.get_state(configuracion_hilo(id_sesion)).values
    assert estado["control"].iteracion == 2
    atendidos = estado["codigo"].vigente.defectos_atendidos
    assert any(linea.startswith("[CAL-SG-002 · alta]") for linea in atendidos)
    assert "Veredicto: APROBADO" in estado["validacion"].reporte
