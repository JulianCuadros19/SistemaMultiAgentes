"""Vectorización local de textos con BGE-M3 servido por TEI (RNF-04, decisión 8)."""

from collections.abc import Sequence
from typing import Protocol

import httpx

from multiagente.core.configuracion import ConfiguracionEmbeddings

TAMANO_LOTE = 16
"""Textos por solicitud al servicio; TEI admite hasta 32 por defecto."""

TIEMPO_ESPERA_SEGUNDOS = 120.0


class Vectorizador(Protocol):
    """Convierte textos en vectores de dimensión fija."""

    @property
    def modelo(self) -> str:
        """Identificador del modelo, que se registra con cada documento ingerido."""
        ...

    @property
    def dimension(self) -> int:
        """Dimensión de los vectores; debe coincidir con la columna `vector(1024)`."""
        ...

    def vectorizar(self, textos: Sequence[str]) -> list[list[float]]:
        """Devuelve un vector normalizado por cada texto, en el mismo orden."""
        ...


class ErrorVectorizacion(RuntimeError):
    """El servicio de embeddings no respondió o devolvió vectores inválidos."""


class VectorizadorTEI:
    """Cliente del servicio Text Embeddings Inference que sirve BGE-M3 en local."""

    def __init__(
        self,
        configuracion: ConfiguracionEmbeddings | None = None,
        cliente: httpx.Client | None = None,
    ) -> None:
        """Prepara el cliente HTTP del servicio.

        Args:
            configuracion: URL, modelo y dimensión; si se omite, se lee del entorno.
            cliente: Cliente HTTP a usar; si se omite, se crea uno con tiempo de espera acotado.
        """
        self.configuracion = configuracion or ConfiguracionEmbeddings()
        self.cliente = cliente or httpx.Client(
            base_url=self.configuracion.url, timeout=TIEMPO_ESPERA_SEGUNDOS
        )

    @property
    def modelo(self) -> str:
        """Identificador del modelo configurado."""
        return self.configuracion.modelo

    @property
    def dimension(self) -> int:
        """Dimensión esperada de los vectores."""
        return self.configuracion.dimension

    def vectorizar(self, textos: Sequence[str]) -> list[list[float]]:
        """Vectoriza los textos por lotes con normalización L2.

        Args:
            textos: Textos a vectorizar.

        Returns:
            Un vector normalizado por texto, en el mismo orden.

        Raises:
            ErrorVectorizacion: Si el servicio falla o devuelve vectores de otra dimensión.
        """
        vectores: list[list[float]] = []
        for inicio in range(0, len(textos), TAMANO_LOTE):
            lote = list(textos[inicio : inicio + TAMANO_LOTE])
            try:
                respuesta = self.cliente.post(
                    "/embed", json={"inputs": lote, "normalize": True, "truncate": False}
                )
                respuesta.raise_for_status()
            except httpx.HTTPError as error:
                raise ErrorVectorizacion(f"El servicio de embeddings falló: {error}") from error
            recibidos = respuesta.json()
            if len(recibidos) != len(lote) or any(len(v) != self.dimension for v in recibidos):
                raise ErrorVectorizacion(
                    f"Se esperaban {len(lote)} vectores de dimensión {self.dimension}"
                )
            vectores.extend(recibidos)
        return vectores
