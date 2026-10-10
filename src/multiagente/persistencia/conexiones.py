"""Conexiones a PostgreSQL para procesos de larga vida, como la web (paso 12).

Un proceso que atiende sesiones durante horas no puede depender de una sola conexión: si la base
se reinicia, todas las operaciones fallarían hasta reiniciar el proceso. Un pool verifica cada
conexión antes de entregarla y abre una nueva si la anterior se cayó.
"""

from collections.abc import Iterator, Sequence
from contextlib import contextmanager

from psycopg_pool import ConnectionPool

from multiagente.core.configuracion import ConfiguracionBaseDatos


@contextmanager
def abrir_pool(
    configuracion: ConfiguracionBaseDatos | None = None,
    aplicacion: str = "multiagente",
    **opciones: object,
) -> Iterator[ConnectionPool]:
    """Abre un pool que verifica cada conexión antes de usarla y se cierra al salir.

    Args:
        configuracion: Conexión a la base; si se omite, se lee del entorno.
        aplicacion: Nombre con que las conexiones aparecen en `pg_stat_activity`.
        **opciones: Opciones de cada conexión, además de `autocommit`.

    Yields:
        El pool abierto.
    """
    configuracion = configuracion or ConfiguracionBaseDatos()
    with ConnectionPool(
        configuracion.cadena_conexion(),
        min_size=1,
        max_size=4,
        kwargs={"autocommit": True, "application_name": aplicacion, **opciones},
        check=ConnectionPool.check_connection,
        open=True,
    ) as pool:
        yield pool


class FilasLeidas:
    """Filas ya leídas de una consulta: la conexión volvió al pool antes de entregarlas."""

    def __init__(self, filas: Sequence[tuple]) -> None:
        """Guarda las filas.

        Args:
            filas: Filas de la consulta.
        """
        self.filas = list(filas)

    def fetchall(self) -> list[tuple]:
        """Devuelve todas las filas, como `Cursor.fetchall`."""
        return self.filas


class ConexionDePool:
    """Conexión de lectura sobre un pool: cada consulta toma una conexión verificada.

    Ofrece lo que el recuperador usa de una conexión (`execute(...).fetchall()`), de modo que la
    base de conocimiento sobrevive a un reinicio de PostgreSQL.
    """

    def __init__(self, pool: ConnectionPool) -> None:
        """Usa un pool abierto con `abrir_pool`.

        Args:
            pool: Pool de conexiones.
        """
        self.pool = pool

    def execute(self, consulta: str, parametros: object = None) -> FilasLeidas:
        """Ejecuta una consulta con una conexión del pool y lee todas sus filas.

        Args:
            consulta: Consulta SQL.
            parametros: Parámetros de la consulta.

        Returns:
            Las filas leídas.
        """
        with self.pool.connection() as conexion:
            return FilasLeidas(conexion.execute(consulta, parametros).fetchall())
