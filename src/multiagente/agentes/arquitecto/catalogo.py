"""Catálogos cerrados del arquitecto, leídos de la base de conocimiento como fuente única.

N9 los usa de forma determinística, sin recuperación semántica: la validación 3 del Anexo B
exige que las dependencias externas pertenezcan al catálogo tecnológico autorizado (arq-004), y
la decisión 5 de `CLAUDE.md` que la arquitectura base sea una del catálogo de referencia.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from multiagente.rag.documentos import RAIZ_CONOCIMIENTO, leer_documento

RUTA_CATALOGO_TECNOLOGICO = (
    RAIZ_CONOCIMIENTO / "arquitecturas_referencia" / "04-catalogo-tecnologico.md"
)
CARPETA_ARQUITECTURAS = RAIZ_CONOCIMIENTO / "arquitecturas_referencia" / "catalogo"
SECCION_LIBRERIAS = "## Librerías por propósito"
MARCA_ESTANDAR = "Biblioteca estándar"


class ErrorCatalogo(ValueError):
    """Un catálogo de la base de conocimiento no tiene la forma esperada."""


@dataclass(frozen=True)
class CatalogoTecnologico:
    """Librerías autorizadas y módulos de la biblioteca estándar del catálogo arq-004.

    Attributes:
        autorizadas: Paquetes externos que la especificación puede declarar.
        estandar: Módulos de la biblioteca estándar, que no se declaran como dependencia.
        version: Versión del documento del que se leyó.
    """

    autorizadas: frozenset[str]
    estandar: frozenset[str]
    version: str


def cargar_catalogo_tecnologico(ruta: Path = RUTA_CATALOGO_TECNOLOGICO) -> CatalogoTecnologico:
    """Lee la tabla «Librerías por propósito» del catálogo tecnológico.

    En la columna de la librería, los nombres van entre comillas invertidas; si la celda empieza
    con «Biblioteca estándar», son módulos de la biblioteca estándar.

    Args:
        ruta: Documento del catálogo tecnológico.

    Returns:
        Las librerías autorizadas y los módulos estándar.

    Raises:
        ErrorCatalogo: Si falta la sección o no declara ninguna librería.
    """
    documento = leer_documento(ruta)
    if SECCION_LIBRERIAS not in documento.cuerpo:
        raise ErrorCatalogo(f"{ruta.name}: falta la sección «{SECCION_LIBRERIAS}»")
    seccion = documento.cuerpo.split(SECCION_LIBRERIAS, 1)[1].split("\n## ", 1)[0]
    autorizadas: set[str] = set()
    estandar: set[str] = set()
    for linea in seccion.splitlines():
        celdas = [celda.strip() for celda in linea.strip().strip("|").split("|")]
        if len(celdas) < 2 or not linea.startswith("|"):
            continue
        nombres = re.findall(r"`([^`]+)`", celdas[1])
        destino = estandar if celdas[1].startswith(MARCA_ESTANDAR) else autorizadas
        destino.update(nombre.lower() for nombre in nombres)
    if not autorizadas:
        raise ErrorCatalogo(f"{ruta.name}: no declara ninguna librería autorizada")
    return CatalogoTecnologico(
        autorizadas=frozenset(autorizadas),
        estandar=frozenset(estandar),
        version=documento.metadatos.version,
    )


def arquitecturas_del_catalogo(carpeta: Path = CARPETA_ARQUITECTURAS) -> frozenset[str]:
    """Identificadores de las arquitecturas de referencia del catálogo cerrado.

    Args:
        carpeta: Carpeta `catalogo/` de la colección de arquitecturas.

    Returns:
        Identificadores `ARQ-nn` de los documentos de la carpeta.

    Raises:
        ErrorCatalogo: Si la carpeta no tiene arquitecturas.
    """
    identificadores = frozenset(
        archivo.name[:6]
        for archivo in carpeta.glob("ARQ-*.md")
        if re.match(r"ARQ-\d{2}-", archivo.name)
    )
    if not identificadores:
        raise ErrorCatalogo(f"{carpeta}: no hay arquitecturas en el catálogo")
    return identificadores
