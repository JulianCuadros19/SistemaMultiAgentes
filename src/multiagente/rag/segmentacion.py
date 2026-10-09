"""Segmentación de los documentos según la estrategia que declara cada uno (RF-30).

- `por_seccion`: prosa de dominio y de elicitación; un fragmento por sección `##`, partida con
  solapamiento si supera el límite de tamaño.
- `por_unidad_conceptual`: catálogo de arquitecturas y patrones; el documento completo si no
  tiene secciones (una arquitectura) o una sección `##` por unidad (un patrón), sin partir.
- `una_regla_por_fragmento`: criterios de calidad; una regla `### REGLA` por fragmento, o una
  sección `##` por criterio en los documentos sin reglas formales.

Los títulos dentro de bloques de código no cuentan como secciones.
"""

import re

from pydantic import ConfigDict, Field

from multiagente.core.esquemas.comunes import ModeloEstricto, TextoObligatorio
from multiagente.rag.documentos import DocumentoConocimiento, Estrategia

MAX_CARACTERES = 4000
"""Límite de tamaño de un fragmento de prosa, unos 1024 tokens (arquitectura, §3)."""

SOLAPAMIENTO_CARACTERES = 400
"""Texto que comparte un fragmento con el anterior cuando una sección se parte."""

SEPARADOR_TITULO = " › "

_REGLA = re.compile(r"^### REGLA\s+(?P<id>[A-Z]+(?:-[A-Z0-9]+)+)\s*·\s*(?P<nombre>.+)$")
_CAMPO_REGLA = re.compile(r"^- \*\*(?P<campo>[^*:]+):\*\*\s*(?P<valor>.+)$")
_CAMPOS_REGLA = {
    "Característica": "caracteristica",
    "Severidad": "severidad",
    "Norma de referencia": "norma",
}


class FragmentoTexto(ModeloEstricto):
    """Fragmento de un documento, antes de vectorizarse."""

    model_config = ConfigDict(frozen=True)

    orden: int = Field(ge=0)
    titulo: TextoObligatorio
    contenido: TextoObligatorio
    metadatos: dict[str, str] = Field(default_factory=dict)


def _lineas_fuera_de_codigo(cuerpo: str) -> list[tuple[str, bool]]:
    """Devuelve cada línea junto con un indicador de si está fuera de un bloque de código."""
    dentro = False
    lineas = []
    for linea in cuerpo.splitlines():
        if linea.lstrip().startswith("```"):
            dentro = not dentro
            lineas.append((linea, False))
            continue
        lineas.append((linea, not dentro))
    return lineas


def _secciones(cuerpo: str, es_encabezado: re.Pattern[str]) -> tuple[str, list[tuple[str, str]]]:
    """Divide el cuerpo en preámbulo y secciones según el patrón de encabezado.

    Returns:
        El preámbulo, sin el título `#` del documento, y la lista de (encabezado, texto), donde
        el texto incluye la línea del encabezado.
    """
    preambulo: list[str] = []
    secciones: list[tuple[str, list[str]]] = []
    for linea, fuera in _lineas_fuera_de_codigo(cuerpo):
        if fuera and es_encabezado.match(linea):
            secciones.append((linea.lstrip("#").strip(), [linea]))
        elif secciones:
            secciones[-1][1].append(linea)
        elif not (fuera and linea.startswith("# ")):
            preambulo.append(linea)
    return (
        "\n".join(preambulo).strip(),
        [(encabezado, "\n".join(lineas).strip()) for encabezado, lineas in secciones],
    )


def partir_con_solapamiento(
    texto: str,
    maximo: int = MAX_CARACTERES,
    solapamiento: int = SOLAPAMIENTO_CARACTERES,
) -> list[str]:
    """Parte un texto largo por párrafos; cada parte repite el final de la anterior.

    Args:
        texto: Texto a partir.
        maximo: Tamaño máximo aproximado de cada parte, en caracteres.
        solapamiento: Caracteres del final de una parte que se repiten en la siguiente.

    Returns:
        Las partes; una sola si el texto no supera el máximo.
    """
    if len(texto) <= maximo:
        return [texto]
    partes: list[str] = []
    actual = ""
    for parrafo in re.split(r"\n\s*\n", texto):
        candidato = f"{actual}\n\n{parrafo}" if actual else parrafo
        if len(candidato) <= maximo or not actual:
            actual = candidato
            continue
        partes.append(actual)
        actual = f"{actual[-solapamiento:]}\n\n{parrafo}"
    partes.append(actual)
    return [parte.strip() for parte in partes]


def _metadatos_regla(encabezado_regla: re.Match[str], texto: str) -> dict[str, str]:
    metadatos = {"regla": encabezado_regla["id"], "nombre": encabezado_regla["nombre"].strip()}
    for linea in texto.splitlines():
        if (campo := _CAMPO_REGLA.match(linea)) and campo["campo"] in _CAMPOS_REGLA:
            metadatos[_CAMPOS_REGLA[campo["campo"]]] = campo["valor"].strip()
    return metadatos


def segmentar(documento: DocumentoConocimiento) -> list[FragmentoTexto]:
    """Divide un documento en fragmentos según su estrategia de segmentación.

    Args:
        documento: Documento del corpus.

    Returns:
        Fragmentos en orden de aparición, cada uno titulado con el documento y su sección.
    """
    titulo = documento.metadatos.titulo
    estrategia = documento.metadatos.segmentacion
    cuerpo = documento.cuerpo
    piezas: list[tuple[str, str, dict[str, str]]] = []

    regla = re.compile(r"^### REGLA\s")
    con_reglas = estrategia is Estrategia.UNA_REGLA_POR_FRAGMENTO and any(
        fuera and regla.match(linea) for linea, fuera in _lineas_fuera_de_codigo(cuerpo)
    )
    preambulo, secciones = _secciones(cuerpo, regla if con_reglas else re.compile(r"^## "))

    if not secciones:
        piezas.append((titulo, preambulo, {}))
    else:
        if preambulo:
            piezas.append((titulo, preambulo, {}))
        for encabezado, texto in secciones:
            metadatos = {}
            if con_reglas and (coincidencia := _REGLA.match(texto.splitlines()[0])):
                metadatos = _metadatos_regla(coincidencia, texto)
            piezas.append((f"{titulo}{SEPARADOR_TITULO}{encabezado}", texto, metadatos))

    fragmentos: list[FragmentoTexto] = []
    for titulo_pieza, texto, metadatos in piezas:
        partes = partir_con_solapamiento(texto) if estrategia is Estrategia.POR_SECCION else [texto]
        for parte in partes:
            fragmentos.append(
                FragmentoTexto(
                    orden=len(fragmentos), titulo=titulo_pieza, contenido=parte, metadatos=metadatos
                )
            )
    return fragmentos
