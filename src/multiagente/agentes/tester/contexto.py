"""Recuperación de los criterios de calidad aplicables al módulo (N13, RF-23, RF-29).

Los criterios aplicables son, primero, las reglas que citan los hallazgos de N12: cada una se
consulta por su identificador, y la coincidencia léxica la trae en primer lugar (ADR-0007).
Además se recuperan con consultas fijas los criterios que usa el juez de N14: la cobertura de los
criterios de aceptación, las técnicas de diseño de casos de prueba y la regla de veredicto. Solo
se consulta la colección `criterios_calidad`.
"""

from openai.types.chat import ChatCompletionMessageParam

from multiagente.agentes.contexto import fragmentos_de
from multiagente.agentes.contexto import mensaje_contexto as mensaje_de_colecciones
from multiagente.orquestador.estado import Contexto, Validacion
from multiagente.rag.colecciones import Coleccion
from multiagente.rag.recuperacion import Recuperador, ResultadoRecuperacion

COLECCION = Coleccion.CRITERIOS_CALIDAD
COLECCIONES_TESTER: tuple[Coleccion, ...] = (COLECCION,)

CONSULTAS_FIJAS: tuple[tuple[str, int], ...] = (
    (
        "Cobertura de criterios de aceptación: cada criterio con al menos un caso de prueba "
        "automatizado que lo ejercite, ejecución sin fallos y camino de error",
        4,
    ),
    (
        "Técnicas de diseño de casos de prueba: partición de equivalencia, valores límite, "
        "cobertura de decisiones y criterio de suficiencia del conjunto de pruebas",
        3,
    ),
    ("Escala de severidad y regla de veredicto del tester", 2),
)
"""Consultas fijas con su número de fragmentos."""


def recuperar_criterios(recuperador: Recuperador, validacion: Validacion) -> Contexto:
    """Recupera las reglas de los hallazgos y los criterios del juicio de los casos.

    Args:
        recuperador: Recuperador limitado a la colección del tester.
        validacion: Validación con los hallazgos de N12.

    Returns:
        Los fragmentos de `criterios_calidad`, sin repetir, y el contexto descartado.
    """
    resultados: list[ResultadoRecuperacion] = [
        recuperador.recuperar(regla, colecciones=COLECCIONES_TESTER, k=1)
        for regla in sorted({hallazgo.regla for hallazgo in validacion.hallazgos})
    ]
    resultados += [
        recuperador.recuperar(consulta, colecciones=COLECCIONES_TESTER, k=k)
        for consulta, k in CONSULTAS_FIJAS
    ]
    fragmentos, descartados = fragmentos_de(resultados, COLECCION)
    return Contexto(fragmentos={COLECCION.value: fragmentos}, descartados=tuple(descartados))


def mensaje_contexto(contexto: Contexto) -> ChatCompletionMessageParam:
    """Mensaje con los criterios etiquetados `F1…Fn` para el juez de N14.

    Args:
        contexto: Contexto acumulado de la sesión; solo se presenta el del tester.

    Returns:
        Mensaje de datos que acompaña al prompt del veredicto.
    """
    return mensaje_de_colecciones(contexto, COLECCIONES_TESTER)
