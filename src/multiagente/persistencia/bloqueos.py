"""Una sola corrida a la vez por sesión, también entre procesos (paso 12, ADR-0014).

La consola, la web y los guiones operan las mismas sesiones desde procesos distintos. Mientras
uno avanza el grafo de una sesión, el estado guardado se ve igual que el de una sesión que se
cayó: nodos pendientes y ninguna pausa. Reanudarla desde otro proceso correría dos veces los
mismos nodos, con su costo, y bifurcaría el historial.

Por eso cada operación que avanza una sesión toma antes un bloqueo consultivo de PostgreSQL, en
una conexión dedicada que se cierra al terminar. Si el proceso muere, PostgreSQL suelta el bloqueo
con la conexión y la sesión vuelve a verse detenida. Los demás procesos leen en `pg_locks` qué
sesiones están ocupadas, sin tomarlas.
"""

import threading
import zlib
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from typing import Protocol

import psycopg
from psycopg_pool import ConnectionPool

from multiagente.core.configuracion import ConfiguracionBaseDatos

ESPACIO = 1_212_012
"""Primera clave de los bloqueos consultivos de sesión, para no chocar con otros usos."""


class SesionOcupada(RuntimeError):
    """Otra corrida está avanzando la sesión."""


def clave(id_sesion: str) -> int:
    """Segunda clave del bloqueo de una sesión: un entero no negativo de 31 bits.

    Dos sesiones distintas comparten clave con una probabilidad de una en dos mil millones; si
    pasara, una se vería en curso mientras la otra avanza.

    Args:
        id_sesion: Identificador de la sesión.

    Returns:
        La clave, siempre la misma para la misma sesión.
    """
    return zlib.crc32(id_sesion.encode("utf-8")) & 0x7FFFFFFF


class Bloqueos(Protocol):
    """Bloqueo exclusivo de una sesión y consulta de las que están ocupadas."""

    def exclusivo(self, id_sesion: str) -> AbstractContextManager[None]:
        """Toma la sesión mientras dura el bloque; lanza `SesionOcupada` si ya está tomada."""
        ...

    def ocupadas(self) -> set[int]:
        """Claves de las sesiones que alguna corrida tiene tomadas ahora."""
        ...


class BloqueosEnMemoria:
    """Bloqueos de un solo proceso, para el checkpointer en memoria y las pruebas."""

    def __init__(self) -> None:
        """Empieza sin sesiones tomadas."""
        self._tomadas: set[int] = set()
        self._candado = threading.Lock()

    @contextmanager
    def exclusivo(self, id_sesion: str) -> Iterator[None]:
        """Toma la sesión mientras dura el bloque.

        Args:
            id_sesion: Identificador de la sesión.

        Yields:
            Nada; la sesión queda tomada hasta salir del bloque.

        Raises:
            SesionOcupada: Si otra corrida ya la tiene tomada.
        """
        with self._candado:
            if clave(id_sesion) in self._tomadas:
                raise SesionOcupada(f"La sesión {id_sesion} está en curso en otra corrida.")
            self._tomadas.add(clave(id_sesion))
        try:
            yield
        finally:
            with self._candado:
                self._tomadas.discard(clave(id_sesion))

    def ocupadas(self) -> set[int]:
        """Claves de las sesiones tomadas."""
        with self._candado:
            return set(self._tomadas)


class BloqueosPostgres:
    """Bloqueos consultivos de PostgreSQL, compartidos por todos los procesos de la base."""

    def __init__(
        self, pool: ConnectionPool, configuracion: ConfiguracionBaseDatos | None = None
    ) -> None:
        """Prepara los bloqueos.

        Args:
            pool: Pool para consultar las sesiones ocupadas, sin tomarlas.
            configuracion: Conexión a la base para los bloqueos; si se omite, se lee del entorno.
        """
        self.pool = pool
        self.cadena = (configuracion or ConfiguracionBaseDatos()).cadena_conexion()

    @contextmanager
    def exclusivo(self, id_sesion: str) -> Iterator[None]:
        """Toma la sesión en una conexión dedicada mientras dura el bloque.

        El bloqueo pertenece a la conexión: se suelta al cerrarla, también si el proceso muere.
        Por eso no sale del pool, que devolvería la conexión con el bloqueo tomado.

        Args:
            id_sesion: Identificador de la sesión.

        Yields:
            Nada; la sesión queda tomada hasta salir del bloque.

        Raises:
            SesionOcupada: Si otro proceso, u otra corrida de este, ya la tiene tomada.
        """
        with psycopg.connect(
            self.cadena, autocommit=True, application_name="multiagente-bloqueo"
        ) as conexion:
            fila = conexion.execute(
                "SELECT pg_try_advisory_lock(%s, %s)", (ESPACIO, clave(id_sesion))
            ).fetchone()
            if not fila or not fila[0]:
                raise SesionOcupada(f"La sesión {id_sesion} está en curso en otro proceso.")
            yield

    def ocupadas(self) -> set[int]:
        """Claves de las sesiones que algún proceso tiene tomadas, leídas en `pg_locks`."""
        with self.pool.connection() as conexion:
            filas = conexion.execute(
                "SELECT objid FROM pg_locks WHERE locktype = 'advisory' AND classid = %s "
                "AND objsubid = 2 AND granted "
                "AND database = (SELECT oid FROM pg_database WHERE datname = current_database())",
                (ESPACIO,),
            ).fetchall()
        return {int(fila[0]) for fila in filas}
