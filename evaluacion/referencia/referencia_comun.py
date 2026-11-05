"""Piezas comunes de las pruebas de aceptación de referencia (paso 15, ADR-0019).

En el entorno aislado, este módulo va en `src/`, junto al adaptador de la implementación evaluada.
Lo importan las pruebas de referencia y los adaptadores.
"""

from collections.abc import Callable


class Ausente(Exception):
    """La implementación no ofrece el comportamiento: el adaptador no tiene a qué llamar.

    La evaluación cuenta aparte las verificaciones que fallan por un comportamiento ausente.
    """


def rechaza(llamada: Callable[..., object], *argumentos: object, mensaje: str | None = None) -> None:
    """Verifica que la llamada se rechace con un error, y con el mensaje si se indica.

    Un comportamiento ausente no cuenta como rechazo: se propaga para que la verificación falle.

    Args:
        llamada: Función de la interfaz de referencia.
        *argumentos: Argumentos con que se llama.
        mensaje: Texto que debe contener el error, sin distinguir mayúsculas.

    Raises:
        Ausente: Si la implementación no ofrece el comportamiento.
        AssertionError: Si la llamada no se rechaza o el mensaje no coincide.
    """
    try:
        llamada(*argumentos)
    except Ausente:
        raise
    except Exception as error:  # cualquier error de la implementación cuenta como rechazo
        if mensaje is not None and mensaje.lower() not in str(error).lower():
            raise AssertionError(f"Se rechazó con otro mensaje: {error!r}") from error
        return
    raise AssertionError("La llamada no se rechazó")
