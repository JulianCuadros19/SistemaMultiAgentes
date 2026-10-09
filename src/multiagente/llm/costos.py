"""Consumo de tokens y costo de una llamada a un modelo, calculado con Decimal."""

import tomllib
from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel, ConfigDict, NonNegativeInt, model_validator

MILLON = Decimal(1_000_000)

RUTA_TARIFAS = Path(__file__).resolve().parents[3] / "config" / "tarifas_modelos.toml"
"""Tarifas versionadas del repositorio (`config/tarifas_modelos.toml`)."""


class ConsumoTokens(BaseModel):
    """Tokens de una llamada, con el razonamiento registrado aparte.

    Los tokens de razonamiento ya están incluidos en `salida`, y los leídos y escritos en caché
    en `entrada`; se desglosan para la traza y el costo, no se suman de nuevo.
    """

    model_config = ConfigDict(frozen=True)

    entrada: NonNegativeInt
    entrada_cacheada: NonNegativeInt = 0
    entrada_escrita_cache: NonNegativeInt = 0
    salida: NonNegativeInt
    razonamiento: NonNegativeInt = 0

    @model_validator(mode="after")
    def _desgloses_dentro_del_total(self) -> "ConsumoTokens":
        if self.entrada_cacheada + self.entrada_escrita_cache > self.entrada:
            raise ValueError("entrada_cacheada y entrada_escrita_cache no pueden superar a entrada")
        if self.razonamiento > self.salida:
            raise ValueError("razonamiento no puede superar a salida")
        return self

    @property
    def salida_visible(self) -> int:
        """Tokens de salida que llegan al contenido de la respuesta."""
        return self.salida - self.razonamiento


class Tarifa(BaseModel):
    """Precio en USD por millón de tokens de un modelo y tipo de despliegue.

    `escritura_cache` es None cuando el proveedor no cobra aparte la escritura en caché: esos
    tokens se cobran entonces como entrada normal. Los modelos GPT-6 sí la cobran (ADR-0011).
    """

    model_config = ConfigDict(frozen=True)

    entrada: Decimal
    entrada_cacheada: Decimal
    salida: Decimal
    escritura_cache: Decimal | None = None


class ErrorTarifaNoEncontrada(LookupError):
    """No hay tarifa registrada para el modelo que respondió la llamada."""


def cargar_tarifas(ruta: Path = RUTA_TARIFAS) -> dict[str, Tarifa]:
    """Lee las tarifas desde un archivo TOML versionado.

    Los precios se leen como texto para convertirlos a Decimal sin pérdida.

    Args:
        ruta: Archivo con una tabla por modelo y las claves `entrada`, `entrada_cacheada`
            y `salida`, más `escritura_cache` si el modelo la cobra aparte.

    Returns:
        Tarifas indexadas por el nombre del modelo.
    """
    with ruta.open("rb") as archivo:
        datos = tomllib.load(archivo, parse_float=Decimal)
    return {
        modelo: Tarifa(
            entrada=Decimal(str(valores["entrada"])),
            entrada_cacheada=Decimal(str(valores["entrada_cacheada"])),
            salida=Decimal(str(valores["salida"])),
            escritura_cache=(
                Decimal(str(valores["escritura_cache"])) if "escritura_cache" in valores else None
            ),
        )
        for modelo, valores in datos.items()
    }


def buscar_tarifa(tarifas: dict[str, Tarifa], modelo: str) -> Tarifa:
    """Busca la tarifa del modelo por la familia registrada más larga.

    Azure responde con el nombre versionado (`gpt-5-nano-2025-08-07`), mientras que las
    tarifas se registran por familia (`gpt-5-nano`). Una familia coincide si es el nombre
    completo o si va seguida de un guion: así `gpt-5` no se aplica en silencio a `gpt-5.4-…`.

    Args:
        tarifas: Tarifas cargadas con `cargar_tarifas`.
        modelo: Nombre del modelo que devolvió la respuesta.

    Returns:
        La tarifa del prefijo más largo que coincide.

    Raises:
        ErrorTarifaNoEncontrada: Si ningún prefijo registrado coincide.
    """
    candidatos = [
        nombre for nombre in tarifas if modelo == nombre or modelo.startswith(f"{nombre}-")
    ]
    if not candidatos:
        raise ErrorTarifaNoEncontrada(f"No hay tarifa registrada para el modelo {modelo!r}")
    return tarifas[max(candidatos, key=len)]


def calcular_costo(consumo: ConsumoTokens, tarifa: Tarifa) -> Decimal:
    """Calcula el costo en USD de una llamada.

    La entrada cacheada se cobra a su tarifa reducida, la escrita en caché a su tarifa si el
    modelo la tiene (si no, como entrada normal) y el resto de la entrada a la tarifa normal.
    Los tokens de razonamiento se cobran como salida una sola vez, porque ya están incluidos en
    `consumo.salida`.

    Args:
        consumo: Tokens de la llamada.
        tarifa: Precios del modelo por millón de tokens.

    Returns:
        Costo en USD, sin redondear.
    """
    escritura = tarifa.escritura_cache if tarifa.escritura_cache is not None else tarifa.entrada
    entrada_normal = consumo.entrada - consumo.entrada_cacheada - consumo.entrada_escrita_cache
    total = (
        entrada_normal * tarifa.entrada
        + consumo.entrada_cacheada * tarifa.entrada_cacheada
        + consumo.entrada_escrita_cache * escritura
        + consumo.salida * tarifa.salida
    )
    return total / MILLON
