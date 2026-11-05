"""Configuración del sistema leída de variables de entorno o del archivo .env."""

from decimal import Decimal
from pathlib import Path
from typing import Literal

from psycopg.conninfo import make_conninfo
from pydantic import Field, NonNegativeInt, PositiveInt, SecretStr
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
    esfuerzo_n14_veredicto: EsfuerzoRazonamiento = "low"
    max_tokens_n14_veredicto: PositiveInt = 6000


class ConfiguracionOrquestador(BaseSettings):
    """Límites de los ciclos del grafo y presupuesto de cada sesión.

    MAX_ITERACIONES_CORRECCION acota el ciclo N10–N15, MAX_TURNOS_ELICITACION el ciclo N3–N4,
    MAX_CORRECCIONES_CALIDAD los retornos automáticos de N6 a N5 y MAX_CORRECCIONES_DISENO los
    de N9 a N8, antes de escalar a la persona. PRESUPUESTO_MAXIMO_POR_MODULO_USD es el costo de
    los modelos que puede gastar una sesión antes de detenerse a esperar que alguien lo amplíe
    (RNF-10). Una variable vacía toma el valor por defecto.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_ignore_empty=True,
    )

    max_iteraciones_correccion: PositiveInt = 3
    # 18 desde el ADR-0015: la fase de casos límite y la pregunta por algo más agregan hasta
    # cuatro turnos antes del resumen.
    max_turnos_elicitacion: PositiveInt = 18
    max_correcciones_calidad: PositiveInt = 2
    max_correcciones_diseno: PositiveInt = 2
    # Decisión del equipo del paso 13 (ADR-0016): cubre con holgura el máximo de la corrida final
    # (0,87 USD) y la sesión de pensiones, con sus devoluciones (0,97 USD).
    presupuesto_maximo_por_modulo_usd: Decimal = Field(default=Decimal("1.50"), gt=0)


class ConfiguracionTester(BaseSettings):
    """Regla de veredicto y ejecución del tester (UMBRAL_HALLAZGOS_MEDIA, TIEMPO_LIMITE_PRUEBAS_S).

    Con el umbral en 0, cualquier hallazgo de severidad media rechaza el módulo (cal-sv), por
    decisión del equipo (ADR-0012).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    umbral_hallazgos_media: NonNegativeInt = 0
    tiempo_limite_pruebas_s: PositiveInt = 120


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


class ConfiguracionInterfaces(BaseSettings):
    """Interfaces de operación, tomadas de las variables INTERFAZ_* (paso 12).

    La traza y la carpeta de trabajo quedan en `data/local/`, que no se versiona. La web escucha
    solo en la máquina local: el acceso remoto y la autenticación se deciden en el paso 14.
    """

    model_config = SettingsConfigDict(
        env_prefix="INTERFAZ_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    traza_llamadas: Path = Path("data/local/traza-llamadas.jsonl")
    """Archivo JSONL con cada llamada a un modelo y su sesión, sin el contenido de los mensajes."""
    carpeta_trabajo: Path = Path("data/local/sesiones")
    """Carpeta donde la consola escribe el código de cada versión para revisarlo."""
    host_web: str = "127.0.0.1"
    puerto_web: PositiveInt = 8000
