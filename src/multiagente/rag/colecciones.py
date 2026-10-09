"""Colecciones de conocimiento y mapa de acceso por agente (RF-29, decisión 1)."""

from collections.abc import Iterable, Mapping
from enum import StrEnum
from types import MappingProxyType


class Coleccion(StrEnum):
    """Las cuatro colecciones de la base de conocimiento (arquitectura, Tabla 2)."""

    ELICITACION = "elicitacion"
    DOMINIO_NEGOCIO = "dominio_negocio"
    ARQUITECTURAS_REFERENCIA = "arquitecturas_referencia"
    CRITERIOS_CALIDAD = "criterios_calidad"


class Agente(StrEnum):
    """Agentes del sistema."""

    ELICITADOR = "elicitador"
    ARQUITECTO = "arquitecto"
    DESARROLLADOR = "desarrollador"
    TESTER = "tester"


ACCESO: Mapping[Agente, frozenset[Coleccion]] = MappingProxyType(
    {
        Agente.ELICITADOR: frozenset({Coleccion.ELICITACION, Coleccion.DOMINIO_NEGOCIO}),
        Agente.ARQUITECTO: frozenset({Coleccion.ARQUITECTURAS_REFERENCIA}),
        Agente.DESARROLLADOR: frozenset(),
        Agente.TESTER: frozenset({Coleccion.CRITERIOS_CALIDAD}),
    }
)
"""Colecciones que puede consultar cada agente. El desarrollador no tiene ninguna."""


class ErrorAccesoNoAutorizado(PermissionError):
    """Un agente intentó consultar una colección que no le corresponde."""


def autorizar(
    agente: Agente, solicitadas: Iterable[Coleccion] | None = None
) -> frozenset[Coleccion]:
    """Determina las colecciones que un agente puede consultar en una recuperación.

    Args:
        agente: Agente que consulta.
        solicitadas: Colecciones pedidas; si se omite, todas las autorizadas al agente.

    Returns:
        Colecciones autorizadas para esta consulta.

    Raises:
        ErrorAccesoNoAutorizado: Si el agente no tiene colecciones o si pide una ajena.
    """
    permitidas = ACCESO[agente]
    if not permitidas:
        raise ErrorAccesoNoAutorizado(f"El agente {agente} no consulta bases de conocimiento")
    if solicitadas is None:
        return permitidas
    pedidas = frozenset(Coleccion(coleccion) for coleccion in solicitadas)
    if ajenas := sorted(pedidas - permitidas):
        raise ErrorAccesoNoAutorizado(f"El agente {agente} no puede consultar {ajenas}")
    return pedidas
