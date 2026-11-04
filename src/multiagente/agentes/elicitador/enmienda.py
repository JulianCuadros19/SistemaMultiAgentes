"""Enmienda de los requerimientos aprobados desde la aprobación final (N5 en modo enmienda).

Una persona descubrió en N17 una regla que los requerimientos no tienen y la escribió como
enmienda (ADR-0015). El modelo la incorpora a los requerimientos vigentes, sin contexto
recuperado, porque el contexto ya está en ellos. De cada requerimiento afectado devuelve la regla
de negocio completa y vigente, los escenarios existentes que la regla obliga a precisar y los
nuevos.

El código conserva lo demás y valida:
- solo se enmiendan requerimientos vigentes: ninguno se agrega, se quita ni se renumera;
- los escenarios precisados conservan su identificador, los que no se devuelven quedan como
  estaban, y los nuevos toman los identificadores siguientes, de modo que ninguno se elimina;
- cada oración de la regla se apoya en la enmienda, en las observaciones del analista, en lo
  que dijo el cliente o en el texto vigente del requerimiento (`fidelidad`);
- el requerimiento enmendado sube a la versión siguiente; los demás, la historia, los títulos y
  las referencias no cambian.
"""

from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, ConfigDict, ValidationError

from multiagente.agentes.contexto import json_texto
from multiagente.agentes.elicitador.fidelidad import (
    oraciones,
    raices,
    raices_del_cliente,
    respaldado,
)
from multiagente.agentes.elicitador.sintesis import (
    EscenarioModelo,
    clausula,
    corrido,
    errores_de_esquema,
    texto_opcional,
)
from multiagente.core.esquemas.requerimiento import RequerimientoFormal
from multiagente.llm.invocador import ErrorValidacionSalida
from multiagente.orquestador.estado import Conversacion, Requerimientos
from multiagente.orquestador.servicios import Sintesis

CAMPOS_PARA_EL_MODELO = {
    "id_requerimiento",
    "version",
    "titulo",
    "descripcion",
    "criterios_aceptacion",
    "requerimientos_relacionados",
}
"""Campos de cada requerimiento vigente que el modelo necesita para enmendarlo."""


class EscenarioPrecisadoModelo(BaseModel):
    """Escenario existente que la enmienda precisa, con su identificador vigente."""

    model_config = ConfigDict(extra="forbid")

    id: str
    nombre: str
    dado_que: str
    cuando: str
    entonces: str


class RequerimientoEnmendadoModelo(BaseModel):
    """Lo que cambia en un requerimiento afectado por la enmienda, como lo devuelve el modelo."""

    model_config = ConfigDict(extra="forbid")

    id_requerimiento: str
    regla_negocio: str
    escenarios_precisados: list[EscenarioPrecisadoModelo]
    escenarios_nuevos: list[EscenarioModelo]


class SalidaEnmienda(BaseModel):
    """Salida estructurada de N5 en modo enmienda: los requerimientos afectados."""

    model_config = ConfigDict(extra="forbid")

    requerimientos: list[RequerimientoEnmendadoModelo]


def mensajes_enmienda(
    requerimientos: Requerimientos, proyecto: str
) -> list[ChatCompletionMessageParam]:
    """Arma el mensaje de datos de N5 en modo enmienda.

    Lleva los requerimientos vigentes, la enmienda en curso, las observaciones del analista y
    los defectos que N6 encontró en la vuelta anterior. No lleva contexto recuperado.

    Args:
        requerimientos: Requerimientos vigentes, con la enmienda en curso y sus defectos.
        proyecto: Proyecto de la sesión.

    Returns:
        El mensaje de datos que acompaña al prompt de sistema.

    Raises:
        ValueError: Si no hay una enmienda en curso.
    """
    enmienda = requerimientos.enmienda
    if enmienda is None:
        raise ValueError("No hay una enmienda en curso que incorporar")
    datos = {
        "proyecto": proyecto,
        "requerimientos": [
            requerimiento.model_dump(mode="json", include=CAMPOS_PARA_EL_MODELO)
            for requerimiento in requerimientos.requerimientos
        ],
        "enmienda": enmienda.texto,
        "observaciones_analista": list(enmienda.observaciones_analista),
        "defectos": list(requerimientos.defectos),
    }
    return [{"role": "user", "content": json_texto(datos)}]


def texto_vigente(requerimiento: RequerimientoFormal) -> str:
    """Texto vigente de un requerimiento, que también respalda su regla enmendada.

    Args:
        requerimiento: Requerimiento antes de la enmienda.

    Returns:
        Título, precondición, regla, datos y escenarios en un solo texto.
    """
    titulo = requerimiento.titulo
    descripcion = requerimiento.descripcion
    partes = [titulo.como, titulo.quiero, titulo.para]
    partes += [descripcion.precondicion, descripcion.regla_negocio]
    partes += [f"{dato.nombre} {dato.restriccion or ''}" for dato in descripcion.datos_entrada]
    partes += [f"{dato.nombre} {dato.formato or ''}" for dato in descripcion.datos_salida]
    partes += [
        f"{escenario.nombre or ''} {escenario.dado_que} {escenario.cuando} {escenario.entonces}"
        for escenario in requerimiento.criterios_aceptacion
    ]
    return " ".join(partes)


def _escenario(
    id_escenario: str, escenario: EscenarioModelo | EscenarioPrecisadoModelo
) -> dict[str, object]:
    return {
        "id": id_escenario,
        "nombre": texto_opcional(escenario.nombre),
        "dado_que": clausula(escenario.dado_que, ("dado que", "dado")),
        "cuando": clausula(escenario.cuando, ("cuando",)),
        "entonces": clausula(escenario.entonces, ("entonces",)),
    }


