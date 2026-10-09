"""Configuración del sistema leída de variables de entorno o del archivo .env."""

from typing import Literal

from psycopg.conninfo import make_conninfo
from pydantic import Field, PositiveInt, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

EsfuerzoRazonamiento = Literal["minimal", "low", "medium", "high"]
"""Esfuerzo de razonamiento que admiten los modelos GPT-5."""


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


class ConfiguracionAzureOpenAI(BaseSettings):
    """Acceso a Azure OpenAI por la API v1, tomado de las variables AZURE_OPENAI_*."""

    model_config = SettingsConfigDict(
        env_prefix="AZURE_OPENAI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    endpoint: str
    api_key: SecretStr

    def url_base(self) -> str:
        """Construye la URL base de la API v1 a partir de la raíz del recurso.

        Acepta el endpoint con o sin barra final y con o sin el sufijo `/openai/v1`.

        Returns:
            URL de la forma `https://<recurso>.openai.azure.com/openai/v1/`.
        """
        raiz = self.endpoint.strip().rstrip("/").removesuffix("/openai/v1").rstrip("/")
        return f"{raiz}/openai/v1/"


class ConfiguracionModelos(BaseSettings):
    """Despliegue de modelo asignado a cada nodo que invoca un modelo (RNF-06).

    Cambiar el modelo de un nodo es editar su variable MODELO_* en .env.
    """

    model_config = SettingsConfigDict(
        env_prefix="MODELO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    n3_dialogo: str
    n5_sintesis: str
    n8_arquitectura: str
    n10_generacion: str
    n14_veredicto: str


class ConfiguracionRazonamiento(BaseSettings):
    """Esfuerzo de razonamiento y límite de salida por nodo (ESFUERZO_*, MAX_TOKENS_*).

    El límite incluye los tokens de razonamiento ocultos: si se agota antes de producir texto, la
    respuesta llega vacía y se cobra igual (ADR-0003). Los valores por defecto se fijaron con las
    mediciones del paso 7 (ADR-0008).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    esfuerzo_n3_dialogo: EsfuerzoRazonamiento = "low"
    max_tokens_n3_dialogo: PositiveInt = 4000
    esfuerzo_n5_sintesis: EsfuerzoRazonamiento = "medium"
    max_tokens_n5_sintesis: PositiveInt = 16000


class ConfiguracionOrquestador(BaseSettings):
    """Límites de los ciclos del grafo (MAX_ITERACIONES_CORRECCION y MAX_TURNOS_ELICITACION)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    max_iteraciones_correccion: PositiveInt = 3
    max_turnos_elicitacion: PositiveInt = 15


class ConfiguracionEmbeddings(BaseSettings):
    """Servicio local de embeddings (EMBEDDINGS_URL, EMBEDDINGS_MODELO, EMBEDDINGS_DIMENSION)."""

    model_config = SettingsConfigDict(
        env_prefix="EMBEDDINGS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    url: str = "http://localhost:8081"
    modelo: str = "BAAI/bge-m3"
    dimension: PositiveInt = 1024


class ConfiguracionRecuperacion(BaseSettings):
    """Parámetros de la recuperación híbrida, tomados de las variables RAG_*."""

    model_config = SettingsConfigDict(
        env_prefix="RAG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    fragmentos: PositiveInt = 5
    candidatos: PositiveInt = 20
    umbral_similitud: float = Field(default=0.37, ge=0, le=1)
