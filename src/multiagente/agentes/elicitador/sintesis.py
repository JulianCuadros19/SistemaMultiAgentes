"""Síntesis de la historia de usuario y de los requerimientos formales (N5, Anexo A).

El modelo redacta el contenido. El código asigna los campos deterministas: identificadores,
versión, proyecto, autor, título, prioridad heredada de la historia y nombres de los datos como
identificadores (`numero_predial`). Descarta las oraciones de
la precondición y de la regla, y los datos, que no están respaldados por lo que dijo el cliente
(`fidelidad`). Después valida contra los esquemas del Anexo A y traduce las etiquetas de
contexto citadas a referencias estables (RF-04).
"""

import re

from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, ConfigDict, ValidationError

from multiagente.agentes.elicitador.calidad import identificador
from multiagente.agentes.elicitador.contexto import etiquetar, json_texto, mensaje_contexto
from multiagente.agentes.elicitador.dialogo import DatoEntradaModelo, DatoSalidaModelo
from multiagente.agentes.elicitador.fidelidad import (
    oraciones_respaldadas,
    raices_del_cliente,
    respaldado,
)
from multiagente.core.esquemas.comunes import Enunciado, Impacto, Prioridad
from multiagente.core.esquemas.requerimiento import (
    DatoEntrada,
    DatoSalida,
    Descripcion,
    EscenarioAceptacion,
    HistoriaUsuario,
    RequerimientoFormal,
    TipoSolicitud,
)
from multiagente.llm.invocador import ErrorValidacionSalida
from multiagente.orquestador.estado import Contexto, Conversacion, Requerimientos
from multiagente.orquestador.servicios import Sintesis

AUTOR = "Agente elicitador"
"""Autor que registra la ficha del requerimiento (Anexo A)."""

POR_CONFIRMAR = "Por confirmar con el cliente."
"""Texto de un campo obligatorio que la conversación no llegó a capturar (eli-003).

Es un marcador de pendiente: la verificación de calidad lo detecta como defecto que requiere al
cliente y escala el requerimiento al analista, en lugar de que el modelo invente el contenido.
"""


class EnunciadoModelo(BaseModel):
    """Historia en sus tres partes, tal como la devuelve el modelo."""

    model_config = ConfigDict(extra="forbid")

    como: str
    quiero: str
    para: str


class HistoriaModelo(BaseModel):
    """Historia de usuario del backlog, tal como la devuelve el modelo."""

    model_config = ConfigDict(extra="forbid")

    enunciado: EnunciadoModelo
    epica: str | None
    prioridad: Prioridad
    supuestos: list[str]
    preguntas_abiertas: list[str]


class EscenarioModelo(BaseModel):
    """Escenario Gherkin, tal como lo devuelve el modelo."""

    model_config = ConfigDict(extra="forbid")

    nombre: str
    dado_que: str
    cuando: str
    entonces: str


class RequerimientoModelo(BaseModel):
    """Contenido de una ficha de requerimiento, tal como lo devuelve el modelo."""

    model_config = ConfigDict(extra="forbid")

    tipo_solicitud: TipoSolicitud
    impacto: Impacto
    modulo: str
    riesgo: str | None
    area_funcional: str
    funcional_responsable: str | None
    precondicion: str
    regla_negocio: str
    datos_entrada: list[DatoEntradaModelo]
    datos_salida: list[DatoSalidaModelo]
    escenarios: list[EscenarioModelo]
    relacionados: list[int]
    fuentes: list[str]


class SalidaSintesis(BaseModel):
    """Salida estructurada de N5: una historia y los requerimientos que la desarrollan."""

    model_config = ConfigDict(extra="forbid")

    historia: HistoriaModelo
    requerimientos: list[RequerimientoModelo]


