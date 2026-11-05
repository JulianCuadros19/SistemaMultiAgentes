"""Documentos de la sesión en HTML para la web (ADR-0018).

La trazabilidad (RF-33) y la traza por nodo (RF-34) se escriben en Markdown en
`multiagente.interfaces.documentos`, la misma fuente que usan la consola y la exportación. La web
los muestra en HTML con este conversor, que entiende solo el Markdown que esos generadores
escriben:
- títulos con `#`, `##` y `###`;
- listas con `- `, con un segundo nivel sangrado con dos espacios;
- tablas con una fila de encabezado y otra de separación; una barra escapada queda en su celda;
- párrafos, y `**negrita**` y `` `código` `` dentro de una línea.

Todo el texto se escapa antes de darle formato: lo que escribió el cliente o devolvió un modelo
nunca se interpreta como HTML.
"""

import re
from html import escape

from markupsafe import Markup

_TITULO = re.compile(r"^(#{1,3}) (.+)$")
_NEGRITA = re.compile(r"\*\*(.+?)\*\*")
_CODIGO = re.compile(r"`([^`]+)`")
_SEPARADOR = re.compile(r"^\|(?:\s*:?-+:?\s*\|)+\s*$")
_BARRA = re.compile(r"(?<!\\)\|")
_NUMERO = re.compile(r"^\d[\d.,]*(?: \(\d[\d.,]*\))?$")
_VACIO = "—"


def _en_linea(texto: str) -> str:
    """Escapa el texto y aplica el código y la negrita dentro de una línea."""
    texto = escape(texto, quote=False)
    texto = _CODIGO.sub(r"<code>\1</code>", texto)
    return _NEGRITA.sub(r"<strong>\1</strong>", texto)


def _celdas(fila: str) -> list[str]:
    """Celdas de una fila de tabla, sin las barras de los extremos."""
    partes = _BARRA.split(fila.strip())
    return [parte.strip().replace("\\|", "|") for parte in partes[1:-1]]


def _tabla(filas: list[str]) -> str:
    """Tabla con encabezado; las columnas de cifras se alinean a la derecha."""
    encabezado = _celdas(filas[0])
    cuerpo = [_celdas(fila) for fila in filas[1:] if not _SEPARADOR.match(fila)]
    numericas = [
        any(len(fila) > i and fila[i] != _VACIO for fila in cuerpo)
        and all(len(fila) <= i or fila[i] == _VACIO or _NUMERO.match(fila[i]) for fila in cuerpo)
        for i in range(len(encabezado))
    ]

    def celda(etiqueta: str, texto: str, i: int) -> str:
        clase = ' class="num"' if i < len(numericas) and numericas[i] else ""
        return f"<{etiqueta}{clase}>{_en_linea(texto)}</{etiqueta}>"

    partes = ['<div class="tabla-envoltura"><table class="tabla">', "<thead><tr>"]
    partes += [celda("th", texto, i) for i, texto in enumerate(encabezado)]
    partes.append("</tr></thead><tbody>")
    for fila in cuerpo:
        partes.append("<tr>" + "".join(celda("td", t, i) for i, t in enumerate(fila)) + "</tr>")
    partes.append("</tbody></table></div>")
    return "".join(partes)


def _lista(elementos: list[tuple[str, list[str]]]) -> str:
    """Lista de dos niveles a lo sumo."""
    partes = ["<ul>"]
    for texto, hijos in elementos:
        anidada = "".join(f"<li>{_en_linea(hijo)}</li>" for hijo in hijos)
        partes.append(
            f"<li>{_en_linea(texto)}" + (f"<ul>{anidada}</ul>" if hijos else "") + "</li>"
        )
    partes.append("</ul>")
    return "".join(partes)


def a_html(markdown: str, omitir_titulo: bool = False) -> Markup:
    """Convierte a HTML un documento de `multiagente.interfaces.documentos`.

    Args:
        markdown: El documento en Markdown.
        omitir_titulo: Si se omite el título de la primera línea, cuando la página ya lo muestra.

    Returns:
        El HTML, marcado como seguro para que la plantilla no lo vuelva a escapar.
    """
    lineas = markdown.splitlines()
    if omitir_titulo and lineas and lineas[0].startswith("# "):
        lineas = lineas[1:]
    salida: list[str] = []
    parrafo: list[str] = []

    def cerrar_parrafo() -> None:
        if parrafo:
            salida.append(f"<p>{_en_linea(' '.join(parrafo))}</p>")
            parrafo.clear()

    i = 0
    while i < len(lineas):
        linea = lineas[i]
        titulo = _TITULO.match(linea)
        if not linea.strip():
            cerrar_parrafo()
            i += 1
        elif titulo:
            cerrar_parrafo()
            nivel = len(titulo.group(1))
            salida.append(f"<h{nivel}>{_en_linea(titulo.group(2))}</h{nivel}>")
            i += 1
        elif linea.startswith("|"):
            cerrar_parrafo()
            filas = []
            while i < len(lineas) and lineas[i].startswith("|"):
                filas.append(lineas[i])
                i += 1
            salida.append(_tabla(filas))
        elif linea.startswith("- "):
            cerrar_parrafo()
            elementos: list[tuple[str, list[str]]] = []
            while i < len(lineas) and lineas[i].startswith(("- ", "  - ")):
                if lineas[i].startswith("- ") or not elementos:
                    elementos.append((lineas[i].lstrip()[2:], []))
                else:
                    elementos[-1][1].append(lineas[i][4:])
                i += 1
            salida.append(_lista(elementos))
        else:
            parrafo.append(linea.strip())
            i += 1
    cerrar_parrafo()
    return Markup("\n".join(salida))
