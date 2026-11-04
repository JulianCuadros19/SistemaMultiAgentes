"""Selección de la arquitectura y registro de decisión (N8, primera llamada; RF-10).

El modelo elige del catálogo cerrado con los criterios de selección (arq-003) a la vista. El
código verifica las reglas obligatorias de la plantilla arq-001 y arma el registro en Markdown
con la estructura MADR, de modo que su forma no depende del modelo. Cada rediseño que atiende
observaciones del revisor agrega una revisión al registro, con la respuesta del modelo y los
cambios de la especificación, que calcula el código.
"""

import re
from datetime import date

from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, ConfigDict

from multiagente.agentes.arquitecto.contexto import mensaje_contexto
from multiagente.agentes.contexto import json_texto
from multiagente.llm.invocador import ErrorValidacionSalida
from multiagente.orquestador.estado import (
    Arquitectura,
    Contexto,
    FragmentoContexto,
    Requerimientos,
)

RF = re.compile(r"\bRF-\d{2,}\b")
ETIQUETA = re.compile(r"\bF\d+\b")


class OpcionModelo(BaseModel):
    """Arquitectura considerada, con su análisis."""

    model_config = ConfigDict(extra="forbid")

    id: str
    favorables: list[str]
    desfavorables: list[str]
    motivo_descarte: str | None


class SalidaSeleccion(BaseModel):
    """Salida de la selección: el contenido del registro de decisión."""

    model_config = ConfigDict(extra="forbid")

    titulo: str
    contexto: str
    factores: list[str]
    opciones: list[OpcionModelo]
    elegida: str
    justificacion: str
    consecuencias_favorables: list[str]
    consecuencias_desfavorables: list[str]
    confirmacion: str
    respuesta_observaciones: str


def mensajes_seleccion(
    requerimientos: Requerimientos, contexto: Contexto, previa: Arquitectura
) -> list[ChatCompletionMessageParam]:
    """Arma los mensajes de datos de la selección.

    Args:
        requerimientos: Requerimientos aprobados en N6.
        contexto: Contexto acumulado; solo se presenta el del arquitecto.
        previa: Diseño anterior, con su registro y las observaciones del revisor, si las hay.

    Returns:
        Dos mensajes de datos que acompañan al prompt de selección.
    """
    datos: dict[str, object] = {
        "historias": [h.model_dump(mode="json") for h in requerimientos.historias],
        "requerimientos": [r.model_dump(mode="json") for r in requerimientos.requerimientos],
        "observaciones_revisor": list(previa.observaciones_revisor),
        "observaciones_nuevas": list(
            previa.observaciones_revisor[previa.observaciones_atendidas :]
        ),
    }
    if previa.registro_decision:
        datos["registro_previo"] = previa.registro_decision
    return [mensaje_contexto(contexto), {"role": "user", "content": json_texto(datos)}]


def _textos(valores: list[str]) -> list[str]:
    return [limpio for valor in valores if (limpio := valor.strip())]


def validar_seleccion(
    salida: SalidaSeleccion,
    aprobados: set[str],
    arquitecturas: frozenset[str],
    observaciones_nuevas: bool = False,
) -> SalidaSeleccion:
    """Verifica las reglas obligatorias del registro de decisión (arq-001 y arq-003).

    Args:
        salida: Salida del modelo.
        aprobados: Identificadores de los requerimientos aprobados.
        arquitecturas: Identificadores del catálogo cerrado.
        observaciones_nuevas: Si el revisor dejó observaciones que ningún diseño atendió; la
            salida debe responderlas.

    Returns:
        La salida con los identificadores normalizados.

    Raises:
        ErrorValidacionSalida: Si incumple alguna regla.
    """
    opciones = [
        opcion.model_copy(update={"id": opcion.id.strip().upper()}) for opcion in salida.opciones
    ]
    salida = salida.model_copy(
        update={"opciones": opciones, "elegida": salida.elegida.strip().upper()}
    )
    identificadores = [opcion.id for opcion in opciones]
    problemas: list[str] = []
    if fuera := sorted(set(identificadores) - arquitecturas):
        problemas.append(f"Las opciones {fuera} no pertenecen al catálogo {sorted(arquitecturas)}.")
    if len(set(identificadores)) < 2 or len(set(identificadores)) != len(identificadores):
        problemas.append("Considera al menos dos arquitecturas distintas del catálogo.")
    if salida.elegida not in identificadores:
        problemas.append(f"La elegida {salida.elegida} debe estar entre las opciones consideradas.")
    descartadas = [o for o in opciones if o.id != salida.elegida]
    if not any(
        o.motivo_descarte and set(RF.findall(o.motivo_descarte)) & aprobados for o in descartadas
    ):
        problemas.append(
            "Al menos una opción descartada debe explicar su descarte citando un requerimiento "
            "aprobado."
        )
    if not set(RF.findall(salida.justificacion)) & aprobados:
        problemas.append("La justificación debe citar los requerimientos aprobados que la motivan.")
    textos = [salida.contexto, salida.justificacion, *(o.motivo_descarte or "" for o in opciones)]
    if ajenos := sorted({rf for texto in textos for rf in RF.findall(texto)} - aprobados):
        problemas.append(f"Se citan requerimientos que no están aprobados: {ajenos}.")
    if not _textos(salida.factores):
        problemas.append("Declara al menos un factor de decisión.")
    if not _textos(salida.consecuencias_desfavorables):
        problemas.append("Declara al menos una consecuencia desfavorable de la opción elegida.")
    if not salida.confirmacion.strip():
        problemas.append("Describe una confirmación verificable de la decisión.")
    if not salida.titulo.strip() or not salida.contexto.strip():
        problemas.append("El título y el contexto no pueden ir vacíos.")
    if observaciones_nuevas and not salida.respuesta_observaciones.strip():
        problemas.append(
            "Responde a las observaciones nuevas del revisor: qué cambia en la decisión y en la "
            "especificación, y por qué."
        )
    if problemas:
        raise ErrorValidacionSalida(problemas)
    return salida


