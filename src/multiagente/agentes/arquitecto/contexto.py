"""Recuperación del catálogo de arquitecturas de referencia y su metodología (N7, RF-09).

El catálogo es cerrado y pequeño, así que N7 recupera las seis arquitecturas completas, con
sus criterios de aplicabilidad, en lugar de las más parecidas a los requerimientos: la elección
es de N8, con los criterios de selección a la vista. Cada arquitectura se consulta por su
identificador y su título, y se toma el fragmento de su propio documento; si alguna falta, el
catálogo recuperado estaría incompleto y N7 falla.

Además recupera la metodología, con consultas fijas, y los patrones de diseño relacionados con
los requerimientos aprobados. Solo consulta la colección `arquitecturas_referencia` (RF-29).
"""

from pathlib import Path

from openai.types.chat import ChatCompletionMessageParam

from multiagente.agentes.arquitecto.catalogo import CARPETA_ARQUITECTURAS, ErrorCatalogo
from multiagente.agentes.contexto import fragmentos_de
from multiagente.agentes.contexto import mensaje_contexto as mensaje_de_colecciones
from multiagente.orquestador.estado import Contexto, Requerimientos
from multiagente.rag.colecciones import Coleccion
from multiagente.rag.documentos import leer_documento
from multiagente.rag.recuperacion import Recuperador, ResultadoRecuperacion

COLECCION = Coleccion.ARQUITECTURAS_REFERENCIA
COLECCIONES_ARQUITECTO: tuple[Coleccion, ...] = (COLECCION,)

CONSULTAS_METODOLOGICAS: tuple[tuple[str, int], ...] = (
    (
        "Criterios de selección de arquitectura: clasificar la naturaleza del módulo, peso de la "
        "lógica de negocio, restricciones no funcionales, simplicidad suficiente y prohibiciones",
        7,
    ),
    (
        "Plantilla del registro de decisión arquitectónica: opciones consideradas, resultado, "
        "consecuencias y confirmación",
        3,
    ),
    (
        "Esquema de la especificación de diseño: módulos, interfaces públicas, dependencias "
        "permitidas, modelo de datos y reglas de validación",
        3,
    ),
    ("Catálogo tecnológico autorizado: librerías por propósito, reglas de uso y prohibiciones", 3),
)
"""Consultas fijas con su número de fragmentos; cada una trae las secciones de un documento
metodológico. Los criterios de selección se traen completos: los cinco pasos y las
prohibiciones."""

FRAGMENTOS_POR_CONSULTA = 3
CANDIDATOS_POR_ARQUITECTURA = 5
LONGITUD_CONSULTA = 2000
"""Caracteres de la consulta construida con los requerimientos."""


def consulta_de_requerimientos(requerimientos: Requerimientos) -> str:
    """Construye una consulta descriptiva con los requerimientos aprobados completos.

    El ADR-0007 mostró que una consulta descriptiva recupera mejor que una frase suelta.

    Args:
        requerimientos: Requerimientos aprobados en N6.

    Returns:
        Texto con la funcionalidad, la regla y los datos de cada requerimiento, acotado.
    """
    partes = []
    for requerimiento in requerimientos.requerimientos:
        descripcion = requerimiento.descripcion
        datos = ", ".join(
            dato.nombre for dato in (*descripcion.datos_entrada, *descripcion.datos_salida)
        )
        partes.append(f"{requerimiento.titulo.quiero}. {descripcion.regla_negocio} Datos: {datos}.")
    return " ".join(partes)[:LONGITUD_CONSULTA]


def _arquitectura(recuperador: Recuperador, archivo: Path) -> ResultadoRecuperacion:
    """Recupera el fragmento de una arquitectura del catálogo, desde su propio documento."""
    documento = leer_documento(archivo)
    identificador = archivo.name[:6]
    consulta = f"{identificador} · {documento.metadatos.titulo}"
    resultado = recuperador.recuperar(consulta, [COLECCION], k=CANDIDATOS_POR_ARQUITECTURA)
    propios = tuple(f for f in resultado.fragmentos if f.documento_id == documento.metadatos.id)
    if not propios:
        raise ErrorCatalogo(f"N7 no recuperó la arquitectura {identificador} del catálogo")
    return resultado.model_copy(update={"fragmentos": propios[:1], "descartados": ()})


def recuperar_catalogo(
    recuperador: Recuperador,
    requerimientos: Requerimientos,
    carpeta: Path = CARPETA_ARQUITECTURAS,
) -> Contexto:
    """Recupera las seis arquitecturas, la metodología y los patrones aplicables (N7).

    Args:
        recuperador: Recuperador del arquitecto, limitado a su colección.
        requerimientos: Requerimientos aprobados en N6.
        carpeta: Carpeta del catálogo cerrado de arquitecturas.

    Returns:
        Fragmentos de `arquitecturas_referencia`: primero las arquitecturas en orden de
        catálogo, luego la metodología y los patrones, y los descartes con su motivo.

    Raises:
        ErrorCatalogo: Si alguna arquitectura del catálogo no se recupera.
    """
    resultados = [_arquitectura(recuperador, a) for a in sorted(carpeta.glob("ARQ-*.md"))]
    resultados += [
        recuperador.recuperar(consulta, [COLECCION], k=k) for consulta, k in CONSULTAS_METODOLOGICAS
    ]
    resultados.append(
        recuperador.recuperar(
            consulta_de_requerimientos(requerimientos), [COLECCION], k=FRAGMENTOS_POR_CONSULTA
        )
    )
    fragmentos, descartados = fragmentos_de(resultados, COLECCION)
    return Contexto(fragmentos={COLECCION.value: fragmentos}, descartados=tuple(descartados))


def mensaje_contexto(contexto: Contexto) -> ChatCompletionMessageParam:
    """Arma el mensaje con el contexto etiquetado del arquitecto, solo de su colección.

    Args:
        contexto: Contexto acumulado de la sesión, que también tiene el del elicitador.

    Returns:
        Mensaje de datos que acompaña a los prompts de N8.
    """
    return mensaje_de_colecciones(contexto, COLECCIONES_ARQUITECTO)