def mensajes_sintesis(
    conversacion: Conversacion, contexto: Contexto, previos: Requerimientos, proyecto: str
) -> list[ChatCompletionMessageParam]:
    """Arma los mensajes de datos de N5.

    En una corrección incluye los artefactos previos y los defectos que N6 encontró en ellos.

    Args:
        conversacion: Conversación cerrada por N4.
        contexto: Contexto recuperado en N2.
        previos: Artefactos y defectos de la síntesis anterior, si la hubo.
        proyecto: Proyecto de la sesión.

    Returns:
        Dos mensajes de datos que acompañan al prompt de sistema.
    """
    datos: dict[str, object] = {
        "proyecto": proyecto,
        "registro": conversacion.registro.model_dump(mode="json"),
        "transcripcion": [
            {"emisor": turno.emisor.value, "texto": turno.texto} for turno in conversacion.turnos
        ],
        "observaciones_revisor": list(conversacion.observaciones_revisor),
    }
    if previos.defectos:
        datos["correccion"] = {
            "artefactos_previos": {
                "historias": [h.model_dump(mode="json") for h in previos.historias],
                "requerimientos": [r.model_dump(mode="json") for r in previos.requerimientos],
            },
            "defectos": list(previos.defectos),
        }
    return [mensaje_contexto(contexto), {"role": "user", "content": json_texto(datos)}]


def _corrido(texto: str) -> str:
    """Une en un solo párrafo un texto con saltos de línea, reales o escritos como barra y n."""
    return re.sub(r"(?:\\n|\s)+", " ", texto).strip()


def _clausula(texto: str, claves: tuple[str, ...]) -> str:
    """Quita la palabra clave Gherkin que el modelo repite al inicio de la cláusula.

    El esquema guarda «dado que», «cuando» y «entonces» en campos separados: la palabra clave la
    pone quien presenta el escenario, no el texto.
    """
    limpio = _corrido(texto)
    patron = re.compile(rf"^(?:{'|'.join(claves)})\b[\s,:]*", re.IGNORECASE)
    while (sin_clave := patron.sub("", limpio)) != limpio:
        limpio = sin_clave
    return limpio.rstrip(".").strip()


def _texto(valor: str | None) -> str | None:
    limpio = valor.strip() if valor else ""
    return limpio or None


def _textos(valores: list[str]) -> list[str]:
    return list(dict.fromkeys(limpio for valor in valores if (limpio := valor.strip())))


def _errores(error: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(parte) for parte in detalle['loc'])}: {detalle['msg']}"
        for detalle in error.errors()
    )


