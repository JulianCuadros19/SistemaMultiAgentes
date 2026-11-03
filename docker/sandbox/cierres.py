"""Cierre de dependencias de cada requisito de la imagen del entorno aislado (ADR-0014).

Corre dentro de la imagen al construirla. Para cada línea del archivo de requisitos recorre las
dependencias instaladas, evalúa sus marcadores para este Python y para los extras pedidos, y
escribe en la salida estándar un JSON con el nombre canónico de cada requisito y los de todas
sus dependencias, directas y transitivas. El paquete exportado de un módulo fija con él las
versiones de lo que instala `pip install -r requirements.txt`.

Uso: python cierres.py requisitos.txt > cierres.json
"""

import json
import re
import sys
from importlib import metadata

from packaging.requirements import Requirement


def canonico(nombre: str) -> str:
    """Nombre de distribución normalizado según PEP 503."""
    return re.sub(r"[-_.]+", "-", nombre).lower()


def cierre(requisito: Requirement) -> list[str]:
    """Nombres canónicos de las dependencias instaladas de un requisito, sin el requisito."""
    pendientes = [(requisito.name, frozenset(requisito.extras))]
    vistos: set[tuple[str, frozenset[str]]] = set()
    while pendientes:
        nombre, extras = pendientes.pop()
        if (canonico(nombre), extras) in vistos:
            continue
        vistos.add((canonico(nombre), extras))
        for linea in metadata.requires(nombre) or []:
            dependencia = Requirement(linea)
            marcador = dependencia.marker
            if marcador is None or any(
                marcador.evaluate({"extra": extra}) for extra in (extras or {""})
            ):
                pendientes.append((dependencia.name, frozenset(dependencia.extras)))
    return sorted({nombre for nombre, _ in vistos} - {canonico(requisito.name)})


def main(ruta: str) -> None:
    """Imprime el cierre de cada requisito del archivo."""
    with open(ruta, encoding="utf-8") as archivo:
        lineas = [linea.split("#", 1)[0].strip() for linea in archivo]
    requisitos = [Requirement(linea) for linea in lineas if linea]
    cierres = {canonico(requisito.name): cierre(requisito) for requisito in requisitos}
    print(json.dumps(cierres, indent=2, sort_keys=True))


if __name__ == "__main__":
    main(sys.argv[1])
