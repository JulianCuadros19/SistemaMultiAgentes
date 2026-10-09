"""Generación del módulo (N10): una llamada estructurada por versión, sin contexto recuperado.

El modelo recibe solo los requerimientos aprobados, la especificación de diseño y la
configuración de estilo (decisiones 1 y 2 de `CLAUDE.md`). En una corrección recibe además la
versión previa y la retroalimentación, y devuelve solo los archivos que cambian; el código los
combina sobre la versión previa (RF-19). La versión resultante se verifica en código antes de
pasar al tester (`verificacion.py`).
"""

import json

from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, ConfigDict

from multiagente.agentes.desarrollador.verificacion import RUTA_USO, verificar_version
from multiagente.core.esquemas.especificacion_diseno import EspecificacionDiseno
from multiagente.core.estilo import EstiloGenerado
from multiagente.llm.invocador import ErrorValidacionSalida
from multiagente.orquestador.estado import Requerimientos, Validacion, VersionCodigo


class ArchivoModelo(BaseModel):
    """Archivo generado, tal como lo devuelve el modelo."""

    model_config = ConfigDict(extra="forbid")

    ruta: str
    contenido: str


class SalidaGeneracion(BaseModel):
    """Salida de la generación: archivos del módulo y documento de uso."""

    model_config = ConfigDict(extra="forbid")

    archivos: list[ArchivoModelo]
    documentacion_uso: str


def _json(datos: object) -> str:
    """JSON con tildes legibles y sin espacios de sobra, como los demás agentes."""
    return json.dumps(datos, ensure_ascii=False, separators=(",", ":"))


def etiquetar_defectos(retroalimentacion: tuple[str, ...]) -> list[dict[str, str]]:
    """Asigna etiquetas `D1…Dn` a la retroalimentación, en orden.

    Args:
        retroalimentacion: Defectos reportados por el tester o el revisor humano.

    Returns:
        Cada defecto con su etiqueta.
    """
    return [
        {"etiqueta": f"D{numero}", "defecto": defecto}
        for numero, defecto in enumerate(retroalimentacion, 1)
    ]


def mensajes_generacion(
    requerimientos: Requerimientos,
    especificacion: EspecificacionDiseno,
    estilo: EstiloGenerado,
    validacion: Validacion,
    previa: VersionCodigo | None,
) -> list[ChatCompletionMessageParam]:
    """Arma los mensajes de datos de la generación.

    El primer mensaje no cambia entre las versiones de una sesión, de modo que el proveedor
    puede cobrarlo como entrada en caché en las correcciones.

    Args:
        requerimientos: Requerimientos aprobados en N6.
        especificacion: Especificación aprobada en N9.
        estilo: Configuración de estilo del código generado.
        validacion: Validación vigente, con la retroalimentación a atender.
        previa: Versión anterior del módulo, o None en la primera generación.

    Returns:
        Uno o dos mensajes de datos que acompañan al prompt de generación.
    """
    datos = {
        "estilo": {"archivo": estilo.archivo, "contenido": estilo.texto},
        "especificacion": especificacion.model_dump(mode="json"),
        "requerimientos": [r.model_dump(mode="json") for r in requerimientos.requerimientos],
    }
    mensajes: list[ChatCompletionMessageParam] = [{"role": "user", "content": _json(datos)}]
    if previa is not None:
        correccion = {
            "version_previa": {
                "numero": previa.numero,
                "archivos": [
                    {"ruta": ruta, "contenido": contenido}
                    for ruta, contenido in sorted(previa.archivos.items())
                ],
            },
            "retroalimentacion": etiquetar_defectos(validacion.retroalimentacion),
        }
        mensajes.append({"role": "user", "content": _json({"correccion": correccion})})
    return mensajes


def _normalizar(contenido: str) -> str:
    """Finales de línea LF y un salto de línea al final, como exige el estilo."""
    return contenido.replace("\r\n", "\n").rstrip("\n") + "\n"


def version_desde_salida(
    salida: SalidaGeneracion,
    requerimientos: Requerimientos,
    especificacion: EspecificacionDiseno,
    validacion: Validacion,
    previa: VersionCodigo | None,
    estilo: EstiloGenerado,
) -> VersionCodigo:
    """Combina la salida sobre la versión previa y verifica la estructura del resultado.

    Args:
        salida: Salida del modelo.
        requerimientos: Requerimientos aprobados en N6.
        especificacion: Especificación aprobada en N9.
        validacion: Validación vigente; su retroalimentación queda como defectos atendidos.
        previa: Versión anterior, o None en la primera generación.
        estilo: Configuración de estilo que rigió la generación.

    Returns:
        La versión nueva, con el número siguiente.

    Raises:
        ErrorValidacionSalida: Si la salida repite rutas, si una corrección no cambia nada o si
            la versión resultante no pasa la verificación estructural.
    """
    rutas = [archivo.ruta.strip() for archivo in salida.archivos]
    if repetidas := sorted({ruta for ruta in rutas if rutas.count(ruta) > 1}):
        raise ErrorValidacionSalida([f"Archivos repetidos en la salida: {repetidas}"])
    archivos = dict(previa.archivos) if previa is not None else {}
    nuevos = {archivo.ruta.strip(): _normalizar(archivo.contenido) for archivo in salida.archivos}
    if documentacion := salida.documentacion_uso.strip():
        nuevos[RUTA_USO] = _normalizar(documentacion)
    if previa is not None and all(archivos.get(r) == c for r, c in nuevos.items()):
        raise ErrorValidacionSalida(
            [
                "La corrección no modifica ningún archivo: atiende cada defecto de la "
                "retroalimentación"
            ]
        )
    archivos.update(nuevos)
    if problemas := verificar_version(archivos, especificacion, requerimientos):
        raise ErrorValidacionSalida(problemas)
    return VersionCodigo(
        numero=previa.numero + 1 if previa is not None else 1,
        archivos=archivos,
        defectos_atendidos=validacion.retroalimentacion if previa is not None else (),
        huella_estilo=estilo.huella,
    )
