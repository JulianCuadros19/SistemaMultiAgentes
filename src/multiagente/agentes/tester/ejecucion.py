"""Ejecución de la versión y sus pruebas en el entorno aislado (N11, RF-20).

Primero se importa cada módulo declarado y después se corren las pruebas con pytest, cada vez en
un contenedor efímero sin red (RNF-03). El resultado queda por módulo y por prueba, para que N14
dictamine cada caso del plan con su prueba como evidencia.
"""

from multiagente.core.esquemas.especificacion_diseno import EspecificacionDiseno
from multiagente.orquestador.estado import (
    EjecucionPruebas,
    PruebaEjecutada,
    ResultadoPrueba,
    VersionCodigo,
)
from multiagente.sandbox.ejecutor import EntornoAislado


def ejecutar_version(
    entorno: EntornoAislado,
    version: VersionCodigo,
    especificacion: EspecificacionDiseno,
    tiempo_limite_pruebas_s: float,
) -> EjecucionPruebas:
    """Importa los módulos declarados y corre las pruebas de la versión.

    Args:
        entorno: Entorno aislado donde se ejecuta el código.
        version: Versión del módulo con sus pruebas.
        especificacion: Especificación aprobada; da los módulos que deben importarse.
        tiempo_limite_pruebas_s: Tiempo límite de la corrida de pruebas.

    Returns:
        Los errores de importación, el resultado de cada prueba y los errores de recolección.

    Raises:
        ErrorEntornoAislado: Si Docker no responde o la imagen no existe; el nodo falla y la
            sesión se reanuda desde su último punto de control.
    """
    modulos = [modulo.nombre for modulo in especificacion.modulos]
    importacion = entorno.importar(version.archivos, modulos)
    corrida = entorno.probar(version.archivos, tiempo_limite_pruebas_s)
    return EjecucionPruebas(
        errores_importacion=importacion.errores,
        pruebas=tuple(
            PruebaEjecutada(
                archivo=prueba.archivo,
                nombre=prueba.nombre,
                resultado=ResultadoPrueba(prueba.resultado),
                duracion_ms=prueba.duracion_ms,
                mensaje=prueba.mensaje,
            )
            for prueba in corrida.pruebas
        ),
        errores_recoleccion=corrida.errores_recoleccion,
        vencido=importacion.ejecucion.vencido or corrida.ejecucion.vencido,
        duracion_ms=importacion.ejecucion.duracion_ms + corrida.ejecucion.duracion_ms,
        salida=corrida.salida_pytest,
    )
