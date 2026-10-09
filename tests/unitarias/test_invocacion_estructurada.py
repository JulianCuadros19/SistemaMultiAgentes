"""Invocación estructurada, prompts versionados y traza de costo, sin llamar a la red."""

import json
from decimal import Decimal

import pytest
from openai import omit
from pydantic import BaseModel, ConfigDict

from multiagente.llm.cliente import (
    ErrorFiltroContenido,
    ErrorLimiteSalida,
    ErrorRechazoModelo,
    ErrorSalidaInvalida,
    formato_json,
    invocar,
    invocar_estructurado,
)
from multiagente.llm.costos import Tarifa
from multiagente.llm.invocador import InvocadorNodo, ParametrosNodo
from multiagente.llm.prompts import ErrorPrompt, cargar_prompt
from multiagente.llm.traza import RegistroEnMemoria, RegistroJsonl

TARIFAS = {
    "gpt-5-nano": Tarifa(
        entrada=Decimal("0.05"), entrada_cacheada=Decimal("0.005"), salida=Decimal("0.40")
    )
}


class Salida(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pregunta: str | None
    atributos: list[str]


def llamar(cliente):
    return invocar_estructurado(
        cliente,
        despliegue="gpt-5-nano",
        mensajes=[{"role": "user", "content": "datos"}],
        esfuerzo="low",
        max_tokens_salida=4000,
        esquema=Salida,
    )


def test_formato_json_es_estricto_y_exige_todos_los_campos():
    formato = formato_json(Salida)
    assert formato["type"] == "json_schema"
    esquema = formato["json_schema"]
    assert (esquema["name"], esquema["strict"]) == ("Salida", True)
    assert sorted(esquema["schema"]["required"]) == ["atributos", "pregunta"]
    assert esquema["schema"]["additionalProperties"] is False


def test_salida_estructurada_valida(cliente_falso, completar_respuesta):
    cliente = cliente_falso(completar_respuesta({"pregunta": "¿Quién?", "atributos": ["rol"]}))
    salida = llamar(cliente)
    assert salida.valor == Salida(pregunta="¿Quién?", atributos=["rol"])
    assert salida.respuesta.region == "South Central US"
    argumentos = cliente.llamadas[0]
    assert argumentos["reasoning_effort"] == "low"
    assert argumentos["max_completion_tokens"] == 4000
    assert argumentos["response_format"]["json_schema"]["name"] == "Salida"


def test_tiempo_de_espera_por_llamada(cliente_falso, completar_respuesta):
    cliente = cliente_falso(completar_respuesta({"pregunta": None, "atributos": []}))
    invocar_estructurado(
        cliente,
        despliegue="gpt-5",
        mensajes=[],
        esfuerzo="medium",
        max_tokens_salida=16000,
        esquema=Salida,
        tiempo_espera_s=300,
    )
    assert cliente.opciones == {"timeout": 300}


def test_invocacion_de_texto_libre_no_envia_formato(cliente_falso, completar_respuesta):
    cliente = cliente_falso(completar_respuesta("listo"))
    respuesta = invocar(
        cliente,
        despliegue="gpt-5-nano",
        mensajes=[{"role": "user", "content": "di listo"}],
        esfuerzo="minimal",
        max_tokens_salida=100,
    )
    assert respuesta.contenido == "listo"
    assert cliente.llamadas[0]["response_format"] is omit


def test_limite_agotado_conserva_el_consumo(cliente_falso, completar_respuesta):
    cliente = cliente_falso(
        completar_respuesta(None, motivo_fin="length", salida=4000, razonamiento=4000)
    )
    with pytest.raises(ErrorLimiteSalida, match="4000 de razonamiento") as error:
        llamar(cliente)
    assert error.value.respuesta.consumo.salida == 4000


@pytest.mark.parametrize(
    ("argumentos", "error"),
    [
        ({"contenido": None, "motivo_fin": "content_filter"}, ErrorFiltroContenido),
        ({"contenido": None, "rechazo": "No puedo ayudar"}, ErrorRechazoModelo),
        ({"contenido": '{"pregunta": 3}'}, ErrorSalidaInvalida),
        ({"contenido": "no es JSON"}, ErrorSalidaInvalida),
    ],
)
def test_respuestas_inutilizables(cliente_falso, completar_respuesta, argumentos, error):
    contenido = argumentos.pop("contenido")
    cliente = cliente_falso(completar_respuesta(contenido, **argumentos))
    with pytest.raises(error):
        llamar(cliente)


def escribir_prompt(raiz, agente="elicitador", version="1.10", cuerpo="Eres un analista."):
    carpeta = raiz / agente
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "dialogo.md").write_text(
        f"---\nid: elicitador.dialogo\nagente: elicitador\nnodo: N3\nversion: {version}\n"
        f"descripcion: Prompt de prueba\n---\n\n{cuerpo}\n",
        encoding="utf-8",
    )


