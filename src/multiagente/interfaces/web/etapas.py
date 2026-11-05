"""Etapas de una sesión para la línea del flujo de la web (ADR-0018).

La página de la sesión muestra el recorrido en cinco etapas, que agrupan los diecisiete nodos:
- la conversación (N1 a N4);
- los requerimientos (N5 y N6);
- el diseño (N7 a N9 y N16);
- el desarrollo y las pruebas (N10 a N15);
- la aprobación final (N17).

Cada etapa queda hecha, actual o pendiente según lo que ya existe en el estado, no según el orden.
Así se ve bien también después de una enmienda o de una devolución desde N17, cuando el flujo
vuelve a una etapa anterior con las siguientes ya recorridas.

El panel agrupa las sesiones según quién debe actuar y repite la línea en miniatura; la vista del
cliente la resume en cuatro pasos de su lenguaje.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from multiagente.interfaces.operacion import VistaSesion
from multiagente.orquestador.estado import (
    PAUSA_PRESUPUESTO,
    Decision,
    EstadoGrafo,
    Fase,
    PuntoControl,
)
from multiagente.orquestador.grafo import Nodo

Clave = Literal["conversacion", "requerimientos", "diseno", "desarrollo", "final"]
EstadoEtapa = Literal["hecha", "actual", "pendiente"]
Tono = Literal["espera", "procesa", "alerta", "ok", "neutro"]
Grupo = Literal["equipo", "curso", "terminadas"]

CLAVES: tuple[Clave, ...] = ("conversacion", "requerimientos", "diseno", "desarrollo", "final")

NOMBRES: dict[Clave, str] = {
    "conversacion": "Conversación",
    "requerimientos": "Requerimientos",
    "diseno": "Diseño",
    "desarrollo": "Desarrollo y pruebas",
    "final": "Aprobación final",
}

PUNTO_DE_CONTROL: dict[Clave, str] = {
    "requerimientos": "N6",
    "diseno": "N9",
    "final": "N17",
}
"""Etapas que terminan en un punto de control humano y el nodo de ese punto."""

ETAPA_DE_NODO: dict[str, Clave] = {
    **{nodo.value: "conversacion" for nodo in (Nodo.N1, Nodo.N2, Nodo.N3, Nodo.N4)},
    **{nodo.value: "requerimientos" for nodo in (Nodo.N5, Nodo.N6)},
    **{nodo.value: "diseno" for nodo in (Nodo.N7, Nodo.N8, Nodo.N9, Nodo.N16)},
    **{
        nodo.value: "desarrollo"
        for nodo in (Nodo.N10, Nodo.N11, Nodo.N12, Nodo.N13, Nodo.N14, Nodo.N15)
    },
    Nodo.N17.value: "final",
}

ETAPA_DE_PAUSA: dict[str, Clave] = {
    "dialogo": "conversacion",
    PuntoControl.REQUERIMIENTOS.value: "requerimientos",
    PuntoControl.ESPECIFICACION.value: "diseno",
    PuntoControl.FINAL.value: "final",
}

ETAPA_DE_FASE: dict[Fase, Clave] = {
    Fase.DISENO: "diseno",
    Fase.DESARROLLO: "desarrollo",
    Fase.APROBACION_FINAL: "final",
    Fase.VALIDADO: "final",
    Fase.REQUIERE_INTERVENCION: "final",
}


@dataclass(frozen=True)
class Etapa:
    """Una etapa de la línea del flujo, lista para dibujar.

    Attributes:
        clave: Identificador estable de la etapa, que usan las pestañas y los anclajes.
        nombre: Nombre de la etapa para la persona.
        punto: Nodo del punto de control humano con que termina, si lo tiene.
        estado: Hecha, actual o pendiente.
        tono: Color de estado de la etapa actual: espera de una persona, procesa, alerta, ok o
            neutro. Las demás no llevan tono.
        detalle: Texto breve bajo el nombre.
    """

    clave: Clave
    nombre: str
    punto: str | None
    estado: EstadoEtapa
    tono: Tono | None
    detalle: str


def etapa_actual(vista: VistaSesion, estado: EstadoGrafo) -> Clave:
    """Etapa en la que está la sesión.

    Args:
        vista: Vista de la sesión.
        estado: Estado del grafo de la sesión.

    Returns:
        La etapa de la pausa, la del nodo donde se detuvo o, si no hay ninguna, la de su fase.
    """
    pausa = vista.pausa
    if pausa is not None and pausa.punto in ETAPA_DE_PAUSA:
        return ETAPA_DE_PAUSA[pausa.punto]
    if pausa is not None and pausa.punto == PAUSA_PRESUPUESTO:
        return ETAPA_DE_NODO.get(str(pausa.datos.get("nodo")), _alcanzada(estado))
    if vista.pendientes:
        return ETAPA_DE_NODO.get(vista.pendientes[0], _alcanzada(estado))
    if vista.fase is Fase.CERRADA or vista.fase is Fase.ELICITACION:
        return _alcanzada(estado)
    return ETAPA_DE_FASE.get(vista.fase, _alcanzada(estado))


def _alcanzada(estado: EstadoGrafo) -> Clave:
    """La etapa más avanzada que dejó algo en el estado."""
    if estado["codigo"].versiones:
        return "desarrollo"
    if estado["arquitectura"].especificacion is not None:
        return "diseno"
    if estado["requerimientos"].requerimientos:
        return "requerimientos"
    return "conversacion"


def _aprobada(estado: EstadoGrafo, punto: PuntoControl) -> str | None:
    """Revisor de la última aprobación en ese punto de control, si la última fue aprobar."""
    aprobacion = estado["sesion"].ultima_aprobacion(punto)
    if aprobacion is not None and aprobacion.decision is Decision.APROBADO:
        return aprobacion.revisor
    return None


def _hecha(clave: Clave, vista: VistaSesion, estado: EstadoGrafo) -> str | None:
    """Detalle de una etapa ya recorrida, o None si todavía no se recorrió."""
    if clave == "conversacion":
        turnos = len(estado["conversacion"].turnos)
        hecha = bool(estado["requerimientos"].requerimientos) or vista.fase is not Fase.ELICITACION
        return f"{turnos} turnos" if hecha else None
    if clave == "requerimientos":
        revisor = _aprobada(estado, PuntoControl.REQUERIMIENTOS)
        return f"Aprobados por {revisor}" if revisor else None
    if clave == "diseno":
        revisor = _aprobada(estado, PuntoControl.ESPECIFICACION)
        return f"Aprobado por {revisor}" if revisor else None
    if clave == "desarrollo":
        versiones = len(estado["codigo"].versiones)
        if not versiones:
            return None
        return "1 versión" if versiones == 1 else f"{versiones} versiones"
    revisor = _aprobada(estado, PuntoControl.FINAL)
    return f"Validado por {revisor}" if vista.fase is Fase.VALIDADO and revisor else None


def tono_de(vista: VistaSesion, procesando: bool = False) -> tuple[Tono, str]:
    """Tono de la sesión y detalle breve de su etapa actual.

    Args:
        vista: Vista de la sesión.
        procesando: Si la web está avanzando la sesión en segundo plano.

    Returns:
        El tono según lo que espera la sesión, y el detalle que se muestra bajo la etapa.
    """
    pausa = vista.pausa
    if procesando or vista.en_curso:
        return "procesa", "Procesando"
    if vista.fase is Fase.VALIDADO:
        return "ok", "Validado"
    if vista.fase is Fase.CERRADA:
        return "neutro", "Cerrada aquí"
    if vista.detenida:
        return "alerta", "Detenida por una falla"
    if pausa is None:
        return "procesa", "En curso"
    if pausa.punto == PAUSA_PRESUPUESTO:
        return "alerta", "Sin presupuesto"
    if pausa.punto == "dialogo":
        return "espera", "Espera al cliente"
    if pausa.datos.get("escalado"):
        return "alerta", "Escalada"
    return "espera", "Espera su decisión"


def etapas_de(
    vista: VistaSesion, estado: EstadoGrafo, procesando: bool = False
) -> tuple[list[Etapa], Clave]:
    """Las cinco etapas de la sesión y la que debe abrirse al entrar.

    Args:
        vista: Vista de la sesión.
        estado: Estado del grafo de la sesión.
        procesando: Si la web está avanzando la sesión en segundo plano.

    Returns:
        Las etapas en orden y la clave de la etapa actual, que es la que se abre.
    """
    actual = etapa_actual(vista, estado)
    tono, detalle_actual = tono_de(vista, procesando)
    etapas = []
    for clave in CLAVES:
        hecha = _hecha(clave, vista, estado)
        if clave == actual and not (vista.fase is Fase.VALIDADO and hecha):
            etapas.append(
                Etapa(
                    clave,
                    NOMBRES[clave],
                    PUNTO_DE_CONTROL.get(clave),
                    "actual",
                    tono,
                    detalle_actual,
                )
            )
        elif hecha is not None:
            etapas.append(
                Etapa(clave, NOMBRES[clave], PUNTO_DE_CONTROL.get(clave), "hecha", None, hecha)
            )
        else:
            etapas.append(
                Etapa(
                    clave,
                    NOMBRES[clave],
                    PUNTO_DE_CONTROL.get(clave),
                    "pendiente",
                    None,
                    "Pendiente",
                )
            )
    return etapas, actual


# Panel ------------------------------------------------------------------------------------------

GRUPOS: tuple[tuple[Grupo, str], ...] = (
    ("equipo", "Esperan al equipo"),
    ("curso", "En curso o con el cliente"),
    ("terminadas", "Terminadas"),
)
"""Grupos del panel, en orden, con su título."""


def grupo_de(vista: VistaSesion, procesando: bool = False) -> Grupo:
    """Grupo del panel de una sesión, según quién debe actuar.

    Args:
        vista: Vista de la sesión.
        procesando: Si la web está avanzando la sesión en segundo plano.

    Returns:
        `terminadas` si se validó o se cerró; `curso` si avanza o espera al cliente; `equipo` si
        espera una decisión, que amplíen su presupuesto o que la reanuden tras una falla.
    """
    if vista.fase in (Fase.VALIDADO, Fase.CERRADA):
        return "terminadas"
    if procesando or vista.en_curso or (vista.pausa is not None and vista.pausa.punto == "dialogo"):
        return "curso"
    return "equipo"


@dataclass(frozen=True)
class FilaPanel:
    """Una sesión del panel, lista para dibujar.

    Attributes:
        vista: Vista de la sesión.
        etapas: Sus cinco etapas, para la línea en miniatura.
        tono: Tono de su estado.
        grupo: Grupo del panel en el que va.
        tarea: Lo que la web está haciendo con ella, si la avanza en segundo plano.
    """

    vista: VistaSesion
    etapas: tuple[Etapa, ...]
    tono: Tono
    grupo: Grupo
    tarea: str | None


def fila_del_panel(vista: VistaSesion, estado: EstadoGrafo, tarea: str | None = None) -> FilaPanel:
    """Arma la fila del panel de una sesión.

    Args:
        vista: Vista de la sesión.
        estado: Estado del grafo de la sesión.
        tarea: Descripción de lo que la web está haciendo con ella, si la avanza.

    Returns:
        La fila con sus etapas, su tono y su grupo.
    """
    procesando = tarea is not None
    etapas, _ = etapas_de(vista, estado, procesando)
    tono, _ = tono_de(vista, procesando)
    return FilaPanel(vista, tuple(etapas), tono, grupo_de(vista, procesando), tarea)


# Vista del cliente --------------------------------------------------------------------------------

PASOS_DEL_CLIENTE: tuple[tuple[str, tuple[Clave, ...]], ...] = (
    ("Conversación", ("conversacion",)),
    ("Revisión del equipo", ("requerimientos", "diseno")),
    ("Construcción y pruebas", ("desarrollo",)),
    ("Validación final", ("final",)),
)
"""Los cuatro pasos que ve el cliente y las etapas que agrupa cada uno."""


@dataclass(frozen=True)
class Paso:
    """Un paso del avance que ve el cliente.

    Attributes:
        nombre: Nombre del paso en el lenguaje del cliente.
        estado: Hecho, actual o pendiente.
    """

    nombre: str
    estado: EstadoEtapa


def pasos_del_cliente(etapas: Sequence[Etapa]) -> list[Paso]:
    """Resume las cinco etapas en los cuatro pasos que ve el cliente.

    Args:
        etapas: Las etapas de la sesión, de `etapas_de`.

    Returns:
        Un paso actual si alguna de sus etapas lo es; hecho si todas están hechas; si no, pendiente.
    """
    estados = {etapa.clave: etapa.estado for etapa in etapas}
    pasos = []
    for nombre, claves in PASOS_DEL_CLIENTE:
        suyos = [estados[clave] for clave in claves]
        if "actual" in suyos:
            pasos.append(Paso(nombre, "actual"))
        elif all(estado == "hecha" for estado in suyos):
            pasos.append(Paso(nombre, "hecha"))
        else:
            pasos.append(Paso(nombre, "pendiente"))
    return pasos
