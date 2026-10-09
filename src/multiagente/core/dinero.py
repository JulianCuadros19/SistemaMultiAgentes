"""Nombres que representan dinero o avalúos, que deben usar `Decimal` (decisión 10).

La regla es de severidad alta (arq-004 y CAL-FS-005). El arquitecto la aplica a la especificación
(N9) y el tester al código generado (N12).
"""

import re

MONETARIO = re.compile(
    r"(?:avaluo|valor|monto|tarifa|impuesto|precio|pago|saldo|deuda|liquidacion|costo|interes"
    r"|descuento|recargo|multa|cuota)"
)
"""Raíces de los nombres de campos, parámetros y variables que representan dinero o avalúos."""


def es_monetario(nombre: str) -> bool:
    """Indica si un nombre representa dinero o un avalúo por sus raíces.

    Args:
        nombre: Nombre de un campo, parámetro o variable.

    Returns:
        True si contiene alguna raíz monetaria, sin distinguir mayúsculas.
    """
    return MONETARIO.search(nombre.lower()) is not None
