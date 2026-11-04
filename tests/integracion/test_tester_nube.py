"""Condición de terminado del paso 10: el tester detecta los defectos inyectados a propósito.

Sobre cada variante del corpus (`evaluacion/defectos/`), el tester completo dictamina:
- N11 en el entorno aislado;
- N12 con Ruff y la conformidad;
- N13 con BGE-M3;
- N14 con el juez de MODELO_N14_VEREDICTO.

Cada defecto debe salir rechazado y con su regla, y cada control aprobado sin hallazgos. El juez
debe marcar exactamente los casos cuyas pruebas no verifican su escenario, sin rechazos falsos
ocultos tras un hallazgo determinístico. También recorre el ciclo N10–N15 del grafo con el tester
real.

Cuesta dinero y requiere el archivo .env, los servicios `db` y `embeddings` y la imagen del
entorno aislado:
`pytest -m "nube and embeddings and sandbox" tests/integracion/test_tester_nube.py`.
"""

from decimal import Decimal

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from multiagente.agentes.tester.servicio import crear_agente_tester
from multiagente.core.configuracion import ConfiguracionAzureOpenAI, ConfiguracionOrquestador
from multiagente.interfaces.defectos import cargar_corpus_de_defectos
from multiagente.llm.cliente import crear_cliente
from multiagente.llm.traza import RegistroEnMemoria
from multiagente.orquestador.ejecucion import avanzar, configuracion_hilo, iniciar_sesion
from multiagente.orquestador.estado import (
    CasoPrueba,
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

pytestmark = [pytest.mark.nube, pytest.mark.embeddings, pytest.mark.sandbox]

CORPUS = cargar_corpus_de_defectos()
VARIANTES = [(corpus, variante) for corpus in CORPUS for variante in corpus.variantes()]


@pytest.fixture(scope="module")
def tester(base_real, vectorizador, entorno_aislado):
    registro = RegistroEnMemoria()
    agente = crear_agente_tester(
        base_real,
        registro,
        crear_cliente(ConfiguracionAzureOpenAI()),
        vectorizador,
        entorno_aislado,
    )
    yield agente
    costo = sum((llamada.costo_usd for llamada in registro.llamadas), Decimal(0))
    print(f"\nJuez: {len(registro.llamadas)} llamadas · USD {costo:.5f}")


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
def test_el_tester_detecta_cada_defecto_y_aprueba_los_controles(tester, corpus, variante):
    caso = corpus.caso
    requerimientos = Requerimientos(
        historias=caso.sintesis.historias, requerimientos=caso.sintesis.requerimientos
    )
    version = VersionCodigo(numero=1, archivos=variante.archivos)
    plan = plan_de(requerimientos)
    ejecucion = tester.ejecutar(version, caso.especificacion)
    analisis = tester.analizar(version, caso.especificacion, requerimientos)
    validacion = Validacion(
        plan_pruebas=plan,
        ejecucion=ejecucion,
        hallazgos=analisis.hallazgos,
        conformidad=analisis.conformidad,
        no_evaluadas=analisis.no_evaluadas,
    )
    contexto = tester.recuperar_criterios(validacion)
    dictamen = tester.dictaminar(plan, validacion, contexto, version, caso.especificacion)
    reglas = {h.regla for h in dictamen.hallazgos}
    print(f"{variante.id}: {dictamen.veredicto.value} · {sorted(reglas)}")

    # El juez marca exactamente los casos cuyas pruebas no verifican su escenario: ningún otro.
    juzgados = [v for v in dictamen.veredictos if " pasan. " in v.evidencia]
    marcados = {v.id_caso for v in juzgados if not v.cumple}
    assert marcados == set(variante.esperado.casos_juez), dictamen.reporte

    # N13 solo recupera de criterios_calidad (RF-29).
    assert set(contexto.fragmentos) == {"criterios_calidad"}
    if variante.es_control:
        assert dictamen.veredicto is Veredicto.APROBADO, dictamen.reporte
        assert dictamen.hallazgos == ()
    else:
        assert dictamen.veredicto is Veredicto.RECHAZADO, dictamen.reporte
        assert set(variante.esperado.reglas) <= reglas, dictamen.reporte


def test_ciclo_de_correccion_con_el_tester_completo(tester):
    corpus = next(c for c in CORPUS if c.nombre == "avaluo")
    variantes = {v.id: v for v in corpus.variantes()}
    desarrollador = DesarrolladorFijo(
        versiones=[variantes["avaluo-J01"].archivos, variantes["avaluo-control"].archivos]
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

    # La versión 1 debilita la aserción del ESC-01: el juez la rechaza; la 2 es la base limpia.
    assert avance.pausa.punto == "final"
    assert avance.pausa.datos["version"] == 2
    assert avance.pausa.datos["veredicto"] == "aprobado"
    estado = app.get_state(configuracion_hilo(id_sesion)).values
    atendidos = estado["codigo"].vigente.defectos_atendidos
    assert any(linea.startswith("[CAL-FS-001 · alta]") for linea in atendidos)
