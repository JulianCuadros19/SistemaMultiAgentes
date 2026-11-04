"""Verificación estructural de una versión del módulo antes del entorno aislado (N10).

Comprueba, sin ejecutar el código, los criterios de aceptación del desarrollador que pueden
verificarse leyendo el árbol sintáctico (arquitectura, §11):

- RF-15: un archivo Python sintácticamente válido para Python 3.11 por cada módulo declarado,
  sin módulos no previstos, que expone las interfaces públicas de la especificación con firmas
  compatibles (los parámetros declarados, en orden y con sus tipos; al final solo se admiten
  parámetros con valor por defecto) y define o importa las excepciones declaradas.
- RF-17: cada módulo importa solo la biblioteca estándar, las dependencias externas declaradas y
  los módulos de sus `dependencias_permitidas`, siempre con importaciones absolutas y sin nombres
  privados de otro módulo (CAL-MT-010, que el tester rechaza con el umbral 0).
- RF-18: toda función, clase y método público documentado, al menos una prueba por cada
  escenario de cada requerimiento cubierto, nombrada `test_rf_01_esc_01_…`, y un `USO.md` con
  las secciones que necesita quien lo pone en marcha (`SECCIONES_USO`).

El análisis es el de `multiagente.core.conformidad`, el mismo que aplica el tester en N12.

- RF-16: con el criterio de estilo bloqueante del tester, las infracciones de Ruff que
  rechazarían la versión también son problemas aquí, para que el reintento las corrija
  (ADR-0015). El tester sigue dictaminando el estilo, la ejecución y la severidad (N11 a N14).

Los problemas se redactan para que el modelo los corrija en su reintento.
"""

from collections.abc import Callable, Mapping

from multiagente.agentes.desarrollador.uso import SECCIONES_USO, secciones_faltantes
from multiagente.core.conformidad import (
    RUTA_USO,
    TipoProblema,
    analizar_conformidad,
    importacion_de_paquete,
    nombre_de_prueba,
)
from multiagente.core.esquemas.especificacion_diseno import EspecificacionDiseno
from multiagente.core.estilo import hallazgos_de_estilo
from multiagente.orquestador.estado import Requerimientos

__all__ = [
    "RUTA_USO",
    "SECCIONES_USO",
    "importacion_de_paquete",
    "nombre_de_prueba",
    "verificar_version",
]

ARCHIVOS = "RF-15 · archivos"
SINTAXIS = "RF-15 · sintaxis"
INTERFACES = "RF-15 · interfaces"
DEPENDENCIAS = "RF-17 · dependencias"
DOCUMENTACION = "RF-18 · documentación"
PRUEBAS = "RF-18 · pruebas"
ESTILO = "RF-16 · estilo"

CRITERIO_POR_TIPO: dict[TipoProblema, str] = {
    TipoProblema.RUTA_INSEGURA: ARCHIVOS,
    TipoProblema.MODULO_FALTANTE: ARCHIVOS,
    TipoProblema.NO_PREVISTO: ARCHIVOS,
    TipoProblema.SIN_PRUEBAS: ARCHIVOS,
    TipoProblema.SIN_USO: ARCHIVOS,
    TipoProblema.SINTAXIS: SINTAXIS,
    TipoProblema.INTERFAZ: INTERFACES,
    TipoProblema.EXCEPCION: INTERFACES,
    TipoProblema.IMPORTACION_RELATIVA: DEPENDENCIAS,
    TipoProblema.IMPORTACION_NO_PERMITIDA: DEPENDENCIAS,
    TipoProblema.IMPORTACION_NO_DECLARADA: DEPENDENCIAS,
    TipoProblema.IMPORTACION_EXTERNA: DEPENDENCIAS,
    TipoProblema.IMPORTACION_PRIVADA: DEPENDENCIAS,
    TipoProblema.SIN_DOCSTRING: DOCUMENTACION,
    TipoProblema.ESCENARIO_SIN_PRUEBA: PRUEBAS,
    TipoProblema.PRUEBA_SIN_ESCENARIO: PRUEBAS,
    TipoProblema.PRUEBA_SIMULADA: PRUEBAS,
}
"""Criterio del desarrollador al que corresponde cada tipo de problema que verifica N10."""


def verificar_version(
    archivos: Mapping[str, str],
    especificacion: EspecificacionDiseno,
    requerimientos: Requerimientos,
    estilo_bloqueante: Callable[[str], str | None] | None = None,
) -> list[str]:
    """Verifica la estructura de una versión del módulo contra su especificación.

    Args:
        archivos: Contenido de cada archivo de la versión por su ruta.
        especificacion: Especificación de diseño aprobada en N9.
        requerimientos: Requerimientos aprobados en N6, con sus escenarios.
        estilo_bloqueante: Regla con que un código de Ruff rechaza la versión, o None si no la
            rechaza; si se omite, el estilo no se verifica aquí.

    Returns:
        Problemas encontrados, cada uno con el criterio que incumple; vacía si la versión puede
        pasar al tester.
    """
    informe = analizar_conformidad(archivos, especificacion, requerimientos.requerimientos)
    problemas = [
        f"{CRITERIO_POR_TIPO[problema.tipo]}: {problema.mensaje}"
        for problema in informe.problemas
        if problema.tipo in CRITERIO_POR_TIPO
    ]
    if (uso := archivos.get(RUTA_USO)) is not None and (faltan := secciones_faltantes(uso)):
        lista = ", ".join(f"«## {seccion}»" for seccion in faltan)
        problemas.append(f"{DOCUMENTACION}: a {RUTA_USO} le faltan las secciones {lista}")
    if estilo_bloqueante is not None:
        problemas.extend(
            f"{ESTILO}: {infraccion.archivo}:{infraccion.linea} {infraccion.codigo} "
            f"{infraccion.mensaje} ({regla})"
            for infraccion in hallazgos_de_estilo(dict(archivos))
            # La sintaxis ya la reporta la conformidad.
            if infraccion.codigo != "sintaxis"
            and (regla := estilo_bloqueante(infraccion.codigo)) is not None
        )
    return problemas
