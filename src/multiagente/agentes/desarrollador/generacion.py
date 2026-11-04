"""Generación del módulo (N10): una llamada estructurada por versión, sin contexto recuperado.

El modelo recibe solo los requerimientos aprobados, la especificación de diseño y la
configuración de estilo (decisiones 1 y 2 de `CLAUDE.md`). En una corrección recibe además la
versión previa y la retroalimentación, y devuelve solo los archivos que cambian; el código los
combina sobre la versión previa (RF-19). Tras un rediseño, la versión anterior llega como
referencia, sin los módulos que la especificación ya no declara, junto con la retroalimentación
y la revisión del diseño; la salida se combina sobre esos archivos. La versión resultante se
verifica en código antes de pasar al tester (`verificacion.py`).

Si no pasa la verificación, el reintento sigue la misma vía: el modelo recibe su intento ya
combinado con los problemas y devuelve solo lo que cambia, que el código combina sobre el
intento. Así un reintento parcial no deja la versión incompleta.
"""

import json
from collections.abc import Callable, Mapping

from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, ConfigDict

from multiagente.agentes.desarrollador.uso import componer_uso
from multiagente.agentes.desarrollador.verificacion import RUTA_USO, verificar_version
from multiagente.core.esquemas.especificacion_diseno import EspecificacionDiseno
from multiagente.core.estilo import EstiloGenerado
from multiagente.llm.invocador import ErrorValidacionSalida
from multiagente.orquestador.estado import Requerimientos, Validacion, VersionCodigo
from multiagente.orquestador.servicios import Rediseno


class IntentoRechazado(ErrorValidacionSalida):
    """La versión combinada de un intento no pasa la verificación.

    Attributes:
        archivos: Archivos del intento ya combinados, sobre los que se corrige al reintentar.
    """

    def __init__(self, problemas: list[str], archivos: dict[str, str]) -> None:
        """Crea el error con los problemas y los archivos del intento.

        Args:
            problemas: Incumplimientos encontrados.
            archivos: Archivos del intento, combinados sobre su base.
        """
        super().__init__(problemas)
        self.archivos = archivos


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


def archivos_de_referencia(
    version: VersionCodigo, especificacion: EspecificacionDiseno
) -> dict[str, str]:
    """Archivos de una versión anterior que siguen valiendo con una especificación nueva.

    Se conservan los módulos que la especificación sigue declarando en la misma ruta, las pruebas
    y el documento de uso; los demás módulos ya no existen en el diseño.

    Args:
        version: Versión generada con la especificación anterior.
        especificacion: Especificación nueva, aprobada tras el rediseño.

    Returns:
        Contenido de cada archivo que se conserva, por su ruta.
    """
    rutas = {modulo.ruta for modulo in especificacion.modulos}
    return {
        ruta: contenido
        for ruta, contenido in version.archivos.items()
        if ruta in rutas or ruta.startswith("tests/") or ruta == RUTA_USO
    }


def mensajes_generacion(
    requerimientos: Requerimientos,
    especificacion: EspecificacionDiseno,
    estilo: EstiloGenerado,
    validacion: Validacion,
    previa: VersionCodigo | None,
    rediseno: Rediseno | None = None,
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
        rediseno: Versión anterior y revisión del diseño, si la especificación cambió desde
            ella; la versión no se corrige, se toma como referencia.

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
    elif rediseno is not None:
        referencia = archivos_de_referencia(rediseno.version_previa, especificacion)
        datos_rediseno: dict[str, object] = {
            "version_previa": {
                "numero": rediseno.version_previa.numero,
                "archivos": [
                    {"ruta": ruta, "contenido": contenido}
                    for ruta, contenido in sorted(referencia.items())
                ],
            },
            "retroalimentacion": etiquetar_defectos(validacion.retroalimentacion),
        }
        if rediseno.revision:
            datos_rediseno["revision_del_diseno"] = rediseno.revision
        mensajes.append({"role": "user", "content": _json({"rediseno": datos_rediseno})})
    return mensajes


def mensaje_intento_rechazado(
    archivos: Mapping[str, str], problemas: list[str]
) -> ChatCompletionMessageParam:
    """Arma el mensaje del reintento: el intento rechazado y los problemas de la verificación.

    El modelo no ve su respuesta anterior; con este mensaje la corrige y devuelve solo los
    archivos que cambian.

    Args:
        archivos: Archivos del intento rechazado, ya combinados; vacío si la salida no pudo
            combinarse y no hay versión previa.
        problemas: Incumplimientos que encontró la verificación.

    Returns:
        El mensaje de datos que se agrega a los de la generación.
    """
    intento = {
        "archivos": [
            {"ruta": ruta, "contenido": contenido} for ruta, contenido in sorted(archivos.items())
        ],
        "problemas": problemas,
    }
    return {"role": "user", "content": _json({"intento_rechazado": intento})}


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
    base: Mapping[str, str] | None = None,
    estilo_bloqueante: Callable[[str], str | None] | None = None,
) -> VersionCodigo:
    """Combina la salida sobre su base y verifica la estructura del resultado.

    Args:
        salida: Salida del modelo.
        requerimientos: Requerimientos aprobados en N6.
        especificacion: Especificación aprobada en N9.
        validacion: Validación vigente; su retroalimentación queda como defectos atendidos.
        previa: Versión anterior, o None en la primera generación.
        estilo: Configuración de estilo que rigió la generación.
        base: Archivos sobre los que se combina la salida; si se omite, los de la versión
            previa. En el reintento, los del intento rechazado.
        estilo_bloqueante: Criterio de estilo del tester; si se da, las infracciones que
            rechazarían la versión también la rechazan aquí.

    Returns:
        La versión nueva, con el número siguiente.

    Raises:
        ErrorValidacionSalida: Si la salida repite rutas.
        IntentoRechazado: Si una corrección no cambia nada respecto de la versión previa o si
            la versión resultante no pasa la verificación estructural.
    """
    rutas = [archivo.ruta.strip() for archivo in salida.archivos]
    if repetidas := sorted({ruta for ruta in rutas if rutas.count(ruta) > 1}):
        raise ErrorValidacionSalida([f"Archivos repetidos en la salida: {repetidas}"])
    if base is None:
        base = previa.archivos if previa is not None else {}
    archivos = dict(base)
    archivos.update(
        {archivo.ruta.strip(): _normalizar(archivo.contenido) for archivo in salida.archivos}
    )
    if documentacion := salida.documentacion_uso.strip():
        paquetes = [dependencia.paquete for dependencia in especificacion.dependencias_externas]
        archivos[RUTA_USO] = componer_uso(_normalizar(documentacion), paquetes)
    if previa is not None and archivos == previa.archivos:
        raise IntentoRechazado(
            [
                "La corrección no modifica ningún archivo: atiende cada defecto de la "
                "retroalimentación"
            ],
            archivos,
        )
    if problemas := verificar_version(archivos, especificacion, requerimientos, estilo_bloqueante):
        raise IntentoRechazado(problemas, archivos)
    return VersionCodigo(
        numero=previa.numero + 1 if previa is not None else 1,
        archivos=archivos,
        defectos_atendidos=validacion.retroalimentacion if previa is not None else (),
        huella_estilo=estilo.huella,
    )