def test_prompt_versionado(tmp_path):
    escribir_prompt(tmp_path)
    prompt = cargar_prompt("elicitador", "dialogo", tmp_path)
    assert prompt.texto == "Eres un analista."
    assert prompt.identificador == "elicitador.dialogo@1.10"
    assert len(prompt.huella) == 64
    escribir_prompt(tmp_path, cuerpo="Eres otro analista.")
    assert cargar_prompt("elicitador", "dialogo", tmp_path).huella != prompt.huella


def test_prompt_inexistente(tmp_path):
    with pytest.raises(ErrorPrompt, match="no existe"):
        cargar_prompt("elicitador", "dialogo", tmp_path)


def test_prompt_sin_cabecera(tmp_path):
    (tmp_path / "elicitador").mkdir()
    (tmp_path / "elicitador" / "dialogo.md").write_text("Eres un analista.\n", encoding="utf-8")
    with pytest.raises(ErrorPrompt, match="falta la cabecera"):
        cargar_prompt("elicitador", "dialogo", tmp_path)


def test_prompt_con_version_invalida(tmp_path):
    escribir_prompt(tmp_path, version="uno")
    with pytest.raises(ErrorPrompt, match="inválido"):
        cargar_prompt("elicitador", "dialogo", tmp_path)


def test_prompt_en_carpeta_de_otro_agente(tmp_path):
    escribir_prompt(tmp_path, agente="tester")
    with pytest.raises(ErrorPrompt, match="declara el agente elicitador"):
        cargar_prompt("tester", "dialogo", tmp_path)


def invocador(tmp_path, cliente, registrador):
    escribir_prompt(tmp_path)
    return InvocadorNodo(
        cliente,
        ParametrosNodo(nodo="N3", despliegue="gpt-5-nano", esfuerzo="low", max_tokens_salida=4000),
        cargar_prompt("elicitador", "dialogo", tmp_path),
        registrador,
        TARIFAS,
    )


def test_invocador_antepone_el_prompt_y_registra_la_llamada(
    tmp_path, cliente_falso, completar_respuesta
):
    cliente = cliente_falso(
        completar_respuesta({"pregunta": None, "atributos": []}, entrada=1000, salida=500)
    )
    registro = RegistroEnMemoria()
    valor = invocador(tmp_path, cliente, registro).invocar(
        [{"role": "user", "content": "datos"}], Salida
    )
    assert valor.atributos == []
    mensajes = cliente.llamadas[0]["messages"]
    assert mensajes[0] == {"role": "system", "content": "Eres un analista."}
    [llamada] = registro.llamadas
    assert (llamada.nodo, llamada.prompt, llamada.error) == ("N3", "elicitador.dialogo@1.10", None)
    # 1000 × 0,05 + 500 × 0,40 por millón de tokens.
    assert llamada.costo_usd == Decimal("0.00025")
    assert registro.costo_total_usd == Decimal("0.00025")


def test_invocador_registra_tambien_la_llamada_fallida(
    tmp_path, cliente_falso, completar_respuesta
):
    cliente = cliente_falso(completar_respuesta(None, motivo_fin="length", salida=4000))
    registro = RegistroEnMemoria()
    with pytest.raises(ErrorLimiteSalida):
        invocador(tmp_path, cliente, registro).invocar([], Salida)
    [llamada] = registro.llamadas
    assert llamada.error == "ErrorLimiteSalida"
    assert llamada.costo_usd > 0


def test_registro_jsonl_no_guarda_contenido(tmp_path, cliente_falso, completar_respuesta):
    cliente = cliente_falso(completar_respuesta({"pregunta": "¿Secreto?", "atributos": []}))
    ruta = tmp_path / "mediciones" / "llamadas.jsonl"
    invocador(tmp_path, cliente, RegistroJsonl(ruta)).invocar([], Salida)
    [linea] = ruta.read_text(encoding="utf-8").splitlines()
    datos = json.loads(linea)
    assert datos["costo_usd"] == "0.000145"
    assert datos["consumo"]["salida_visible"] == 100
    assert "Secreto" not in linea
