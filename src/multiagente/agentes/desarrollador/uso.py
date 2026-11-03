"""Documento de uso del módulo generado (RF-18): sus secciones y las que escribe el sistema.

El modelo redacta lo propio del módulo: el título, el propósito, la configuración, la ejecución,
las interfaces y los supuestos. Requisitos, Instalación y Pruebas las escribe el sistema, porque
dependen de la versión de Python y de las dependencias con que se probó el módulo: el modelo no
las conoce y, al redactarlas, fijaba una versión de Python que no siempre existe, repetía la
instalación de pytest y copiaba notas internas del prompt (ADR-0014).
"""

import unicodedata
from collections.abc import Sequence

from multiagente.core.conformidad import VERSION_PYTHON

SECCIONES_USO = (
    "Requisitos",
    "Instalación",
    "Configuración",
    "Ejecución",
    "Pruebas",
    "Interfaces",
    "Supuestos",
)
"""Secciones de segundo nivel que debe tener el documento de uso, en ese orden."""

SECCIONES_DEL_SISTEMA = ("Requisitos", "Instalación", "Pruebas")
"""Secciones del documento de uso que escribe el sistema, no el modelo."""

PYTHON = ".".join(str(parte) for parte in VERSION_PYTHON)
"""Versión de Python con que el entorno aislado prueba el módulo."""


def _comparable(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in descompuesto if not unicodedata.combining(c)).strip().casefold()


def _secciones(documento: str) -> tuple[str, list[tuple[str, str]]]:
    """Lo que precede a la primera sección de segundo nivel y cada sección con su cuerpo.

    Un título dentro de un bloque de código no abre sección.
    """
    preambulo: list[str] = []
    secciones: list[tuple[str, list[str]]] = []
    en_codigo = False
    for linea in documento.splitlines():
        if linea.lstrip().startswith("```"):
            en_codigo = not en_codigo
        if not en_codigo and linea.startswith("## "):
            secciones.append((linea.removeprefix("## ").strip(), []))
        elif secciones:
            secciones[-1][1].append(linea)
        else:
            preambulo.append(linea)
    return "\n".join(preambulo), [(titulo, "\n".join(cuerpo)) for titulo, cuerpo in secciones]


def secciones_faltantes(documento: str) -> list[str]:
    """Secciones de `SECCIONES_USO` que no están como títulos de segundo nivel del documento.

    Args:
        documento: Contenido de `USO.md`.

    Returns:
        Las secciones que faltan, sin importar mayúsculas ni tildes.
    """
    titulos = {_comparable(titulo) for titulo, _ in _secciones(documento)[1]}
    return [seccion for seccion in SECCIONES_USO if _comparable(seccion) not in titulos]


def _secciones_del_sistema(dependencias: Sequence[str]) -> dict[str, str]:
    if dependencias:
        lista = ", ".join(f"`{paquete}`" for paquete in dependencias)
        externas = (
            f"- Dependencias externas: {lista}. Sus versiones, y las de pytest, quedan fijadas "
            "en `requirements.txt`."
        )
    else:
        externas = "- Sin dependencias externas: `requirements.txt` fija la versión de pytest."
    return {
        "Requisitos": f"- Python {PYTHON} o superior; el módulo se probó con Python {PYTHON}.\n"
        + externas,
        "Instalación": (
            "Desde la carpeta del código, cree un entorno e instale las dependencias:\n\n"
            "```sh\npython3 -m venv .venv\nsource .venv/bin/activate\n"
            "pip install -r requirements.txt\n```\n\n"
            "En Windows, el entorno se activa con `.venv\\Scripts\\activate`. "
            "`requirements.txt` acompaña al código: fija las versiones con que se probó e "
            "incluye pytest."
        ),
        "Pruebas": (
            "```sh\nPYTHONPATH=src python -m pytest tests\n```\n\n"
            'En Windows, con PowerShell: `$env:PYTHONPATH = "src"; python -m pytest tests`.'
        ),
    }


def componer_uso(documento: str, dependencias: Sequence[str]) -> str:
    """Documento de uso con las secciones del sistema en su lugar.

    Conserva el título, el propósito y las secciones que redactó el modelo, en el orden de
    `SECCIONES_USO` y seguidas de las que agregó por su cuenta. Requisitos, Instalación y
    Pruebas se reemplazan o se agregan. Componer dos veces da lo mismo que una.

    Args:
        documento: Documento de uso en Markdown, como lo redactó el modelo.
        dependencias: Paquetes de las dependencias externas que declara la especificación.

    Returns:
        El documento completo, con un salto de línea al final.
    """
    preambulo, secciones = _secciones(documento)
    redactadas = {_comparable(titulo): (titulo, cuerpo) for titulo, cuerpo in secciones}
    del_sistema = _secciones_del_sistema(dependencias)
    partes = [preambulo.strip()] if preambulo.strip() else []
    for seccion in SECCIONES_USO:
        if seccion in del_sistema:
            partes.append(f"## {seccion}\n\n{del_sistema[seccion]}")
        elif (redactada := redactadas.get(_comparable(seccion))) is not None:
            titulo, cuerpo = redactada
            partes.append(f"## {titulo}\n\n{cuerpo.strip()}".rstrip())
    canonicas = {_comparable(seccion) for seccion in SECCIONES_USO}
    partes += [
        f"## {titulo}\n\n{cuerpo.strip()}".rstrip()
        for titulo, cuerpo in secciones
        if _comparable(titulo) not in canonicas
    ]
    return "\n\n".join(partes) + "\n"
