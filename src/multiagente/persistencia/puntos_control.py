"""Persistencia del estado del grafo mediante puntos de control (RF-28, RNF-02)."""

from enum import Enum
from types import ModuleType

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from multiagente.core.esquemas import comunes, especificacion_diseno, requerimiento
from multiagente.orquestador import estado
from multiagente.orquestador.estado import PARTICIONES

MODULOS_DEL_ESTADO: tuple[ModuleType, ...] = (
    comunes,
    requerimiento,
    especificacion_diseno,
    estado,
)
"""Módulos que definen los tipos que pueden aparecer dentro del estado."""


def tipos_permitidos() -> list[tuple[str, str]]:
    """Lista los tipos que el serializador puede reconstruir desde un punto de control.

    Son las particiones del estado y todas las enumeraciones de los módulos del estado: los
    modelos anidados se reconstruyen a partir de su partición, pero las enumeraciones se
    serializan como tipos propios.

    Returns:
        Pares (módulo, nombre) ordenados.
    """
    tipos = {(clase.__module__, clase.__name__) for clase in PARTICIONES}
    for modulo in MODULOS_DEL_ESTADO:
        for objeto in vars(modulo).values():
            if (
                isinstance(objeto, type)
                and issubclass(objeto, Enum)
                and objeto.__module__ == modulo.__name__
            ):
                tipos.add((objeto.__module__, objeto.__name__))
    return sorted(tipos)


def serializador() -> JsonPlusSerializer:
    """Crea el serializador de los puntos de control con la lista blanca del estado.

    Con una lista blanca explícita, LangGraph bloquea cualquier tipo propio que no figure en
    ella, de modo que un tipo nuevo en el estado debe registrarse aquí.

    Returns:
        Serializador que reconstruye las particiones del estado al reanudar.
    """
    return JsonPlusSerializer(allowed_msgpack_modules=tipos_permitidos())
