"""Elementos compartidos por las pruebas."""

import hashlib
import math
import re
from collections.abc import Sequence

import pytest


class VectorizadorDePrueba:
    """Vectorizador determinista de bolsa de palabras, para probar sin el modelo real.

    Cada palabra suma en una posición fija del vector según su hash; los textos que comparten
    palabras quedan cerca. No tiene calidad semántica: solo sirve para probar la lógica.
    """

    modelo = "prueba/bolsa-de-palabras"
    dimension = 1024

    def __init__(self) -> None:
        self.llamadas = 0

    def vectorizar(self, textos: Sequence[str]) -> list[list[float]]:
        self.llamadas += 1
        vectores = []
        for texto in textos:
            vector = [0.0] * self.dimension
            for palabra in re.findall(r"\w+", texto.lower()):
                posicion = int(hashlib.md5(palabra.encode()).hexdigest(), 16) % self.dimension
                vector[posicion] += 1.0
            norma = math.sqrt(sum(v * v for v in vector)) or 1.0
            vectores.append([v / norma for v in vector])
        return vectores


@pytest.fixture
def vectorizador_prueba() -> VectorizadorDePrueba:
    return VectorizadorDePrueba()