def registro_de_decision(
    salida: SalidaSeleccion,
    titulos: dict[str, str],
    fecha: date,
    etiquetas: dict[str, FragmentoContexto] | None = None,
) -> str:
    """Arma el registro de decisión en Markdown con la estructura MADR de la plantilla arq-001.

    Las etiquetas `F1…Fn` que el modelo cite se reemplazan por la referencia estable del
    fragmento, que sí tiene sentido para quien lee el registro.

    Args:
        salida: Selección validada.
        titulos: Título de cada arquitectura del catálogo.
        fecha: Fecha del registro.
        etiquetas: Fragmentos por etiqueta, tal como se presentaron al modelo.

    Returns:
        El registro en Markdown.
    """

    def nombre(identificador: str) -> str:
        return f"{identificador} · {titulos.get(identificador, identificador)}"

    def con_fuentes(texto: str) -> str:
        return ETIQUETA.sub(
            lambda m: etiquetas[m[0]].referencia if etiquetas and m[0] in etiquetas else m[0],
            texto,
        )

    lineas = [
        "---",
        "estado: propuesta",
        f"fecha: {fecha.isoformat()}",
        "decisores: [Agente arquitecto]",
        "---",
        "",
        f"# Registro de decisión · {salida.titulo.strip()}",
        "",
        "## Contexto y planteamiento del problema",
        "",
        salida.contexto.strip(),
        "",
        "## Factores de decisión",
        "",
        *(f"- {factor}" for factor in _textos(salida.factores)),
        "",
        "## Opciones consideradas",
        "",
        *(f"- {nombre(opcion.id)}" for opcion in salida.opciones),
        "",
        "## Resultado de la decisión",
        "",
        f"Opción elegida: «{nombre(salida.elegida)}», porque {salida.justificacion.strip()}",
        "",
        "### Consecuencias",
        "",
        *(f"- Favorable, porque {c}" for c in _textos(salida.consecuencias_favorables)),
        *(f"- Desfavorable, porque {c}" for c in _textos(salida.consecuencias_desfavorables)),
        "",
        "### Confirmación",
        "",
        salida.confirmacion.strip(),
        "",
        "## Análisis de las opciones",
    ]
    for opcion in salida.opciones:
        lineas += ["", f"### {nombre(opcion.id)}"]
        lineas += [f"- Favorable, porque {a}" for a in _textos(opcion.favorables)]
        lineas += [f"- Desfavorable, porque {a}" for a in _textos(opcion.desfavorables)]
        if opcion.id != salida.elegida and opcion.motivo_descarte:
            lineas.append(f"- Descartada, porque {opcion.motivo_descarte.strip()}")
    return con_fuentes("\n".join(lineas)) + "\n"


ENCABEZADO_REVISIONES = "## Revisiones"


def entrada_de_revision(
    numero: int,
    version: str,
    observaciones: tuple[str, ...],
    respuesta: str,
    cambios: list[str] | None,
) -> str:
    """Arma la entrada de una revisión del registro de decisión.

    Args:
        numero: Número de la revisión en la sesión.
        version: Versión de la especificación que resulta de la revisión.
        observaciones: Observaciones del revisor que la motivan.
        respuesta: Cómo las atiende el arquitecto, según la selección.
        cambios: Cambios de la especificación respecto de la anterior; None si aún no se conocen
            o si no había especificación anterior.

    Returns:
        La entrada en Markdown, con su propio encabezado.
    """
    lineas = [
        f"### Revisión {numero} · especificación {version}",
        "",
        "Observaciones del revisor:",
        "",
        *(f"- «{observacion.strip()}»" for observacion in observaciones),
        "",
        f"Respuesta: {respuesta.strip()}",
    ]
    if cambios is not None:
        lineas += ["", "Cambios en la especificación:", ""]
        lineas += [f"- {cambio}" for cambio in cambios] or ["- Ninguno."]
    return "\n".join(lineas)


def con_revisiones(registro: str, revisiones: tuple[str, ...]) -> str:
    """Reemplaza la sección de revisiones del registro por las revisiones dadas.

    Aplicarla dos veces da el mismo resultado: la sección anterior, si la hay, se descarta.

    Args:
        registro: Registro de decisión, con o sin sección de revisiones.
        revisiones: Entradas de revisión, en orden.

    Returns:
        El registro con las revisiones al final, o sin sección si no hay ninguna.
    """
    base = registro.split(f"\n{ENCABEZADO_REVISIONES}\n", 1)[0].rstrip("\n") + "\n"
    if not revisiones:
        return base
    return f"{base}\n{ENCABEZADO_REVISIONES}\n\n" + "\n\n".join(revisiones) + "\n"
