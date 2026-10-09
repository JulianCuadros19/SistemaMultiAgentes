"""Ejecución de sesiones sobre el grafo compilado: iniciar, avanzar y consultar la pausa."""

import uuid
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from pydantic import BaseModel, ConfigDict

from multiagente.orquestador.estado import Fase

RespuestaPausa = str | dict[str, str]
"""Respuesta a una pausa: texto del cliente en el diálogo o decisión en un punto de control."""


class Pausa(BaseModel):
    """Punto en el que el grafo espera a una persona y los datos que debe revisar."""

    model_config = ConfigDict(frozen=True)

    punto: str
    datos: dict[str, Any]


class Avance(BaseModel):
    """Resultado de una ejecución hasta la siguiente pausa o hasta el final."""

    model_config = ConfigDict(frozen=True)

    nodos: tuple[str, ...]
    pausa: Pausa | None
    fase: Fase | None


def configuracion_hilo(id_sesion: str) -> RunnableConfig:
    """Configuración de LangGraph para una sesión: el hilo es el identificador de la sesión.

    Args:
        id_sesion: Identificador de la sesión.

    Returns:
        Configuración con el `thread_id` de la sesión.
    """
    return {"configurable": {"thread_id": id_sesion}}


def pausa_pendiente(app: CompiledStateGraph, id_sesion: str) -> Pausa | None:
    """Devuelve la pausa en la que está detenida la sesión, si la hay.

    Args:
        app: Grafo compilado con checkpointer.
        id_sesion: Identificador de la sesión.

    Returns:
        La pausa pendiente, o None si la sesión terminó o aún no ha empezado.
    """
    interrupciones = app.get_state(configuracion_hilo(id_sesion)).interrupts
    if not interrupciones:
        return None
    valor = dict(interrupciones[0].value)
    return Pausa(punto=valor.pop("punto"), datos=valor)


def _ejecutar(
    app: CompiledStateGraph, entrada: dict[str, str] | Command | None, id_sesion: str
) -> Avance:
    nodos: list[str] = []
    for actualizacion in app.stream(
        entrada, configuracion_hilo(id_sesion), stream_mode="updates", durability="sync"
    ):
        nodos.extend(nombre for nombre in actualizacion if nombre != "__interrupt__")
    sesion = app.get_state(configuracion_hilo(id_sesion)).values.get("sesion")
    return Avance(
        nodos=tuple(nodos),
        pausa=pausa_pendiente(app, id_sesion),
        fase=sesion.fase if sesion else None,
    )


def iniciar_sesion(
    app: CompiledStateGraph,
    cliente: str,
    proyecto: str,
    necesidad: str,
    id_sesion: str | None = None,
) -> tuple[str, Avance]:
    """Abre una sesión nueva con la necesidad del cliente y la ejecuta hasta la primera pausa.

    Cada paso se guarda antes de ejecutar el siguiente (`durability="sync"`), de modo que una
    interrupción del proceso no pierde trabajo ya hecho (RNF-02).

    Args:
        app: Grafo compilado con checkpointer.
        cliente: Nombre del cliente de la sesión.
        proyecto: Proyecto al que pertenecen los requerimientos.
        necesidad: Primera intervención del cliente, con la que se abre la elicitación.
        id_sesion: Identificador a usar; si se omite, se genera uno.

    Returns:
        El identificador de la sesión y el avance hasta la primera pausa.
    """
    id_sesion = id_sesion or str(uuid.uuid4())
    entrada = {"cliente": cliente, "proyecto": proyecto, "necesidad": necesidad}
    return id_sesion, _ejecutar(app, entrada, id_sesion)


def avanzar(
    app: CompiledStateGraph, id_sesion: str, respuesta: RespuestaPausa | None = None
) -> Avance:
    """Reanuda una sesión hasta la siguiente pausa o hasta el final.

    Args:
        app: Grafo compilado con checkpointer.
        id_sesion: Identificador de la sesión.
        respuesta: Respuesta a la pausa pendiente. Si es None, continúa desde el último punto
            de control guardado, como tras una caída del proceso.

    Returns:
        El avance hasta la siguiente pausa o el final.
    """
    entrada = None if respuesta is None else Command(resume=respuesta)
    return _ejecutar(app, entrada, id_sesion)