def validar_sintesis(
    salida: SalidaSintesis,
    conversacion: Conversacion,
    contexto: Contexto,
    previos: Requerimientos,
    proyecto: str,
) -> Sintesis:
    """Completa los campos deterministas, filtra lo no dicho, valida y traduce las fuentes.

    Args:
        salida: Salida del modelo.
        conversacion: Conversación de la que salen los requerimientos.
        contexto: Contexto con el que se invocó al modelo.
        previos: Artefactos de la síntesis anterior; dan el número de versión.
        proyecto: Proyecto de la sesión.

    Returns:
        Historia, requerimientos y referencias al contexto de cada requerimiento.

    Raises:
        ErrorValidacionSalida: Si algún artefacto incumple el Anexo A, si la precondición, la
            regla o los datos no se apoyan en lo que dijo el cliente, o si cita una etiqueta que
            no existe o no cita ninguna.
    """
    problemas: list[str] = []
    etiquetas = etiquetar(contexto)
    fuente = raices_del_cliente(conversacion)
    # Si N4 cerró por límite de turnos, lo que falta se declara pendiente en lugar de inventarlo.
    incompleto = conversacion.registro.pendientes not in ([], ["confirmacion"])
    try:
        historia = HistoriaUsuario(
            id="HU-01",
            enunciado=Enunciado(**salida.historia.enunciado.model_dump()),
            epica=_texto(salida.historia.epica),
            prioridad=salida.historia.prioridad,
            supuestos=_textos(salida.historia.supuestos),
            preguntas_abiertas=_textos(salida.historia.preguntas_abiertas),
        )
    except ValidationError as error:
        raise ErrorValidacionSalida([f"historia: {_errores(error)}"]) from error
    if not salida.requerimientos:
        raise ErrorValidacionSalida(["Debes producir al menos un requerimiento formal."])

    version = f"0.{previos.sintesis + 1}"
    total = len(salida.requerimientos)
    requerimientos: list[RequerimientoFormal] = []
    referencias: dict[str, tuple[str, ...]] = {}
    for numero, contenido in enumerate(salida.requerimientos, 1):
        id_rf = f"RF-{numero:02d}"
        precondicion = oraciones_respaldadas(_corrido(contenido.precondicion), fuente)
        regla = oraciones_respaldadas(_corrido(contenido.regla_negocio), fuente)
        entradas = [d for d in contenido.datos_entrada if respaldado(d.nombre, fuente)]
        salidas = [d for d in contenido.datos_salida if respaldado(d.nombre, fuente)]
        if incompleto:
            precondicion = precondicion or POR_CONFIRMAR
            regla = regla or POR_CONFIRMAR
        for campo, valor in (
            ("precondicion", precondicion),
            ("regla_negocio", regla),
            ("datos_entrada", entradas),
            ("datos_salida", salidas),
        ):
            if not valor and not (incompleto and campo.startswith("datos")):
                problemas.append(
                    f"{id_rf}: {campo} no contiene nada de lo que dijo el cliente; "
                    "usa solo el registro y la transcripción."
                )
        if not contenido.fuentes:
            problemas.append(f"{id_rf}: cita al menos un fragmento del contexto en fuentes.")
        if desconocidas := sorted(set(contenido.fuentes) - set(etiquetas)):
            problemas.append(
                f"{id_rf}: las fuentes {desconocidas} no existen; usa solo las etiquetas "
                "del contexto."
            )
        if invalidos := [p for p in contenido.relacionados if not 1 <= p <= total or p == numero]:
            problemas.append(
                f"{id_rf}: relacionados {invalidos} no son posiciones de otros "
                f"requerimientos entre 1 y {total}."
            )
        try:
            requerimiento = RequerimientoFormal(
                id_requerimiento=id_rf,
                version=version,
                proyecto=proyecto,
                tipo_solicitud=contenido.tipo_solicitud,
                impacto=contenido.impacto,
                modulo=contenido.modulo,
                riesgo=_texto(contenido.riesgo),
                autor=AUTOR,
                area_funcional=contenido.area_funcional,
                funcional_responsable=_texto(contenido.funcional_responsable),
                titulo=historia.enunciado,
                descripcion=Descripcion(
                    precondicion=precondicion,
                    regla_negocio=regla,
                    datos_entrada=[
                        DatoEntrada(
                            nombre=identificador(dato.nombre),
                            tipo=dato.tipo,
                            obligatorio=dato.obligatorio,
                            restriccion=_texto(dato.restriccion),
                        )
                        for dato in entradas
                    ],
                    datos_salida=[
                        DatoSalida(
                            nombre=identificador(dato.nombre),
                            tipo=dato.tipo,
                            formato=_texto(dato.formato),
                        )
                        for dato in salidas
                    ],
                ),
                criterios_aceptacion=[
                    EscenarioAceptacion(
                        id=f"ESC-{posicion:02d}",
                        nombre=_texto(escenario.nombre),
                        dado_que=_clausula(escenario.dado_que, ("dado que", "dado")),
                        cuando=_clausula(escenario.cuando, ("cuando",)),
                        entonces=_clausula(escenario.entonces, ("entonces",)),
                    )
                    for posicion, escenario in enumerate(contenido.escenarios, 1)
                ],
                prioridad=historia.prioridad,
                requerimientos_relacionados=sorted(
                    {
                        f"RF-{p:02d}"
                        for p in contenido.relacionados
                        if 1 <= p <= total and p != numero
                    }
                ),
            )
        except ValidationError as error:
            problemas.append(f"{id_rf}: {_errores(error)}")
            continue
        requerimientos.append(requerimiento)
        referencias[id_rf] = tuple(
            dict.fromkeys(etiquetas[f].referencia for f in contenido.fuentes if f in etiquetas)
        )
    if problemas:
        raise ErrorValidacionSalida(problemas)
    return Sintesis(
        historias=(historia,), requerimientos=tuple(requerimientos), referencias=referencias
    )
