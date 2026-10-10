"""Agente tester real: implementa los servicios de N11 a N14 (paso 10).

Ejecuta, analiza y dictamina; no modifica el código (decisión 6 de `CLAUDE.md`). Solo consulta la
colección `criterios_calidad` (RF-29).
"""

from openai import OpenAI

from multiagente.agentes.tester.analisis import analizar_version
from multiagente.agentes.tester.contexto import recuperar_criterios
from multiagente.agentes.tester.ejecucion import ejecutar_version
from multiagente.agentes.tester.reglas import ReglaCalidad, cargar_reglas_calidad
from multiagente.agentes.tester.veredicto import dictaminar_version
from multiagente.core.configuracion import (
    ConfiguracionAzureOpenAI,
    ConfiguracionModelos,
    ConfiguracionRazonamiento,
    ConfiguracionTester,
)
from multiagente.core.esquemas.especificacion_diseno import EspecificacionDiseno
from multiagente.llm.cliente import crear_cliente
from multiagente.llm.costos import cargar_tarifas
from multiagente.llm.invocador import InvocadorNodo, ParametrosNodo
from multiagente.llm.prompts import cargar_prompt
from multiagente.llm.traza import RegistradorLlamadas
from multiagente.orquestador.estado import (
    CasoPrueba,
    Contexto,
    EjecucionPruebas,
    Requerimientos,
    Validacion,
    VersionCodigo,
)
from multiagente.orquestador.servicios import AnalisisEstatico, Dictamen
from multiagente.rag.colecciones import Agente
from multiagente.rag.embeddings import Vectorizador, VectorizadorTEI
from multiagente.rag.recuperacion import ConexionLectura, Recuperador
from multiagente.sandbox.ejecutor import EntornoAislado


class AgenteTester:
    """Implementa `ServiciosTester`: ejecuta, analiza y dictamina cada versión del módulo."""

    def __init__(
        self,
        entorno: EntornoAislado,
        recuperador: Recuperador,
        juez: InvocadorNodo | None,
        reglas: dict[str, ReglaCalidad] | None = None,
        configuracion: ConfiguracionTester | None = None,
    ) -> None:
        """Crea el agente con sus dependencias ya configuradas.

        Args:
            entorno: Entorno aislado donde se ejecuta el código (N11).
            recuperador: Recuperador limitado a la colección del tester (N13).
            juez: Invocador del modelo que juzga los casos cuyas pruebas pasaron (N14).
            reglas: Reglas de calidad; si se omiten, se leen de la base de conocimiento.
            configuracion: Umbral de hallazgos medios y tiempo límite de las pruebas.
        """
        self.entorno = entorno
        self.recuperador = recuperador
        self.juez = juez
        self.reglas = reglas or cargar_reglas_calidad()
        self.configuracion = configuracion or ConfiguracionTester()

    def ejecutar(
        self, version: VersionCodigo, especificacion: EspecificacionDiseno
    ) -> EjecucionPruebas:
        """Importa los módulos y corre las pruebas en el entorno aislado (N11)."""
        return ejecutar_version(
            self.entorno, version, especificacion, self.configuracion.tiempo_limite_pruebas_s
        )

    def analizar(
        self,
        version: VersionCodigo,
        especificacion: EspecificacionDiseno,
        requerimientos: Requerimientos,
    ) -> AnalisisEstatico:
        """Aplica el análisis estático y la conformidad arquitectónica (N12)."""
        return analizar_version(version, especificacion, requerimientos, self.reglas)

    def recuperar_criterios(self, validacion: Validacion) -> Contexto:
        """Recupera los criterios de los hallazgos y del juicio de los casos (N13)."""
        return recuperar_criterios(self.recuperador, validacion)

    def dictaminar(
        self,
        plan: tuple[CasoPrueba, ...],
        validacion: Validacion,
        contexto: Contexto,
        version: VersionCodigo,
    ) -> Dictamen:
        """Dictamina cada caso, aplica la regla de veredicto y arma la retroalimentación (N14)."""
        return dictaminar_version(
            plan,
            validacion,
            contexto,
            version,
            self.reglas,
            self.configuracion.umbral_hallazgos_media,
            self.juez,
        )


def crear_juez(
    registrador: RegistradorLlamadas, cliente: OpenAI | None = None, despliegue: str | None = None
) -> InvocadorNodo:
    """Crea el invocador del juez de N14 con la configuración del entorno.

    Args:
        registrador: Destino de la traza de cada llamada al modelo.
        cliente: Cliente de la API OpenAI v1; si se omite, se crea con AZURE_OPENAI_*.
        despliegue: Despliegue del modelo; si se omite, el de MODELO_N14_VEREDICTO. Sirve para
            comparar candidatos sin editar `.env`.

    Returns:
        Invocador con el prompt `prompts/tester/veredicto.md`.
    """
    razonamiento = ConfiguracionRazonamiento()
    n14 = ParametrosNodo(
        nodo="N14",
        despliegue=despliegue or ConfiguracionModelos().n14_veredicto,
        esfuerzo=razonamiento.esfuerzo_n14_veredicto,
        max_tokens_salida=razonamiento.max_tokens_n14_veredicto,
    )
    return InvocadorNodo(
        cliente or crear_cliente(ConfiguracionAzureOpenAI()),
        n14,
        cargar_prompt("tester", "veredicto"),
        registrador,
        cargar_tarifas(),
    )


def crear_agente_tester(
    conexion: ConexionLectura,
    registrador: RegistradorLlamadas,
    cliente: OpenAI | None = None,
    vectorizador: Vectorizador | None = None,
    entorno: EntornoAislado | None = None,
    despliegue_juez: str | None = None,
) -> AgenteTester:
    """Crea el agente tester con la configuración del entorno.

    Args:
        conexion: Conexión con la base de conocimiento.
        registrador: Destino de la traza de cada llamada al modelo.
        cliente: Cliente de la API OpenAI v1; si se omite, se crea con AZURE_OPENAI_*.
        vectorizador: Servicio de embeddings; si se omite, el servicio TEI local.
        entorno: Entorno aislado; si se omite, el de las variables SANDBOX_*.
        despliegue_juez: Despliegue del juez; si se omite, el de MODELO_N14_VEREDICTO.

    Returns:
        Agente listo para inyectarse en el grafo.
    """
    recuperador = Recuperador(conexion, vectorizador or VectorizadorTEI(), Agente.TESTER)
    return AgenteTester(
        entorno or EntornoAislado(),
        recuperador,
        crear_juez(registrador, cliente, despliegue_juez),
    )
