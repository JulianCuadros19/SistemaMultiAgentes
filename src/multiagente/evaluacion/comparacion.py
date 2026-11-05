"""Comparación de los enfoques del objetivo 4 (paso 15, ADR-0019).

Reúne por caso y por enfoque el tiempo de máquina, el costo de inferencia y la tasa de errores de
referencia. En costo y tiempo agrega una prueba de signos por caso, exploratoria: compara el sistema
con cada línea base, un caso a la vez.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from math import comb


@dataclass(frozen=True)
class Medicion:
    """Una implementación medida.

    Attributes:
        caso: Identificador del caso de referencia.
        enfoque: `sistema`, `modelo_unico` o `un_prompt`.
        etiqueta: Identificador de la implementación.
        tiempo_maquina_min: Minutos de cómputo, sin el cliente simulado.
        inferencia_usd: Costo de los modelos, sin el cliente simulado.
        pasan: Verificaciones de referencia que pasan.
        total: Verificaciones de referencia del caso.
    """

    caso: str
    enfoque: str
    etiqueta: str
    tiempo_maquina_min: Decimal
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
        inferencia_usd: Media del costo de los modelos.
        pasan: Verificaciones que pasan, sumadas.
        total: Verificaciones ejecutadas, sumadas.
    """

    caso: str
    enfoque: str
    corridas: int
    tiempo_maquina_min: Decimal
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


@dataclass(frozen=True)
class ComparacionPareada:
    """Comparación caso a caso de un enfoque con otro en una magnitud.

    Attributes:
        mayor: Casos en que el primer enfoque tiene el valor mayor.
        menor: Casos en que tiene el valor menor.
        empates: Casos en que coinciden; no cuentan en la prueba.
        valor_p: Valor p bilateral de la prueba de signos.
    """

    mayor: int
    menor: int
    empates: int
    valor_p: float


def prueba_de_signos(mayor: int, menor: int) -> float:
    """Valor p bilateral de la prueba de signos, sin los empates.

    Args:
        mayor: Casos a favor de un sentido.
        menor: Casos a favor del otro.

    Returns:
        La probabilidad de un reparto igual o más extremo si ambos sentidos fueran igual de
        probables. Vale 1 si no hay casos.
    """
    casos = mayor + menor
    if casos == 0:
        return 1.0
    extremos = sum(comb(casos, k) for k in range(min(mayor, menor) + 1))
    return min(1.0, 2 * extremos / 2**casos)


def comparar_por_caso(
    primero: dict[str, Decimal], segundo: dict[str, Decimal]
) -> ComparacionPareada:
    """Compara dos enfoques en los casos que ambos tienen.

    Args:
        primero: Valor del primer enfoque por caso.
        segundo: Valor del segundo enfoque por caso.

    Returns:
        Cuántos casos caen a cada lado, los empates y el valor p.
    """
    comunes = sorted(set(primero) & set(segundo))
    mayor = sum(primero[caso] > segundo[caso] for caso in comunes)
    menor = sum(primero[caso] < segundo[caso] for caso in comunes)
    return ComparacionPareada(
        mayor, menor, len(comunes) - mayor - menor, prueba_de_signos(mayor, menor)
    )
