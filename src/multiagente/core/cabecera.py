"""Lectura de archivos Markdown con cabecera YAML: documentos de conocimiento y prompts."""

from typing import Any

import yaml


class ErrorCabecera(ValueError):
    """El archivo no tiene una cabecera YAML válida."""


def separar_cabecera(texto: str) -> tuple[dict[str, Any], str]:
    """Separa la cabecera YAML del cuerpo de un archivo Markdown.

    La cabecera se lee con `BaseLoader`, que entrega todos los valores como texto: así una
    versión `1.10` no se convierte en el número 1.1.

    Args:
        texto: Contenido completo del archivo, que empieza con `---`.

    Returns:
        La cabecera como diccionario de textos y el cuerpo sin los saltos de línea de los
        extremos.

    Raises:
        ErrorCabecera: Si falta la cabecera o si no es un diccionario YAML válido.
    """
    if not texto.startswith("---\n") or "\n---\n" not in texto[4:]:
        raise ErrorCabecera("falta la cabecera de metadatos")
    cabecera, cuerpo = texto[4:].split("\n---\n", 1)
    try:
        datos = yaml.load(cabecera, Loader=yaml.BaseLoader)
    except yaml.YAMLError as error:
        raise ErrorCabecera(f"cabecera YAML inválida: {error}") from error
    if not isinstance(datos, dict):
        raise ErrorCabecera("la cabecera no es un diccionario")
    return datos, cuerpo.strip("\n")
