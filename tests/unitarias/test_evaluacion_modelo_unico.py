"""Línea base de un modelo único (paso 15, ADR-0019), con clientes falsos y sin costo."""

import json
from pathlib import Path

from multiagente.core.estilo import EstiloGenerado
from multiagente.evaluacion.modelo_unico import (
    NODO_DIALOGO,
    NODO_ENTREGA,
    RUTA_PROMPT,
    ModeloUnico,
    problemas_de_la_entrega,
)
from multiagente.interfaces.cliente_simulado import ClienteSimulado, cargar_caso
from multiagente.llm.invocador import InvocadorNodo, ParametrosNodo
from multiagente.llm.prompts import leer_prompt
from multiagente.llm.traza import RegistroEnMemoria

CASO = cargar_caso(
    Path(__file__).resolve().parents[2]
    / "evaluacion"
    / "casos"
    / "ampliada"
    / "elicitacion-validacion-nit.md"
)
ENTREGA_VALIDA = {
    "archivos": [
        {"ruta": "src/nit/__init__.py", "contenido": ""},
        {"ruta": "src/nit/digito.py", "contenido": "def dv(numero: str) -> int:\n    return 8\n"},
        {"ruta": "tests/test_digito.py", "contenido": "def test_dv():\n    assert True\n"},
        {"ruta": "USO.md", "contenido": "# Uso\n"},
    ]
}
ESTILO = EstiloGenerado(archivo="ruff.toml", texto="line-length = 100\n", huella="abc")


def modelo_unico(cliente, registro, limite_turnos=18):
    prompt = leer_prompt(RUTA_PROMPT)
    return ModeloUnico(
        dialogo=InvocadorNodo(
            cliente, ParametrosNodo(NODO_DIALOGO, "gpt-6.1-sol", "low", 4000), prompt, registro
        ),
        entrega=InvocadorNodo(
            cliente, ParametrosNodo(NODO_ENTREGA, "gpt-6.1-sol", "medium", 32000), prompt, registro
        ),
        estilo=ESTILO,
        paquetes=("fastapi==0.141.1", "pytest==9.1.1"),
        limite_turnos=limite_turnos,
    )


def datos(llamada):
    return json.loads(llamada["messages"][-1]["content"])


def test_conversa_con_el_cliente_y_entrega_con_un_solo_prompt(cliente_falso, completar_respuesta):
    modelo = cliente_falso(
        completar_respuesta({"pregunta": "¿Quién consulta el servicio?", "listo": False}),
        completar_respuesta({"pregunta": "", "listo": True}),
        completar_respuesta(ENTREGA_VALIDA, salida=4000),
    )
    cliente = cliente_falso(completar_respuesta({"respuesta": "El portal y la facturación"}))
    registro = RegistroEnMemoria()
    simulado = ClienteSimulado(cliente, "gpt-5.4-mini", CASO, registro)

    resultado = modelo_unico(modelo, registro).resolver(CASO, simulado, registro, "corrida-1")

    assert resultado.error is None
    assert set(resultado.archivos) == {a["ruta"] for a in ENTREGA_VALIDA["archivos"]}
    assert resultado.transcripcion == [
        {"emisor": "cliente", "texto": CASO.necesidad},
        {"emisor": "modelo", "texto": "¿Quién consulta el servicio?"},
        {"emisor": "cliente", "texto": "El portal y la facturación"},
    ]
    assert (resultado.turnos_cliente, resultado.llego_al_limite) == (2, False)
    assert (resultado.llamadas_modelo, resultado.reintentos_entrega) == (3, 0)
    assert resultado.costo_modelo_usd > 0 and resultado.costo_cliente_usd > 0
    assert resultado.prompt == "evaluacion.modelo_unico@1.0"

    primera, _, entrega = modelo.llamadas
    assert primera["messages"][0] == entrega["messages"][0]
    assert datos(primera)["momento"] == "dialogo"
    assert datos(primera)["preguntas_restantes"] == 17
    assert datos(entrega)["momento"] == "entrega"
    assert datos(entrega)["entorno"] == {
        "python": "3.11",
        "paquetes": ["fastapi==0.141.1", "pytest==9.1.1"],
        "ruff": {"archivo": "ruff.toml", "contenido": "line-length = 100\n"},
    }
    assert datos(cliente.llamadas[0])["pregunta"] == "¿Quién consulta el servicio?"


def test_una_entrega_inservible_se_reintenta_una_vez(cliente_falso, completar_respuesta):
    sin_pruebas = {
        "archivos": [a for a in ENTREGA_VALIDA["archivos"] if a["ruta"] != "tests/test_digito.py"]
    }
    modelo = cliente_falso(
        completar_respuesta({"pregunta": "", "listo": True}),
        completar_respuesta(sin_pruebas),
        completar_respuesta(ENTREGA_VALIDA),
    )
    registro = RegistroEnMemoria()
    simulado = ClienteSimulado(cliente_falso(), "gpt-5.4-mini", CASO, registro)

    resultado = modelo_unico(modelo, registro).resolver(CASO, simulado, registro, "corrida-2")

    assert resultado.error is None and resultado.reintentos_entrega == 1
    assert datos(modelo.llamadas[2])["problemas_intento_anterior"] == [
        "Faltan las pruebas en tests/."
    ]


def test_el_dialogo_termina_en_el_limite_de_turnos_del_cliente(cliente_falso, completar_respuesta):
    pregunta = completar_respuesta({"pregunta": "¿Algo más?", "listo": False})
    modelo = cliente_falso(pregunta, pregunta, completar_respuesta(ENTREGA_VALIDA))
    respuesta = completar_respuesta({"respuesta": "No"})
    registro = RegistroEnMemoria()
    simulado = ClienteSimulado(cliente_falso(respuesta, respuesta), "gpt-5.4-mini", CASO, registro)

    resultado = modelo_unico(modelo, registro, limite_turnos=3).resolver(
        CASO, simulado, registro, "corrida-3"
    )

    assert (resultado.turnos_cliente, resultado.llego_al_limite) == (3, True)
    assert resultado.archivos and resultado.error is None


def test_sin_entrega_valida_la_corrida_queda_con_el_error(cliente_falso, completar_respuesta):
    roto = {"archivos": [{"ruta": "../fuera.py", "contenido": "x ="}]}
    modelo = cliente_falso(
        completar_respuesta({"pregunta": "", "listo": True}),
        completar_respuesta(roto),
        completar_respuesta(roto),
    )
    registro = RegistroEnMemoria()
    simulado = ClienteSimulado(cliente_falso(), "gpt-5.4-mini", CASO, registro)

    resultado = modelo_unico(modelo, registro).resolver(CASO, simulado, registro, "corrida-4")

    assert resultado.archivos == {}
    assert resultado.error.startswith("ErrorValidacionSalida")
    assert "Ruta insegura" in resultado.error


def test_problemas_de_la_entrega():
    assert problemas_de_la_entrega({}) == ["La entrega no trae archivos."]
    problemas = problemas_de_la_entrega(
        {"src/a.py": "type Numero = int\n", "tests/test_a.py": "def test(): pass\n"}
    )
    assert problemas[0] == "Falta USO.md."
    assert problemas[1].startswith("src/a.py: error de sintaxis en la línea 1")
    assert (
        problemas_de_la_entrega({a["ruta"]: a["contenido"] for a in ENTREGA_VALIDA["archivos"]})
        == []
    )
