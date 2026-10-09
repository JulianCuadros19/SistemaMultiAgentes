"""Recuperación del contexto de elicitación y de dominio de negocio (N2, RF-04).

La colección `elicitacion` se consulta con preguntas metodológicas fijas, porque su contenido
(guía de preguntas, plantillas, Gherkin, antipatrones) no depende de lo que pida el cliente. La
colección `dominio_negocio` se consulta con la necesidad con que el cliente abrió la sesión.
Los fragmentos se presentan al modelo con etiquetas `[F1]…[Fn]` estables, que N5 usa para
referenciar el contexto en cada requerimiento.
"""

from openai.types.chat import ChatCompletionMessageParam

from multiagente.agentes.contexto import etiquetar as etiquetar_colecciones
from multiagente.agentes.contexto import fragmentos_de
from multiagente.agentes.contexto import mensaje_contexto as mensaje_de_colecciones
from multiagente.orquestador.estado import Contexto, Conversacion, FragmentoContexto
from multiagente.rag.colecciones import Coleccion
from multiagente.rag.recuperacion import Recuperador

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
    metodologia, descartes_metodologia = fragmentos_de(
        (
            recuperador.recuperar(
                consulta, [Coleccion.ELICITACION], k=FRAGMENTOS_POR_CONSULTA_METODOLOGICA
            )
            for consulta in CONSULTAS_ELICITACION
        ),
        Coleccion.ELICITACION,
    )
    dominio, descartes_dominio = fragmentos_de(
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
    """Etiqueta `F1…Fn` los fragmentos de elicitación y de dominio del contexto.

    Args:
        contexto: Contexto acumulado de la sesión.

    Returns:
        Fragmentos por etiqueta, primero los de elicitación y luego los de dominio.
    """
    return etiquetar_colecciones(contexto, COLECCIONES_ELICITADOR)


def mensaje_contexto(contexto: Contexto) -> ChatCompletionMessageParam:
    """Arma el mensaje con el contexto etiquetado del elicitador.

    Args:
        contexto: Contexto acumulado de la sesión.

    Returns:
        Mensaje de datos que acompaña a los prompts de N3 y N5.
    """
    return mensaje_de_colecciones(contexto, COLECCIONES_ELICITADOR)
