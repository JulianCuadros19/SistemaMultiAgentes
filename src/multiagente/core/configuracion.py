"""Configuración del sistema leída de variables de entorno o del archivo .env."""

from psycopg.conninfo import make_conninfo
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfiguracionBaseDatos(BaseSettings):
    """Parámetros de conexión a PostgreSQL, tomados de las variables POSTGRES_*."""

    model_config = SettingsConfigDict(
        env_prefix="POSTGRES_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = "localhost"
    port: int = 5432
    db: str = "multiagente"
    user: str
    password: SecretStr

    def cadena_conexion(self) -> str:
        """Construye la cadena de conexión libpq, con los valores escapados por psycopg.

        Returns:
            Cadena de conexión que acepta `psycopg.connect`.
        """
        return make_conninfo(
            host=self.host,
            port=self.port,
            dbname=self.db,
            user=self.user,
            password=self.password.get_secret_value(),
        )
