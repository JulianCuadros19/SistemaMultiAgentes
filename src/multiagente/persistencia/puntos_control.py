"""Persistencia del estado del grafo mediante puntos de control (RF-28, RNF-02)."""

from collections.abc import Iterator
from contextlib import contextmanager
from enum import Enum
from types import ModuleType
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from psycopg import Connection
from psycopg.rows import dict_row

from multiagente.core.configuracion import ConfiguracionBaseDatos
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


@contextmanager
def abrir_checkpointer(
    configuracion: ConfiguracionBaseDatos | None = None,
) -> Iterator[PostgresSaver]:
    """Abre el checkpointer de PostgreSQL y crea sus tablas si no existen.

    La conexión usa `autocommit`, sin sentencias preparadas y con filas como diccionarios, como
    exige `PostgresSaver`. Se cierra al salir del contexto; una sesión se reanuda abriendo otro.

    Args:
        configuracion: Conexión a la base; si se omite, se lee del entorno.

    Yields:
        Checkpointer listo para compilar el grafo.
    """
    configuracion = configuracion or ConfiguracionBaseDatos()
    conexion: Connection[dict[str, Any]]
    with Connection.connect(
        configuracion.cadena_conexion(),
        autocommit=True,
        prepare_threshold=0,
        row_factory=dict_row,
    ) as conexion:
        checkpointer = PostgresSaver(conexion, serde=serializador())
        checkpointer.setup()
        yield checkpointer


def identificadores_de_sesion(checkpointer: BaseCheckpointSaver) -> list[str]:
    """Identificadores de las sesiones guardadas, de la más reciente a la más antigua.

    En PostgreSQL se consulta el último punto de control de cada hilo, sin cargar el estado; en
    memoria, para las pruebas, se toman las claves del almacenamiento.

    Args:
        checkpointer: Checkpointer del grafo compilado.

    Returns:
        El `thread_id` de cada sesión.
    """
    if isinstance(checkpointer, PostgresSaver):
        with checkpointer.lock, checkpointer.conn.cursor() as cursor:
            filas = cursor.execute(
                "SELECT thread_id FROM checkpoints WHERE checkpoint_ns = '' "
                "GROUP BY thread_id ORDER BY max(checkpoint_id) DESC"
            ).fetchall()
        return [fila["thread_id"] for fila in filas]
    if isinstance(checkpointer, InMemorySaver):
        return list(reversed(checkpointer.storage))
    hilos = (punto.config["configurable"]["thread_id"] for punto in checkpointer.list(None))
    return list(dict.fromkeys(hilos))
