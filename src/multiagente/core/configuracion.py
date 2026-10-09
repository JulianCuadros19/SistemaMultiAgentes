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
    cliente_simulado: str | None = None
    """Despliegue del cliente simulado de las pruebas; si se omite, el de N3."""

    @property
    def despliegue_cliente_simulado(self) -> str:
        """Despliegue que usa el cliente simulado: el propio o, si no se fijó, el de N3."""
        return self.cliente_simulado or self.n3_dialogo


class ConfiguracionRazonamiento(BaseSettings):
    """Esfuerzo de razonamiento y límite de salida por nodo (ESFUERZO_*, MAX_TOKENS_*).

    El límite incluye los tokens de razonamiento ocultos: si se agota antes de producir texto, la
    respuesta llega vacía y se cobra igual (ADR-0003). Los valores por defecto se fijaron con las
    mediciones de los pasos 7, 8 y 9 (ADR-0008, ADR-0010 y ADR-0011).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    esfuerzo_n3_dialogo: EsfuerzoRazonamiento = "low"
    max_tokens_n3_dialogo: PositiveInt = 4000
    esfuerzo_n5_sintesis: EsfuerzoRazonamiento = "low"
    max_tokens_n5_sintesis: PositiveInt = 8000
    esfuerzo_n8_arquitectura: EsfuerzoRazonamiento = "low"
    max_tokens_n8_arquitectura: PositiveInt = 16000
    tiempo_espera_n8_arquitectura: PositiveInt = 300
    """Segundos de espera de cada llamada de N8; la parametrización supera los 60 s."""
    esfuerzo_n10_generacion: EsfuerzoRazonamiento = "medium"
    """Con `low`, gpt-6.1-sol degeneraba archivos de prueba y casi siempre exigía reintento."""
    max_tokens_n10_generacion: PositiveInt = 32000
    tiempo_espera_n10_generacion: PositiveInt = 600
    """Segundos de espera de la llamada de N10, que produce el módulo completo con sus pruebas."""


class ConfiguracionOrquestador(BaseSettings):
    """Límites de los ciclos del grafo.

    MAX_ITERACIONES_CORRECCION acota el ciclo N10–N15, MAX_TURNOS_ELICITACION el ciclo N3–N4,
    MAX_CORRECCIONES_CALIDAD los retornos automáticos de N6 a N5 y MAX_CORRECCIONES_DISENO los
    de N9 a N8, antes de escalar a la persona.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    max_iteraciones_correccion: PositiveInt = 3
    max_turnos_elicitacion: PositiveInt = 15
    max_correcciones_calidad: PositiveInt = 2
    max_correcciones_diseno: PositiveInt = 2


class ConfiguracionSandbox(BaseSettings):
    """Entorno aislado del código generado, tomado de las variables SANDBOX_* (RNF-03).

    La imagen se construye con `docker compose --profile sandbox build sandbox`. Los límites
    acotan lo que puede consumir una ejecución; el tiempo límite es por ejecución.
    """

    model_config = SettingsConfigDict(
        env_prefix="SANDBOX_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    imagen: str = "multiagente-sandbox:1"
    tiempo_limite_s: PositiveInt = 60
    memoria: str = "512m"
    cpus: str = "1"
    procesos: PositiveInt = 128


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
