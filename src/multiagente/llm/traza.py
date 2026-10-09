"""Traza de costo de las llamadas a modelos de lenguaje (RF-34, RNF-10).

Cada llamada, también la que falla, queda registrada con su prompt, sus tokens, su costo y su
latencia, porque se cobra igual. El registro no guarda el contenido de los mensajes: la traza
puede versionarse sin exponer lo que dijo el cliente. Hasta que exista la tabla `ejecuciones`
(paso 13), los registros van a memoria o a un archivo JSONL.
"""

import json
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from multiagente.llm.costos import ConsumoTokens


class RegistroLlamada(BaseModel):
    """Una llamada a un modelo con los datos de la traza de costo."""

    model_config = ConfigDict(frozen=True)

    fecha: datetime
    nodo: str
    prompt: str
    huella_prompt: str
    despliegue: str
    modelo: str
    region_procesamiento: str | None
    esfuerzo: str
    max_tokens_salida: int
    motivo_fin: str
    consumo: ConsumoTokens
    costo_usd: Decimal
    latencia_ms: int
    error: str | None = None

    def como_json(self) -> str:
        """Serializa el registro en una línea JSON con la salida visible desglosada.

        Returns:
            Línea JSON sin salto final; el costo va como texto para no perder precisión.
        """
        datos = self.model_dump(mode="json")
        datos["consumo"]["salida_visible"] = self.consumo.salida_visible
        return json.dumps(datos, ensure_ascii=False)


class RegistradorLlamadas(Protocol):
    """Destino de los registros de llamadas."""

    def registrar(self, llamada: RegistroLlamada) -> None:
        """Guarda el registro de una llamada."""
        ...


class RegistroEnMemoria:
    """Acumula los registros en memoria, para las pruebas y la consola."""

    def __init__(self) -> None:
        """Crea el registro vacío."""
        self.llamadas: list[RegistroLlamada] = []

    def registrar(self, llamada: RegistroLlamada) -> None:
        """Agrega el registro de una llamada.

        Args:
            llamada: Registro de la llamada.
        """
        self.llamadas.append(llamada)

    @property
    def costo_total_usd(self) -> Decimal:
        """Suma del costo de todas las llamadas registradas."""
        return sum((llamada.costo_usd for llamada in self.llamadas), Decimal(0))


class RegistroJsonl(RegistroEnMemoria):
    """Acumula los registros en memoria y agrega cada uno como línea de un archivo JSONL."""

    def __init__(self, ruta: Path, sesion: str | None = None) -> None:
        """Crea el registro sobre un archivo; la carpeta se crea si no existe.

        Args:
            ruta: Archivo JSONL al que se agregan las líneas.
            sesion: Identificador de la sesión, que se agrega a cada línea si se indica.
        """
        super().__init__()
        self.ruta = ruta
        self.sesion = sesion
        ruta.parent.mkdir(parents=True, exist_ok=True)

    def registrar(self, llamada: RegistroLlamada) -> None:
        """Agrega el registro en memoria y en el archivo.

        Args:
            llamada: Registro de la llamada.
        """
        super().registrar(llamada)
        linea = llamada.como_json()
        if self.sesion is not None:
            datos = json.loads(linea)
            linea = json.dumps({"sesion": self.sesion, **datos}, ensure_ascii=False)
        with self.ruta.open("a", encoding="utf-8") as archivo:
            archivo.write(linea + "\n")


SESION_ACTUAL: ContextVar[str | None] = ContextVar("sesion_actual", default=None)
"""Sesión a la que pertenecen las llamadas del contexto actual (`RegistroPorSesion`)."""


class RegistroPorSesion(RegistroEnMemoria):
    """Agrega cada llamada a un JSONL con la sesión en curso, para un proceso con varias sesiones.

    Las interfaces atienden varias sesiones en el mismo proceso: la sesión de cada llamada se
    toma de `SESION_ACTUAL`, que fija quien avanza el grafo con `en_sesion`.
    """

    def __init__(self, ruta: Path) -> None:
        """Crea el registro sobre un archivo; la carpeta se crea si no existe.

        Args:
            ruta: Archivo JSONL al que se agregan las líneas.
        """
        super().__init__()
        self.ruta = ruta
        ruta.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    @contextmanager
    def en_sesion(id_sesion: str) -> Iterator[None]:
        """Atribuye a una sesión las llamadas hechas dentro del bloque.

        Args:
            id_sesion: Identificador de la sesión.

        Yields:
            Nada; al salir se restablece la sesión anterior.
        """
        marca = SESION_ACTUAL.set(id_sesion)
        try:
            yield
        finally:
            SESION_ACTUAL.reset(marca)

    def registrar(self, llamada: RegistroLlamada) -> None:
        """Agrega el registro en memoria y en el archivo, con la sesión en curso.

        Args:
            llamada: Registro de la llamada.
        """
        super().registrar(llamada)
        linea = json.dumps(
            {"sesion": SESION_ACTUAL.get(), **json.loads(llamada.como_json())}, ensure_ascii=False
        )
        with self.ruta.open("a", encoding="utf-8") as archivo:
            archivo.write(linea + "\n")
