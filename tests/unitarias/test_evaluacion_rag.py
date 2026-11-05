"""Métricas RAGs del paso 15 sobre sesiones simuladas y un juez falso (ADR-0019)."""

import json

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from multiagente.core.configuracion import ConfiguracionOrquestador
from multiagente.evaluacion.rag import (
    AGENTE_DE_COLECCION,
    NODO_JUEZ,
    RUTA_PROMPT,
    FragmentoRecuperado,
    MuestraRag,
    SalidaJuezRag,
    calcular_metricas,
    coseno,
    evaluar_muestra,
    muestras_de_sesion,
    resumen_por_coleccion,
)
from multiagente.interfaces.operacion import Operador
from multiagente.llm.invocador import InvocadorNodo, ParametrosNodo
from multiagente.llm.prompts import leer_prompt
from multiagente.llm.traza import RegistroEnMemoria
from multiagente.orquestador.estado import Decision, FragmentoContexto
from multiagente.orquestador.grafo import construir_grafo
from multiagente.orquestador.simulacion import ServiciosSimulados, guion_completo
from multiagente.persistencia.puntos_control import serializador


def fragmento(titulo, contenido):
    return FragmentoContexto(
        documento_id="eli-001",
        version_documento="1.0",
        titulo=titulo,
        contenido=contenido,
        similitud=0.8,
    )


MUESTRA = MuestraRag(
    sesion="s-1",
    agente="elicitador",
    consulta="Registrar las mutaciones de propietario de un predio",
    fragmentos=(
        FragmentoRecuperado(
            "elicitacion",
            fragmento("Preguntas de reglas", "Pregunte por las reglas y sus excepciones."),
        ),
        FragmentoRecuperado(
            "dominio_negocio", fragmento("Glosario", "Un predio es un inmueble con número predial.")
        ),
    ),
    entradas="cliente: Necesitamos registrar las mutaciones",
    artefacto="RF-01: la solicitud se acepta solo si el predio existe.",
)
JUICIO = {
    "afirmaciones": [
        {
            "texto": "La solicitud exige que el predio exista.",
            "sustentada": True,
            "fuente": "entradas",
        },
        {"texto": "El predio tiene número predial.", "sustentada": True, "fuente": "F2"},
        {"texto": "La mutación se aprueba en 3 días.", "sustentada": False, "fuente": ""},
    ],
    "preguntas": [
        "¿Cuándo se acepta una solicitud de mutación?",
        "¿Qué se registra en una mutación de propietario?",
        "¿Qué pasa si el predio no existe?",
    ],
    "fragmentos": [{"id": "F1", "necesario": False}, {"id": "F2", "necesario": True}],
}


def juez(cliente):
    return InvocadorNodo(
        cliente,
        ParametrosNodo(NODO_JUEZ, "gpt-6.1-sol", "low", 6000),
        leer_prompt(RUTA_PROMPT),
        RegistroEnMemoria(),
    )


def sesion_validada():
    app = construir_grafo(
        ServiciosSimulados(fallos_veredicto=0).como_servicios(),
        ConfiguracionOrquestador(_env_file=None),
    ).compile(checkpointer=InMemorySaver(serde=serializador()))
    operador = Operador(app)
    guion = guion_completo()
    id_sesion = operador.iniciar("Oficina de catastro", "Gestión catastral", guion.necesidad)
    for respuesta in guion.respuestas_cliente[:7]:
        operador.responder(id_sesion, respuesta)
    for _ in range(3):
        operador.decidir(id_sesion, Decision.APROBADO, "Laura")
    return id_sesion, operador.estado(id_sesion), guion


def test_una_sesion_validada_da_una_muestra_por_agente():
    id_sesion, estado, guion = sesion_validada()

    muestras = {m.agente: m for m in muestras_de_sesion(id_sesion, estado)}

    assert set(muestras) == {"elicitador", "arquitecto", "tester"}
    del_elicitador = [
        c for c in estado["contexto"].fragmentos if AGENTE_DE_COLECCION[c] == "elicitador"
    ]
    assert muestras["elicitador"].colecciones == del_elicitador
    assert muestras["elicitador"].consulta == guion.necesidad
    assert "RF-01" in muestras["elicitador"].artefacto
    assert muestras["arquitecto"].colecciones == ["arquitecturas_referencia"]
    assert muestras["tester"].colecciones == ["criterios_calidad"]
    assert muestras["tester"].artefacto == estado["validacion"].reporte
    assert "# src/" in muestras["tester"].entradas


def test_sin_artefacto_el_agente_no_se_evalua():
    app = construir_grafo(
        ServiciosSimulados().como_servicios(), ConfiguracionOrquestador(_env_file=None)
    ).compile(checkpointer=InMemorySaver(serde=serializador()))
    operador = Operador(app)
    id_sesion = operador.iniciar("Oficina", "Catastro", guion_completo().necesidad)
    assert muestras_de_sesion(id_sesion, operador.estado(id_sesion)) == []


def test_las_metricas_salen_del_juicio_validado(
    cliente_falso, completar_respuesta, vectorizador_prueba
):
    sin_un_fragmento = {**JUICIO, "fragmentos": [{"id": "F2", "necesario": True}]}
    cliente = cliente_falso(completar_respuesta(sin_un_fragmento), completar_respuesta(JUICIO))

    metricas = evaluar_muestra(MUESTRA, juez(cliente), vectorizador_prueba)

    reintento = json.loads(cliente.llamadas[1]["messages"][-1]["content"])
    assert "cada id una vez: F1, F2" in reintento["problemas_intento_anterior"][0]
    enviados = json.loads(cliente.llamadas[0]["messages"][-1]["content"])
    assert [(f["id"], f["coleccion"]) for f in enviados["fragmentos"]] == [
        ("F1", "elicitacion"),
        ("F2", "dominio_negocio"),
    ]
    assert (metricas.afirmaciones, metricas.sustentadas) == (3, 2)
    assert metricas.fidelidad == pytest.approx(2 / 3)
    assert metricas.contexto["elicitacion"].relevancia == 0.0
    assert metricas.contexto["dominio_negocio"].relevancia == 1.0
    consulta, *preguntas = vectorizador_prueba.vectorizar([MUESTRA.consulta, *JUICIO["preguntas"]])
    esperada = sum(coseno(consulta, p) for p in preguntas) / 3
    assert metricas.relevancia_respuesta == pytest.approx(esperada)


def test_resumen_por_coleccion(vectorizador_prueba):
    primera = calcular_metricas(MUESTRA, SalidaJuezRag.model_validate(JUICIO), vectorizador_prueba)
    todo_sustentado = SalidaJuezRag.model_validate(
        {**JUICIO, "afirmaciones": JUICIO["afirmaciones"][:2]}
    )
    segunda = calcular_metricas(MUESTRA, todo_sustentado, vectorizador_prueba)

    resumen = resumen_por_coleccion([primera, segunda])

    assert list(resumen) == ["elicitacion", "dominio_negocio"]
    fidelidad = resumen["elicitacion"]["fidelidad"]
    assert fidelidad["minimo"] == pytest.approx(2 / 3) and fidelidad["maximo"] == 1.0
    assert fidelidad["media"] == pytest.approx(5 / 6)
    assert resumen["dominio_negocio"]["fidelidad"] == fidelidad
    assert resumen["dominio_negocio"]["relevancia_contexto"]["media"] == 1.0
    assert resumen["elicitacion"]["muestras"] == 2


def test_coseno():
    assert coseno([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert coseno([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert coseno([0.0, 0.0], [1.0, 0.0]) == 0.0
