"""Lectura de los documentos de la base de conocimiento y de sus metadatos (RF-30)."""

import hashlib
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Self

import yaml
from pydantic import ConfigDict, Field, ValidationError, model_validator

from multiagente.core.esquemas.comunes import ModeloEstricto, TextoObligatorio, Version
from multiagente.rag.colecciones import ACCESO, Agente, Coleccion

RAIZ_CONOCIMIENTO = Path(__file__).resolve().parents[3] / "knowledge_base"
"""Carpeta `knowledge_base/` del repositorio."""

INDICES = frozenset({"README.md", "00-MANIFIESTO.md"})
"""Archivos que describen las colecciones y no forman parte del corpus."""


class Estrategia(StrEnum):
    """Estrategia de segmentación que declara cada documento."""

    POR_SECCION = "por_seccion"
    POR_UNIDAD_CONCEPTUAL = "por_unidad_conceptual"
    UNA_REGLA_POR_FRAGMENTO = "una_regla_por_fragmento"


class MetadatosDocumento(ModeloEstricto):
    """Cabecera YAML de un documento de la base de conocimiento."""

    id: TextoObligatorio
    titulo: TextoObligatorio
    fuente: TextoObligatorio
    tipo_fuente: TextoObligatorio
    tags: list[TextoObligatorio] = Field(default_factory=list)
    coleccion: Coleccion
    version: Version
    fecha: date
    agente_consumidor: Agente
    segmentacion: Estrategia

    @model_validator(mode="after")
    def _agente_autorizado(self) -> Self:
        if self.coleccion not in ACCESO[self.agente_consumidor]:
            raise ValueError(
                f"El agente {self.agente_consumidor} no está autorizado para {self.coleccion}"
            )
        return self


class DocumentoConocimiento(ModeloEstricto):
    """Documento del corpus con sus metadatos, su cuerpo y su huella."""

    model_config = ConfigDict(frozen=True)

    metadatos: MetadatosDocumento
    ruta: TextoObligatorio
    cuerpo: str
    huella: TextoObligatorio


class ErrorDocumento(ValueError):
    """Un documento del corpus no tiene la forma esperada."""


def leer_documento(archivo: Path, raiz: Path = RAIZ_CONOCIMIENTO) -> DocumentoConocimiento:
    """Lee un documento Markdown con cabecera YAML y valida sus metadatos.

    La cabecera se lee con `BaseLoader`, que entrega todos los valores como texto: así una
    versión `1.10` no se convierte en el número 1.1.

    Args:
        archivo: Ruta del documento.
        raiz: Carpeta raíz del corpus; la primera carpeta bajo ella es la colección.

    Returns:
        El documento con sus metadatos validados y la huella SHA-256 de su contenido.

    Raises:
        ErrorDocumento: Si falta la cabecera, si es inválida o si la colección no coincide con
            la carpeta.
    """
    ruta = archivo.relative_to(raiz).as_posix()
    texto = archivo.read_text(encoding="utf-8")
    if not texto.startswith("---\n") or "\n---\n" not in texto[4:]:
        raise ErrorDocumento(f"{ruta}: falta la cabecera de metadatos")
    cabecera, cuerpo = texto[4:].split("\n---\n", 1)
    try:
        metadatos = MetadatosDocumento.model_validate(yaml.load(cabecera, Loader=yaml.BaseLoader))
    except (yaml.YAMLError, ValidationError) as error:
        raise ErrorDocumento(f"{ruta}: metadatos inválidos: {error}") from error
    carpeta = ruta.split("/", 1)[0]
    if carpeta != metadatos.coleccion:
        raise ErrorDocumento(
            f"{ruta}: declara la colección {metadatos.coleccion} pero está en {carpeta}"
        )
    return DocumentoConocimiento(
        metadatos=metadatos,
        ruta=ruta,
        cuerpo=cuerpo.strip("\n"),
        huella=hashlib.sha256(texto.encode("utf-8")).hexdigest(),
    )


def cargar_corpus(raiz: Path = RAIZ_CONOCIMIENTO) -> list[DocumentoConocimiento]:
    """Carga todos los documentos del corpus, sin los README ni los manifiestos.

    Args:
        raiz: Carpeta raíz del corpus.

    Returns:
        Documentos ordenados por ruta.

    Raises:
        ErrorDocumento: Si algún documento es inválido o si dos comparten identificador.
    """
    documentos = [
        leer_documento(archivo, raiz)
        for archivo in sorted(raiz.rglob("*.md"))
        if archivo.name not in INDICES
    ]
    vistos: dict[str, str] = {}
    for documento in documentos:
        if (previo := vistos.setdefault(documento.metadatos.id, documento.ruta)) != documento.ruta:
            raise ErrorDocumento(
                f"Identificador {documento.metadatos.id} repetido en {previo} y {documento.ruta}"
            )
    return documentos
