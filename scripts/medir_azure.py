"""Mide tokens, costo y latencia de llamadas reales a Azure OpenAI (paso 3 del plan).

Hace cuatro llamadas con el mismo mensaje sintético: esfuerzo minimal, low y medium con un
límite amplio, y medium con un límite de 64 tokens para observar qué ocurre cuando el
razonamiento agota el límite. Cada llamada se agrega como una línea JSON a
docs/mediciones/paso-03-azure-openai.jsonl, sin la clave ni el endpoint.

Uso: python scripts/medir_azure.py [--despliegue NOMBRE]
"""

import argparse
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from openai.types.chat import ChatCompletionMessageParam

from multiagente.core.configuracion import ConfiguracionAzureOpenAI, ConfiguracionModelos
from multiagente.llm.cliente import EsfuerzoRazonamiento, crear_cliente, invocar
from multiagente.llm.costos import buscar_tarifa, calcular_costo, cargar_tarifas

RAIZ = Path(__file__).resolve().parents[1]
ARCHIVO_TARIFAS = RAIZ / "config" / "tarifas_modelos.toml"
ARCHIVO_MEDICIONES = RAIZ / "docs" / "mediciones" / "paso-03-azure-openai.jsonl"

# Mensaje de medición sintético, sin datos de Realtix. Este script no es un nodo del grafo.
MENSAJES: list[ChatCompletionMessageParam] = [
    {
        "role": "system",
        "content": "Eres un analista de requerimientos. Responde en español, en dos frases.",
    },
    {
        "role": "user",
        "content": (
            "¿Qué información mínima necesita una historia de usuario para registrar una "
            "mutación catastral de primera clase?"
        ),
    },
]

CASOS: list[tuple[EsfuerzoRazonamiento, int]] = [
    ("minimal", 8000),
    ("low", 8000),
    ("medium", 8000),
    ("medium", 64),
]


def main() -> None:
    """Ejecuta las llamadas de medición, imprime la tabla y registra cada llamada."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--despliegue",
        help="Despliegue a medir. Por defecto, el del nodo N3 (MODELO_N3_DIALOGO).",
    )
    argumentos = parser.parse_args()
    despliegue = argumentos.despliegue or ConfiguracionModelos().n3_dialogo

    cliente = crear_cliente(ConfiguracionAzureOpenAI())
    tarifas = cargar_tarifas(ARCHIVO_TARIFAS)
    ARCHIVO_MEDICIONES.parent.mkdir(parents=True, exist_ok=True)

    print(f"Despliegue: {despliegue}")
    print(
        f"{'esfuerzo':8} {'límite':>6} {'fin':6} {'entrada':>7} {'salida':>6} "
        f"{'razon.':>6} {'visible':>7} {'costo USD':>12} {'ms':>6}"
    )
    costo_total = Decimal(0)
    for esfuerzo, limite in CASOS:
        respuesta = invocar(
            cliente,
            despliegue=despliegue,
            mensajes=MENSAJES,
            esfuerzo=esfuerzo,
            max_tokens_salida=limite,
        )
        consumo = respuesta.consumo
        costo = calcular_costo(consumo, buscar_tarifa(tarifas, respuesta.modelo))
        costo_total += costo
        registro = {
            "fecha": datetime.now(UTC).isoformat(timespec="seconds"),
            "despliegue": despliegue,
            "modelo": respuesta.modelo,
            "region_procesamiento": respuesta.region,
            "esfuerzo": esfuerzo,
            "max_tokens_salida": limite,
            "motivo_fin": respuesta.motivo_fin,
            "tokens": {
                "entrada": consumo.entrada,
                "entrada_cacheada": consumo.entrada_cacheada,
                "salida": consumo.salida,
                "razonamiento": consumo.razonamiento,
                "salida_visible": consumo.salida_visible,
            },
            "costo_usd": str(costo),
            "latencia_ms": respuesta.latencia_ms,
            "respuesta": respuesta.contenido,
        }
        with ARCHIVO_MEDICIONES.open("a", encoding="utf-8") as archivo:
            archivo.write(json.dumps(registro, ensure_ascii=False) + "\n")
        print(
            f"{esfuerzo:8} {limite:>6} {respuesta.motivo_fin:6} {consumo.entrada:>7} "
            f"{consumo.salida:>6} {consumo.razonamiento:>6} {consumo.salida_visible:>7} "
            f"{costo:>12.8f} {respuesta.latencia_ms:>6}"
        )
    print(f"Costo total: USD {costo_total:.8f}")
    print(f"Registrado en {ARCHIVO_MEDICIONES.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
