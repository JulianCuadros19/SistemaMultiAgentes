"""Implementación de control del caso 17, para validar las pruebas de referencia (ADR-0019).

No participa en la comparación: sirve para comprobar que las pruebas pasan con una implementación
que sigue la ficha y fallan con cada mutante de `mutantes.json`. Expone directamente la interfaz de
referencia, así que hace también de adaptador.
"""

from collections import defaultdict
from datetime import date, datetime, timedelta

TRANSICIONES = {
    ("radicado", "en revisión"),
    ("en revisión", "aprobado"),
    ("en revisión", "rechazado"),
}
MENSAJES = {
    "aprobado": "Su trámite {n} fue aprobado",
    "rechazado": "Su trámite {n} fue rechazado; puede consultar el motivo en la oficina",
    "en revisión": "Su trámite {n} está en revisión",
}
FINALES = {"aprobado", "rechazado"}


def _dias_habiles(desde: date, hasta: date) -> int:
    dias = 0
    actual = desde
    while actual < hasta:
        actual += timedelta(days=1)
        if actual.weekday() < 5:
            dias += 1
    return dias


def procesar(
    avisos: list[dict[str, object]],
) -> tuple[list[tuple[str, bool]], list[str], dict[str, float]]:
    """Publica los avisos en orden, por el canal en memoria, y devuelve lo que dejan los procesos."""
    bitacora: list[tuple[str, bool]] = []
    mensajes: list[str] = []
    radicaciones: dict[str, datetime] = {}
    dias_por_tipo: dict[str, list[int]] = defaultdict(list)
    for aviso in avisos:
        numero, nuevo = str(aviso["numero"]), str(aviso["estado_nuevo"])
        valido = (aviso["estado_anterior"], nuevo) in TRANSICIONES
        bitacora.append((numero, valido))
        if not valido:
            continue
        radicaciones.setdefault(numero, aviso["fecha"])
        mensajes.append(MENSAJES[nuevo].format(n=numero))
        if nuevo in FINALES:
            dias = _dias_habiles(radicaciones[numero].date(), aviso["fecha"].date())
            dias_por_tipo[str(aviso["tipo"])].append(dias)
    promedios = {tipo: sum(dias) / len(dias) for tipo, dias in dias_por_tipo.items()}
    return bitacora, mensajes, promedios
