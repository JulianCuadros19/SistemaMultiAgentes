"""Contexto recuperado que los agentes presentan a sus modelos (RF-04, RF-29, RF-32).

Cada agente recupera de sus colecciones y presenta los fragmentos con etiquetas `F1…Fn`
estables, en el orden de sus colecciones y de la recuperación. Un agente solo presenta las
colecciones que le corresponden, aunque el contexto acumulado de la sesión tenga otras.
"""

import json
from collections.abc import Iterable

from openai.types.chat import ChatCompletionMessageParam

from multiagente.orquestador.estado import Contexto, FragmentoContexto
from multiagente.rag.colecciones import Coleccion
from multiagente.rag.recuperacion import ResultadoRecuperacion


def json_texto(datos: object) -> str:
    """Serializa datos para un mensaje, con tildes legibles y sin espacios de sobra.

    Args:
        datos: Datos serializables en JSON.

    Returns:
        Texto JSON.
    """
    return json.dumps(datos, ensure_ascii=False, separators=(",", ":"))


def fragmentos_de(
    resultados: Iterable[ResultadoRecuperacion], coleccion: Coleccion
) -> tuple[tuple[FragmentoContexto, ...], list[str]]:
    """Convierte resultados de recuperación en fragmentos sin repetir y descartes legibles.

    Args:
        resultados: Resultados de una o varias consultas a la misma colección.
        coleccion: Colección consultada, para rotular los descartes.

    Returns:
        Los fragmentos en orden de aparición, sin repetir, y los descartes con su motivo.
    """
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


def etiquetar(contexto: Contexto, colecciones: Iterable[Coleccion]) -> dict[str, FragmentoContexto]:
    """Asigna etiquetas `F1…Fn` estables a los fragmentos de las colecciones indicadas.

    Args:
        contexto: Contexto acumulado de la sesión.
        colecciones: Colecciones del agente, en el orden en que se presentan.

    Returns:
        Fragmentos por etiqueta, en el orden de las colecciones y de la recuperación.
    """
    fragmentos = (
        fragmento
        for coleccion in colecciones
        for fragmento in contexto.fragmentos.get(coleccion.value, ())
    )
    return {f"F{numero}": fragmento for numero, fragmento in enumerate(fragmentos, 1)}


def mensaje_contexto(
    contexto: Contexto, colecciones: Iterable[Coleccion]
) -> ChatCompletionMessageParam:
    """Arma el mensaje de datos con el contexto etiquetado que acompaña al prompt.

    Va antes de los datos que cambian entre llamadas, de modo que el prefijo se repite y el
    proveedor puede cobrarlo como entrada en caché.

    Args:
        contexto: Contexto acumulado de la sesión.
        colecciones: Colecciones del agente, en el orden en que se presentan.

    Returns:
        Mensaje de usuario con un JSON `{"contexto": [{"etiqueta", "fuente", "contenido"}]}`.
    """
    datos = [
        {"etiqueta": etiqueta, "fuente": fragmento.referencia, "contenido": fragmento.contenido}
        for etiqueta, fragmento in etiquetar(contexto, colecciones).items()
    ]
    return {"role": "user", "content": json_texto({"contexto": datos})}
