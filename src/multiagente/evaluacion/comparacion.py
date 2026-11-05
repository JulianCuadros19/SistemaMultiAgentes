"""Comparación de los enfoques del objetivo 4 (paso 15, ADR-0019).

Reúne por caso y por enfoque el tiempo de máquina, las horas-persona, el costo y la tasa de errores
de referencia. El costo es la inferencia más las horas-persona por la tarifa fijada antes de medir.
"""

import csv
import io
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

FORMATO_HORA = "%Y-%m-%d %H:%M"
TARIFAS_USD_POR_HORA = (Decimal(5), Decimal(9), Decimal(20))
"""La tarifa fijada, 9 USD por hora, y las dos con que se muestra la sensibilidad."""


def minutos_de_tiempos(texto: str) -> Decimal:
    """Suma los minutos de un `tiempos.csv` de la implementación manual.

    Una fila usa su columna `minutos`; si está vacía, se calcula del inicio y el fin.

    Args:
        texto: Contenido del archivo, con las columnas `fase`, `inicio`, `fin`, `minutos` y `notas`.

    Returns:
        Los minutos de trabajo, sin las pausas.

    Raises:
        ValueError: Si una fila no trae minutos ni horas que se puedan leer.
    """
    total = Decimal(0)
    for fila in csv.DictReader(io.StringIO(texto)):
        if (minutos := (fila.get("minutos") or "").strip()) != "":
            total += Decimal(minutos)
            continue
        inicio = datetime.strptime(fila["inicio"].strip(), FORMATO_HORA)
        fin = datetime.strptime(fila["fin"].strip(), FORMATO_HORA)
        total += Decimal(int((fin - inicio).total_seconds())) / Decimal(60)
    return total


def costo_total(inferencia_usd: Decimal, horas_persona: Decimal, tarifa: Decimal) -> Decimal:
    """Costo de una implementación: la inferencia más las horas-persona por la tarifa.

    Args:
        inferencia_usd: Costo de los modelos.
        horas_persona: Horas de trabajo de una persona.
        tarifa: Tarifa en USD por hora.

    Returns:
        El costo en USD.
    """
    return inferencia_usd + horas_persona * tarifa


@dataclass(frozen=True)
class Medicion:
    """Una implementación medida.

    Attributes:
        caso: Identificador del caso de referencia.
        enfoque: `sistema`, `sistema_humano`, `modelo_unico` o `manual`.
        etiqueta: Identificador de la implementación.
        tiempo_maquina_min: Minutos de cómputo, sin el cliente simulado ni la espera humana.
        horas_persona: Horas de implementación o de revisión humana.
        inferencia_usd: Costo de los modelos, sin el cliente simulado.
        pasan: Verificaciones de referencia que pasan.
        total: Verificaciones de referencia del caso.
    """

    caso: str
    enfoque: str
    etiqueta: str
    tiempo_maquina_min: Decimal
    horas_persona: Decimal
    inferencia_usd: Decimal
    pasan: int
    total: int


@dataclass(frozen=True)
class Resumen:
    """Promedio de las mediciones de un enfoque, y los errores de todas sus corridas.

    Attributes:
        caso: Caso de referencia, o `todos` si reúne varios.
        enfoque: Enfoque medido.
        corridas: Implementaciones que promedia.
        tiempo_maquina_min: Media de los minutos de cómputo.
        horas_persona: Media de las horas-persona.
        inferencia_usd: Media del costo de los modelos.
        pasan: Verificaciones que pasan, sumadas.
        total: Verificaciones ejecutadas, sumadas.
    """

    caso: str
    enfoque: str
    corridas: int
    tiempo_maquina_min: Decimal
    horas_persona: Decimal
    inferencia_usd: Decimal
    pasan: int
    total: int

    @property
    def tasa_errores(self) -> Decimal:
        """Verificaciones que no pasan entre el total."""
        return Decimal(self.total - self.pasan) / Decimal(self.total) if self.total else Decimal(1)


def resumir(caso: str, enfoque: str, mediciones: Sequence[Medicion]) -> Resumen:
    """Promedia las mediciones de un enfoque.

    Args:
        caso: Etiqueta del caso, o `todos`.
        enfoque: Enfoque medido.
        mediciones: Implementaciones que se reúnen; al menos una.

    Returns:
        El resumen, con los errores sumados y lo demás en media.

    Raises:
        ValueError: Si no hay mediciones.
    """
    if not mediciones:
        raise ValueError("Sin mediciones que resumir.")
    corridas = Decimal(len(mediciones))
    return Resumen(
        caso=caso,
        enfoque=enfoque,
        corridas=len(mediciones),
        tiempo_maquina_min=sum((m.tiempo_maquina_min for m in mediciones), Decimal(0)) / corridas,
        horas_persona=sum((m.horas_persona for m in mediciones), Decimal(0)) / corridas,
        inferencia_usd=sum((m.inferencia_usd for m in mediciones), Decimal(0)) / corridas,
        pasan=sum(m.pasan for m in mediciones),
        total=sum(m.total for m in mediciones),
    )


def agrupar(mediciones: Iterable[Medicion]) -> list[Resumen]:
    """Resume por caso y enfoque, y agrega el total de cada enfoque.

    Args:
        mediciones: Todas las implementaciones medidas.

    Returns:
        Un resumen por caso y enfoque, en orden, y uno `todos` por enfoque.
    """
    lista = list(mediciones)
    resumenes = []
    for caso, enfoque in sorted({(m.caso, m.enfoque) for m in lista}):
        grupo = [m for m in lista if (m.caso, m.enfoque) == (caso, enfoque)]
        resumenes.append(resumir(caso, enfoque, grupo))
    for enfoque in sorted({m.enfoque for m in lista}):
        resumenes.append(resumir("todos", enfoque, [m for m in lista if m.enfoque == enfoque]))
    return resumenes
