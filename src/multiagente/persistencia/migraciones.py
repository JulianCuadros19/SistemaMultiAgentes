"""Migraciones del esquema: archivos SQL versionados en `db/migraciones/`, aplicados en orden."""

import hashlib
from pathlib import Path

from psycopg import Connection

CARPETA_MIGRACIONES = Path(__file__).resolve().parents[3] / "db" / "migraciones"
"""Carpeta de migraciones del repositorio."""

TABLA_REGISTRO = """
CREATE TABLE IF NOT EXISTS migraciones_esquema (
    version     text PRIMARY KEY,
    huella      char(64) NOT NULL,
    aplicada    timestamptz NOT NULL DEFAULT now()
)
"""


class ErrorMigracionModificada(RuntimeError):
    """Una migración ya aplicada cambió de contenido."""


def _huella(sql: str) -> str:
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()


def aplicar_migraciones(conexion: Connection, carpeta: Path = CARPETA_MIGRACIONES) -> list[str]:
    """Aplica en orden las migraciones pendientes dentro de la transacción de la conexión.

    Cada archivo `NNNN_nombre.sql` se aplica una sola vez y queda registrado con su huella
    SHA-256. Las migraciones aplicadas no se modifican: un cambio se hace con un archivo nuevo.
    El llamador confirma o revierte la transacción.

    Args:
        conexion: Conexión a PostgreSQL. Las tablas se crean en el primer esquema del
            `search_path`.
        carpeta: Carpeta con los archivos de migración.

    Returns:
        Versiones aplicadas en esta llamada, en orden.

    Raises:
        ErrorMigracionModificada: Si el contenido de una migración ya aplicada cambió.
    """
    conexion.execute(TABLA_REGISTRO)
    aplicadas = {
        version: huella
        for version, huella in conexion.execute(
            "SELECT version, huella FROM migraciones_esquema"
        ).fetchall()
    }
    nuevas: list[str] = []
    for archivo in sorted(carpeta.glob("*.sql")):
        version = archivo.stem
        sql = archivo.read_text(encoding="utf-8")
        huella = _huella(sql)
        if version in aplicadas:
            if aplicadas[version] != huella:
                raise ErrorMigracionModificada(
                    f"La migración {version} ya aplicada cambió de contenido; cree una nueva"
                )
            continue
        conexion.execute(sql)
        conexion.execute(
            "INSERT INTO migraciones_esquema (version, huella) VALUES (%s, %s)", (version, huella)
        )
        nuevas.append(version)
    return nuevas
