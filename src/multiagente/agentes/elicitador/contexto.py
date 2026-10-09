"""Recuperación del contexto de elicitación y de dominio de negocio (N2, RF-04).

La colección `elicitacion` se consulta con preguntas metodológicas fijas, porque su contenido
(guía de preguntas, plantillas, Gherkin, antipatrones) no depende de lo que pida el cliente. La
colección `dominio_negocio` se consulta con la necesidad con que el cliente abrió la sesión.
Los fragmentos se presentan al modelo con etiquetas `[F1]…[Fn]` estables, que N5 usa para
referenciar el contexto en cada requerimiento.
"""

import json
from collections.abc import Iterable

from openai.types.chat import ChatCompletionMessageParam

from multiagente.orquestador.estado import Contexto, Conversacion, FragmentoContexto
from multiagente.rag.colecciones import Coleccion
from multiagente.rag.recuperacion import Recuperador, ResultadoRecuperacion

CONSULTAS_ELICITACION: tuple[str, ...] = (
    "Guía de preguntas estratégicas de elicitación: una pregunta por turno, orden de "
    "indagación, reglas de conducta y criterio de suficiencia para cerrar la conversación",
    "Formato de la historia de usuario: como rol, quiero funcionalidad, para beneficio, y "
    "antipatrones de redacción",
    "Plantilla del requerimiento funcional formal del Anexo A: campos, descripción, datos de "
    "entrada y de salida, regla de completitud",
    "Criterios de aceptación en formato Gherkin: DADO QUE, CUANDO, ENTONCES, cobertura mínima "
    "con camino feliz, alterno y de error",
    "Antipatrones y defectos frecuentes en requerimientos: ambigüedad, cuantificadores vagos, "
    "requerimiento compuesto, marcador de pendiente",
)
"""Consultas metodológicas; cada una trae las secciones de un documento de la colección."""

FRAGMENTOS_POR_CONSULTA_METODOLOGICA = 3
COLECCIONES_ELICITADOR: tuple[Coleccion, ...] = (Coleccion.ELICITACION, Coleccion.DOMINIO_NEGOCIO)


def _a_contexto(
    resultados: Iterable[ResultadoRecuperacion], coleccion: Coleccion
) -> tuple[tuple[FragmentoContexto, ...], list[str]]:
    """Convierte resultados de recuperación en fragmentos sin repetir y descartes legibles."""
    fragmentos: list[FragmentoContexto] = []
    vistos: set[int] = set()
    descartados: list[str] = []
    for resultado in resultados:
        if resultado.sin_contexto:
            descartados.append(f"{coleccion}: sin contexto relevante para «{resultado.consulta}»")
        for descarte in resultado.descartados:
            fragmento = descarte.fragmento
            descartados.append(
                f"{coleccion}: {fragmento.documento_id} · {fragmento.titulo} ({descarte.motivo})"
            )
        for fragmento in resultado.fragmentos:
            if fragmento.id in vistos:
                continue
            vistos.add(fragmento.id)
            fragmentos.append(
                FragmentoContexto(
                    documento_id=fragmento.documento_id,
                    version_documento=fragmento.version_documento,
                    titulo=fragmento.titulo,
                    contenido=fragmento.contenido,
                    similitud=round(fragmento.similitud, 4),
                )
            )
    return tuple(fragmentos), descartados


def recuperar_contexto(recuperador: Recuperador, conversacion: Conversacion) -> Contexto:
    """Recupera la guía de elicitación y el dominio de negocio de la necesidad del cliente.

    Args:
        recuperador: Recuperador del agente elicitador, limitado a sus dos colecciones.
        conversacion: Conversación abierta en N1, cuyo primer turno es la necesidad.

    Returns:
        Fragmentos por colección y descartes con su motivo (RF-32).

    Raises:
        ValueError: Si la conversación no tiene la necesidad inicial del cliente.
    """
    necesidad = conversacion.necesidad
    if necesidad is None:
        raise ValueError("La conversación no tiene la necesidad inicial del cliente")
    metodologia, descartes_metodologia = _a_contexto(
        (
            recuperador.recuperar(
                consulta, [Coleccion.ELICITACION], k=FRAGMENTOS_POR_CONSULTA_METODOLOGICA
            )
            for consulta in CONSULTAS_ELICITACION
        ),
        Coleccion.ELICITACION,
    )
    dominio, descartes_dominio = _a_contexto(
        [recuperador.recuperar(necesidad, [Coleccion.DOMINIO_NEGOCIO])], Coleccion.DOMINIO_NEGOCIO
    )
    return Contexto(
        fragmentos={
            Coleccion.ELICITACION.value: metodologia,
            Coleccion.DOMINIO_NEGOCIO.value: dominio,
        },
        descartados=(*descartes_metodologia, *descartes_dominio),
    )


def etiquetar(contexto: Contexto) -> dict[str, FragmentoContexto]:
    """Asigna etiquetas `F1…Fn` estables a los fragmentos de las colecciones del elicitador.

    Args:
        contexto: Contexto acumulado de la sesión.

    Returns:
        Fragmentos por etiqueta, en el orden de las colecciones y de la recuperación.
    """
    fragmentos = (
        fragmento
        for coleccion in COLECCIONES_ELICITADOR
        for fragmento in contexto.fragmentos.get(coleccion.value, ())
    )
    return {f"F{numero}": fragmento for numero, fragmento in enumerate(fragmentos, 1)}


def mensaje_contexto(contexto: Contexto) -> ChatCompletionMessageParam:
    """Arma el mensaje de datos con el contexto etiquetado que acompaña al prompt.

    Va antes de los datos que cambian en cada turno, de modo que el prefijo de la llamada se
    repite y el proveedor puede cobrarlo como entrada en caché.

    Args:
        contexto: Contexto acumulado de la sesión.

    Returns:
        Mensaje de usuario con un JSON `{"contexto": [{"etiqueta", "fuente", "contenido"}]}`.
    """
    datos = [
        {"etiqueta": etiqueta, "fuente": fragmento.referencia, "contenido": fragmento.contenido}
        for etiqueta, fragmento in etiquetar(contexto).items()
    ]
    return {"role": "user", "content": json_texto({"contexto": datos})}


def json_texto(datos: object) -> str:
    """Serializa datos para un mensaje, con tildes legibles y sin espacios de sobra.

    Args:
        datos: Datos serializables en JSON.

    Returns:
        Texto JSON.
    """
    return json.dumps(datos, ensure_ascii=False, separators=(",", ":"))
