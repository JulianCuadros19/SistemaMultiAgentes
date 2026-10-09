"""Fidelidad a lo que dijo el cliente: el elicitador no registra lo que el cliente no expresó.

La guía de elicitación prohíbe completar con supuestos silenciosos (eli-006, regla 4). El modelo,
con el contexto de dominio a la vista, tiende a copiar reglas típicas del dominio que el cliente
nunca mencionó. Esta verificación determinística acepta un texto solo si la mayoría de sus
raíces léxicas aparecen en las intervenciones del cliente.

Es una heurística: compara las cinco primeras letras de cada palabra con contenido, sin tildes.
Puede descartar una paráfrasis legítima; en ese caso el resumen que confirma el cliente no la
muestra, el cliente la echa en falta y se vuelve a registrar.
"""

import re

from multiagente.agentes.elicitador.calidad import normalizar
from multiagente.orquestador.estado import Conversacion, Emisor

UMBRAL_RESPALDO = 0.6
"""Fracción mínima de raíces del texto que deben aparecer en lo que dijo el cliente."""

LONGITUD_RAIZ = 5

PALABRAS_VACIAS = frozenset(
    {
        "ante",
        "cada",
        "como",
        "con",
        "cual",
        "cuando",
        "debe",
        "deben",
        "desde",
        "donde",
        "durante",
        "entre",
        "esta",
        "estado",
        "este",
        "esto",
        "hace",
        "hacia",
        "hasta",
        "para",
        "pero",
        "puede",
        "pueden",
        "queda",
        "quedar",
        "segun",
        "sera",
        "siempre",
        "sido",
        "sistema",
        "sobre",
        "solo",
        "tambien",
        "tener",
        "tiene",
        "tienen",
        "todo",
        "toda",
        "todos",
        "todas",
        "unicamente",
    }
)
"""Palabras de cuatro letras o más que no aportan contenido propio a una regla."""

NUMEROS_EN_LETRAS = {
    "cero": "0",
    "dos": "2",
    "tres": "3",
    "cuatro": "4",
    "cinco": "5",
    "seis": "6",
    "siete": "7",
    "ocho": "8",
    "nueve": "9",
    "diez": "10",
    "once": "11",
    "doce": "12",
    "trece": "13",
    "catorce": "14",
    "quince": "15",
    "dieciseis": "16",
    "diecisiete": "17",
    "dieciocho": "18",
    "diecinueve": "19",
    "veinte": "20",
    "treinta": "30",
    "cuarenta": "40",
    "cincuenta": "50",
    "sesenta": "60",
    "setenta": "70",
    "ochenta": "80",
    "noventa": "90",
    "cien": "100",
    "mil": "1000",
}
"""Números que el cliente dice en letras y el modelo suele escribir en cifras, o al revés.

«Uno» y «una» se omiten, porque casi siempre son artículos. Los compuestos, como «treinta y
dos», no se reconocen como un solo número.
"""


def raices(texto: str) -> set[str]:
    """Raíces léxicas de un texto: números en cifras y prefijos de las palabras con contenido.

    Un número escrito en letras cuenta como el mismo número en cifras: «cuatro dígitos» y
    «4 dígitos» tienen las mismas raíces.

    Args:
        texto: Texto a analizar.

    Returns:
        Conjunto de raíces; las palabras de menos de cuatro letras y las vacías se omiten.
    """
    resultado: set[str] = set()
    for palabra in re.findall(r"\w+", normalizar(texto).replace("_", " ")):
        if palabra.isdigit():
            resultado.add(palabra)
        elif palabra in NUMEROS_EN_LETRAS:
            resultado.add(NUMEROS_EN_LETRAS[palabra])
        elif len(palabra) >= 4 and palabra not in PALABRAS_VACIAS:
            resultado.add(palabra[:LONGITUD_RAIZ])
    return resultado


def raices_del_cliente(conversacion: Conversacion) -> set[str]:
    """Raíces de todas las intervenciones del cliente, incluida la necesidad inicial.

    Args:
        conversacion: Conversación de la sesión.

    Returns:
        Raíces de lo que dijo el cliente.
    """
    return raices(
        " ".join(turno.texto for turno in conversacion.turnos if turno.emisor is Emisor.CLIENTE)
    )


def respaldado(texto: str, fuente: set[str]) -> bool:
    """Indica si un texto está respaldado por lo que dijo el cliente.

    Args:
        texto: Texto producido por el modelo.
        fuente: Raíces de lo que dijo el cliente.

    Returns:
        True si al menos el 60 % de las raíces del texto aparecen en la fuente; un texto sin
        raíces de contenido se considera respaldado.
    """
    propias = raices(texto)
    if not propias:
        return True
    return len(propias & fuente) / len(propias) >= UMBRAL_RESPALDO


MARCAS_DESCONOCIMIENTO = re.compile(
    r"\b(?:no (?:lo )?sé|no lo se|desconozco|no estoy segur[oa]|no sabr[ií]a"
    r"|no tengo (?:esa |ese |ningún |ninguna )?(?:informaci[oó]n|dato)"
    r"|habr[ií]a que (?:consultar|verificar|confirmar))\b"
)
"""Expresiones con que el cliente dice no saber algo: lo único que crea una pregunta abierta.

Se buscan en el texto con tildes, porque sin ellas «no sé» se confunde con «no se acepta».
"""


def desconoce_algo(conversacion: Conversacion) -> bool:
    """Indica si el cliente dijo no saber algo en alguna de sus intervenciones (eli-006, regla 4).

    Args:
        conversacion: Conversación de la sesión.

    Returns:
        True si alguna intervención del cliente expresa desconocimiento.
    """
    return any(
        MARCAS_DESCONOCIMIENTO.search(turno.texto.casefold())
        for turno in conversacion.turnos
        if turno.emisor is Emisor.CLIENTE
    )


def oraciones_respaldadas(texto: str, fuente: set[str]) -> str:
    """Conserva solo las oraciones de un texto que están respaldadas por lo que dijo el cliente.

    Args:
        texto: Texto en una o varias oraciones, separadas por punto o punto y coma.
        fuente: Raíces de lo que dijo el cliente.

    Returns:
        Las oraciones respaldadas, unidas en el orden original; vacío si ninguna lo está.
    """
    oraciones = [parte.strip() for parte in re.split(r"(?<=[.;])\s+", texto) if parte.strip()]
    return " ".join(oracion for oracion in oraciones if respaldado(oracion, fuente))
