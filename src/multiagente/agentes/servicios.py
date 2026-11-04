"""Servicios con los cuatro agentes reales, listos para inyectarse en el grafo (paso 11).

El elicitador, el arquitecto y el tester comparten la conexión con la base de conocimiento, el
servicio de embeddings y el cliente del modelo. El desarrollador recibe solo el cliente: no
consulta bases de conocimiento (decisión 1 de `CLAUDE.md`, RF-29).
"""

from openai import OpenAI

from multiagente.agentes.arquitecto.servicio import crear_agente_arquitecto
from multiagente.agentes.desarrollador.servicio import crear_agente_desarrollador
from multiagente.agentes.elicitador.servicio import crear_agente_elicitador
from multiagente.agentes.tester.reglas import cargar_reglas_calidad, estilo_bloqueante
from multiagente.agentes.tester.servicio import crear_agente_tester
from multiagente.core.configuracion import ConfiguracionAzureOpenAI, ConfiguracionTester
from multiagente.llm.cliente import crear_cliente
from multiagente.llm.traza import RegistradorLlamadas
from multiagente.orquestador.servicios import Servicios
from multiagente.rag.embeddings import Vectorizador, VectorizadorTEI
from multiagente.rag.recuperacion import ConexionLectura
from multiagente.sandbox.ejecutor import EntornoAislado


def crear_servicios(
    conexion: ConexionLectura,
    registrador: RegistradorLlamadas,
    cliente: OpenAI | None = None,
    vectorizador: Vectorizador | None = None,
    entorno: EntornoAislado | None = None,
) -> Servicios:
    """Crea los servicios de los cuatro agentes reales con la configuración del entorno.

    Args:
        conexion: Conexión con la base de conocimiento.
        registrador: Destino de la traza de cada llamada al modelo.
        cliente: Cliente de la API OpenAI v1; si se omite, se crea con AZURE_OPENAI_*.
        vectorizador: Servicio de embeddings; si se omite, el servicio TEI local.
        entorno: Entorno aislado del tester; si se omite, el de las variables SANDBOX_*.

    Returns:
        Servicios del elicitador, el arquitecto, el desarrollador y el tester.
    """
    cliente = cliente or crear_cliente(ConfiguracionAzureOpenAI())
    vectorizador = vectorizador or VectorizadorTEI()
    return Servicios(
        elicitador=crear_agente_elicitador(conexion, registrador, cliente, vectorizador),
        arquitecto=crear_agente_arquitecto(conexion, registrador, cliente, vectorizador),
        # El desarrollador aplica el criterio de estilo del tester antes de entregarle la
        # versión, sin importarlo (ADR-0015).
        desarrollador=crear_agente_desarrollador(
            registrador,
            cliente,
            estilo_bloqueante(
                cargar_reglas_calidad(), ConfiguracionTester().umbral_hallazgos_media
            ),
        ),
        tester=crear_agente_tester(
            conexion, registrador, cliente, vectorizador, entorno or EntornoAislado()
        ),
    )
