"""Condición de terminado del paso 3: una llamada real responde y su costo se calcula.

Cuesta dinero. Requiere las variables AZURE_OPENAI_* y MODELO_* en .env y se ejecuta con
`pytest -m nube`.
"""

from decimal import Decimal
from pathlib import Path

import pytest

from multiagente.core.configuracion import ConfiguracionAzureOpenAI, ConfiguracionModelos
from multiagente.llm.cliente import crear_cliente, invocar
from multiagente.llm.costos import buscar_tarifa, calcular_costo, cargar_tarifas

pytestmark = pytest.mark.nube

RAIZ = Path(__file__).resolve().parents[2]


def test_llamada_real_responde_y_tiene_costo():
    cliente = crear_cliente(ConfiguracionAzureOpenAI())
    respuesta = invocar(
        cliente,
        despliegue=ConfiguracionModelos().n14_veredicto,
        mensajes=[{"role": "user", "content": "Responde únicamente con la palabra: listo"}],
        esfuerzo="minimal",
        max_tokens_salida=500,
    )
    assert respuesta.motivo_fin == "stop"
    assert respuesta.contenido.strip()
    tarifas = cargar_tarifas(RAIZ / "config" / "tarifas_modelos.toml")
    costo = calcular_costo(respuesta.consumo, buscar_tarifa(tarifas, respuesta.modelo))
    assert costo > Decimal(0)
