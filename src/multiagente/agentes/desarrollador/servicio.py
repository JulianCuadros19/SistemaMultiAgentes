"""Agente desarrollador real: implementa el servicio de N10 (paso 9).

No recibe recuperador ni conexión con la base de conocimiento: su entrada, requerimientos y
especificación, ya es una definición completa (decisión 1 de `CLAUDE.md`, RF-29).
"""

from openai import OpenAI

from multiagente.agentes.desarrollador.generacion import (
    SalidaGeneracion,
    mensajes_generacion,
    version_desde_salida,
)
from multiagente.core.configuracion import (
    ConfiguracionAzureOpenAI,
    ConfiguracionModelos,
    ConfiguracionRazonamiento,
)
from multiagente.core.esquemas.especificacion_diseno import EspecificacionDiseno
from multiagente.core.estilo import EstiloGenerado, cargar_estilo
from multiagente.llm.cliente import crear_cliente
from multiagente.llm.costos import cargar_tarifas
from multiagente.llm.invocador import InvocadorNodo, ParametrosNodo
from multiagente.llm.prompts import cargar_prompt
from multiagente.llm.traza import RegistradorLlamadas
from multiagente.orquestador.estado import Requerimientos, Validacion, VersionCodigo


class AgenteDesarrollador:
    """Implementa `ServiciosDesarrollador`: genera el módulo a partir de la especificación."""

    def __init__(self, generacion: InvocadorNodo, estilo: EstiloGenerado | None = None) -> None:
        """Crea el agente con su invocador ya configurado.

        Args:
            generacion: Invocador de la generación de N10.
            estilo: Configuración de estilo; si se omite, se lee de `config/estilo_generado/`.
        """
        self.generacion = generacion
        self.estilo = estilo or cargar_estilo()

    def generar(
        self,
        requerimientos: Requerimientos,
        especificacion: EspecificacionDiseno,
        validacion: Validacion,
        previa: VersionCodigo | None,
    ) -> VersionCodigo:
        """Genera el módulo o corrige la versión previa con la retroalimentación (N10).

        Una salida que no pasa la verificación estructural se reintenta una vez con los
        problemas a la vista del modelo; si vuelve a fallar, el nodo falla y la sesión se
        reanuda desde su último punto de control.
        """
        return self.generacion.invocar_validado(
            mensajes_generacion(requerimientos, especificacion, self.estilo, validacion, previa),
            SalidaGeneracion,
            lambda salida: version_desde_salida(
                salida, requerimientos, especificacion, validacion, previa, self.estilo
            ),
        )


def crear_agente_desarrollador(
    registrador: RegistradorLlamadas, cliente: OpenAI | None = None
) -> AgenteDesarrollador:
    """Crea el agente desarrollador con la configuración del entorno.

    El despliegue sale de MODELO_N10_GENERACION; el esfuerzo, el límite de salida y el tiempo
    de espera, de ESFUERZO_N10_GENERACION, MAX_TOKENS_N10_GENERACION y
    TIEMPO_ESPERA_N10_GENERACION; el prompt, de `prompts/desarrollador/`.

    Args:
        registrador: Destino de la traza de cada llamada al modelo.
        cliente: Cliente de la API OpenAI v1; si se omite, se crea con AZURE_OPENAI_*.

    Returns:
        Agente listo para inyectarse en el grafo.
    """
    razonamiento = ConfiguracionRazonamiento()
    n10 = ParametrosNodo(
        nodo="N10",
        despliegue=ConfiguracionModelos().n10_generacion,
        esfuerzo=razonamiento.esfuerzo_n10_generacion,
        max_tokens_salida=razonamiento.max_tokens_n10_generacion,
        tiempo_espera_s=razonamiento.tiempo_espera_n10_generacion,
    )
    generacion = InvocadorNodo(
        cliente or crear_cliente(ConfiguracionAzureOpenAI()),
        n10,
        cargar_prompt("desarrollador", "generacion"),
        registrador,
        cargar_tarifas(),
    )
    return AgenteDesarrollador(generacion)