def _enmendar_uno(
    contenido: RequerimientoEnmendadoModelo,
    vigente: RequerimientoFormal,
    fuente: set[str],
    version: str,
) -> tuple[RequerimientoFormal | None, list[str]]:
    """Aplica a un requerimiento vigente lo que devolvió el modelo.

    Returns:
        El requerimiento enmendado, o None si no cambia o no es válido, y los problemas.
    """
    id_rf = vigente.id_requerimiento
    problemas: list[str] = []
    partes = oraciones(corrido(contenido.regla_negocio))
    if not partes:
        problemas.append(f"{id_rf}: la regla_negocio está vacía; devuélvela completa y vigente.")
    if sin_respaldo := [oracion for oracion in partes if not respaldado(oracion, fuente)]:
        problemas.append(
            f"{id_rf}: estas oraciones de la regla_negocio no se apoyan en la enmienda, en las "
            f"observaciones del analista ni en el requerimiento vigente: {sin_respaldo}. Usa sus "
            "palabras y no agregues reglas que nadie dijo."
        )
    vigentes = {escenario.id: escenario for escenario in vigente.criterios_aceptacion}
    precisados = {}
    for escenario in contenido.escenarios_precisados:
        id_escenario = escenario.id.strip().upper()
        if id_escenario not in vigentes:
            problemas.append(
                f"{id_rf}: {escenario.id} no es un escenario vigente ({', '.join(vigentes)}); los "
                "escenarios nuevos van en escenarios_nuevos, sin id."
            )
        elif id_escenario in precisados:
            problemas.append(f"{id_rf}: precisas {id_escenario} dos veces; hazlo una sola vez.")
        else:
            precisados[id_escenario] = escenario
    if problemas:
        return None, problemas
    siguiente = max(int(id_escenario.removeprefix("ESC-")) for id_escenario in vigentes) + 1
    escenarios = [
        _escenario(id_escenario, precisados[id_escenario])
        if id_escenario in precisados
        else escenario.model_dump(mode="json")
        for id_escenario, escenario in vigentes.items()
    ]
    escenarios += [
        _escenario(f"ESC-{siguiente + desplazamiento:02d}", nuevo)
        for desplazamiento, nuevo in enumerate(contenido.escenarios_nuevos)
    ]
    descripcion = vigente.descripcion.model_dump(mode="json")
    try:
        enmendado = RequerimientoFormal.model_validate(
            {
                **vigente.model_dump(mode="json"),
                "version": version,
                "descripcion": {**descripcion, "regla_negocio": " ".join(partes)},
                "criterios_aceptacion": escenarios,
            }
        )
    except ValidationError as error:
        return None, [f"{id_rf}: {errores_de_esquema(error)}"]
    sin_version = {"version"}
    if enmendado.model_dump(exclude=sin_version) == vigente.model_dump(exclude=sin_version):
        return None, []
    return enmendado, []


def validar_enmienda(
    salida: SalidaEnmienda, conversacion: Conversacion, requerimientos: Requerimientos
) -> Sintesis:
    """Aplica la enmienda del modelo a los requerimientos vigentes y la valida.

    Args:
        salida: Salida del modelo.
        conversacion: Conversación de la sesión: lo que dijo el cliente respalda la regla.
        requerimientos: Requerimientos vigentes, con la enmienda en curso; su número de síntesis
            da la versión de los enmendados.

    Returns:
        La historia, los requerimientos y las referencias, con los afectados enmendados.

    Raises:
        ErrorValidacionSalida: Si el modelo enmienda un requerimiento que no existe o lo repite,
            precisa un escenario que no existe, deja la regla vacía o con oraciones que nada
            respalda, incumple el Anexo A, o no cambia ningún requerimiento.
        ValueError: Si no hay una enmienda en curso.
    """
    enmienda = requerimientos.enmienda
    if enmienda is None:
        raise ValueError("No hay una enmienda en curso que incorporar")
    vigentes = {r.id_requerimiento: r for r in requerimientos.requerimientos}
    comun = (
        raices_del_cliente(conversacion)
        | raices(enmienda.texto)
        | raices(" ".join(enmienda.observaciones_analista))
    )
    version = f"0.{requerimientos.sintesis + 1}"
    problemas: list[str] = []
    enmendados: dict[str, RequerimientoFormal] = {}
    vistos: set[str] = set()
    for contenido in salida.requerimientos:
        id_rf = contenido.id_requerimiento.strip().upper()
        vigente = vigentes.get(id_rf)
        if vigente is None:
            problemas.append(
                f"{contenido.id_requerimiento} no es un requerimiento vigente: enmienda solo "
                f"{', '.join(vigentes)}, sin agregar ni renumerar requerimientos."
            )
            continue
        if id_rf in vistos:
            problemas.append(f"{id_rf} aparece dos veces: devuelve cada requerimiento una vez.")
            continue
        vistos.add(id_rf)
        fuente = comun | raices(texto_vigente(vigente))
        enmendado, propios = _enmendar_uno(contenido, vigente, fuente, version)
        problemas += propios
        if enmendado is not None:
            enmendados[id_rf] = enmendado
    if not problemas and not enmendados:
        problemas.append(
            "La enmienda no cambió ningún requerimiento: incorpora la regla nueva en la "
            "regla_negocio del requerimiento al que aplica y agrega un escenario que la verifique."
        )
    if problemas:
        raise ErrorValidacionSalida(problemas)
    return Sintesis(
        historias=requerimientos.historias,
        requerimientos=tuple(
            enmendados.get(requerimiento.id_requerimiento, requerimiento)
            for requerimiento in requerimientos.requerimientos
        ),
        referencias=requerimientos.referencias,
    )
