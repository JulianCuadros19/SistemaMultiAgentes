"""Agente elicitador real: implementa los servicios de N2, N3, N5 y N6 (paso 7)."""

from openai import OpenAI
from psycopg import Connection

from multiagente.agentes.elicitador.calidad import verificar_conjunto
from multiagente.agentes.elicitador.contexto import recuperar_contexto
from multiagente.agentes.elicitador.dialogo import (
    SalidaDialogo,
    mensajes_dialogo,
    validar_dialogo,
)
from multiagente.agentes.elicitador.sintesis import (
    SalidaSintesis,
    mensajes_sintesis,
    validar_sintesis,
)
from multiagente.core.configuracion import (
    ConfiguracionAzureOpenAI,
    ConfiguracionModelos,
    ConfiguracionRazonamiento,
)
from multiagente.llm.cliente import crear_cliente
from multiagente.llm.costos import cargar_tarifas
from multiagente.llm.invocador import InvocadorNodo, ParametrosNodo
from multiagente.llm.prompts import cargar_prompt
from multiagente.llm.traza import RegistradorLlamadas
from multiagente.orquestador.estado import Contexto, Conversacion, Requerimientos
from multiagente.orquestador.servicios import Dialogo, Sintesis
from multiagente.rag.colecciones import Agente
from multiagente.rag.embeddings import Vectorizador, VectorizadorTEI
from multiagente.rag.recuperacion import Recuperador


class AgenteElicitador:
    """Implementa `ServiciosElicitador` con recuperación real, modelo de lenguaje y RF-07."""

    def __init__(
        self, recuperador: Recuperador, dialogo: InvocadorNodo, sintesis: InvocadorNodo
    ) -> None:
        """Crea el agente con sus dependencias ya configuradas.

        Args:
            recuperador: Recuperador limitado a las colecciones del elicitador.
            dialogo: Invocador del modelo de N3.
            sintesis: Invocador del modelo de N5.
        """
        self.recuperador = recuperador
        self.dialogo = dialogo
        self.sintesis = sintesis

    def recuperar_contexto(self, conversacion: Conversacion) -> Contexto:
        """Recupera la guía de elicitación y el dominio de la necesidad del cliente (N2)."""
        return recuperar_contexto(self.recuperador, conversacion)

    def dialogar(self, conversacion: Conversacion, contexto: Contexto) -> Dialogo:
        """Procesa la respuesta nueva y formula la siguiente pregunta (N3)."""
        return self.dialogo.invocar_validado(
            mensajes_dialogo(conversacion, contexto),
            SalidaDialogo,
            lambda salida: validar_dialogo(salida, conversacion),
        )

    def sintetizar(
        self,
        conversacion: Conversacion,
        contexto: Contexto,
        previos: Requerimientos,
        proyecto: str,
    ) -> Sintesis:
        """Sintetiza la historia y los requerimientos formales; corrige los defectos (N5)."""
        return self.sintesis.invocar_validado(
            mensajes_sintesis(conversacion, contexto, previos, proyecto),
            SalidaSintesis,
            lambda salida: validar_sintesis(salida, contexto, previos, proyecto),
        )

    def verificar_calidad(self, requerimientos: Requerimientos) -> list[str]:
        """Devuelve los defectos de calidad de los requerimientos (N6, RF-07)."""
        return [str(defecto) for defecto in verificar_conjunto(requerimientos)]


def crear_agente_elicitador(
    conexion: Connection,
    registrador: RegistradorLlamadas,
    cliente: OpenAI | None = None,
    vectorizador: Vectorizador | None = None,
) -> AgenteElicitador:
    """Crea el agente elicitador con la configuración del entorno.

    Los despliegues salen de MODELO_N3_DIALOGO y MODELO_N5_SINTESIS, el esfuerzo y el límite de
    salida de ESFUERZO_* y MAX_TOKENS_*, y los prompts de `prompts/elicitador/`.

    Args:
        conexion: Conexión con la base de conocimiento.
        registrador: Destino de la traza de cada llamada al modelo.
        cliente: Cliente de la API OpenAI v1; si se omite, se crea con AZURE_OPENAI_*.
        vectorizador: Servicio de embeddings; si se omite, el servicio TEI local.

    Returns:
        Agente listo para inyectarse en el grafo.
    """
    modelos = ConfiguracionModelos()
    razonamiento = ConfiguracionRazonamiento()
    cliente = cliente or crear_cliente(ConfiguracionAzureOpenAI())
    tarifas = cargar_tarifas()
    dialogo = InvocadorNodo(
        cliente,
        ParametrosNodo(
            nodo="N3",
            despliegue=modelos.n3_dialogo,
            esfuerzo=razonamiento.esfuerzo_n3_dialogo,
            max_tokens_salida=razonamiento.max_tokens_n3_dialogo,
        ),
        cargar_prompt("elicitador", "dialogo"),
        registrador,
        tarifas,
    )
    sintesis = InvocadorNodo(
        cliente,
        ParametrosNodo(
            nodo="N5",
            despliegue=modelos.n5_sintesis,
            esfuerzo=razonamiento.esfuerzo_n5_sintesis,
            max_tokens_salida=razonamiento.max_tokens_n5_sintesis,
        ),
        cargar_prompt("elicitador", "sintesis"),
        registrador,
        tarifas,
    )
    recuperador = Recuperador(conexion, vectorizador or VectorizadorTEI(), Agente.ELICITADOR)
    return AgenteElicitador(recuperador, dialogo, sintesis)
