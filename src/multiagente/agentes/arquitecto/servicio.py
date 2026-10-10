"""Agente arquitecto real: implementa los servicios de N7, N8 y N9 (paso 8)."""

from datetime import UTC, datetime

from openai import OpenAI

from multiagente.agentes.arquitecto.catalogo import (
    CatalogoTecnologico,
    cargar_catalogo_tecnologico,
    titulos_del_catalogo,
)
from multiagente.agentes.arquitecto.contexto import COLECCIONES_ARQUITECTO, recuperar_catalogo
from multiagente.agentes.arquitecto.parametrizacion import (
    SalidaEspecificacion,
    especificacion_desde_salida,
    mensajes_parametrizacion,
)
from multiagente.agentes.arquitecto.seleccion import (
    SalidaSeleccion,
    mensajes_seleccion,
    registro_de_decision,
    validar_seleccion,
)
from multiagente.agentes.arquitecto.validacion import validar_especificacion
from multiagente.agentes.contexto import etiquetar
from multiagente.core.configuracion import (
    ConfiguracionAzureOpenAI,
    ConfiguracionModelos,
    ConfiguracionRazonamiento,
)
from multiagente.core.esquemas.especificacion_diseno import EspecificacionDiseno
from multiagente.llm.cliente import crear_cliente
from multiagente.llm.costos import cargar_tarifas
from multiagente.llm.invocador import InvocadorNodo, ParametrosNodo
from multiagente.llm.prompts import cargar_prompt
from multiagente.llm.traza import RegistradorLlamadas
from multiagente.orquestador.estado import Arquitectura, Contexto, Requerimientos
from multiagente.orquestador.servicios import Diseno
from multiagente.rag.colecciones import Agente
from multiagente.rag.embeddings import Vectorizador, VectorizadorTEI
from multiagente.rag.recuperacion import ConexionLectura, Recuperador


class AgenteArquitecto:
    """Implementa `ServiciosArquitecto`: selecciona y parametriza del catálogo cerrado."""

    def __init__(
        self,
        recuperador: Recuperador,
        seleccion: InvocadorNodo,
        parametrizacion: InvocadorNodo,
        catalogo: CatalogoTecnologico | None = None,
        titulos: dict[str, str] | None = None,
    ) -> None:
        """Crea el agente con sus dependencias ya configuradas.

        Args:
            recuperador: Recuperador limitado a la colección del arquitecto.
            seleccion: Invocador de la selección de N8.
            parametrizacion: Invocador de la parametrización de N8.
            catalogo: Catálogo tecnológico; si se omite, se lee de la base de conocimiento.
            titulos: Arquitecturas del catálogo con su título; si se omiten, se leen de ella.
        """
        self.recuperador = recuperador
        self.seleccion = seleccion
        self.parametrizacion = parametrizacion
        self.catalogo = catalogo or cargar_catalogo_tecnologico()
        self.titulos = titulos or titulos_del_catalogo()

    def recuperar_catalogo(self, requerimientos: Requerimientos) -> Contexto:
        """Recupera las seis arquitecturas, la metodología y los patrones (N7)."""
        return recuperar_catalogo(self.recuperador, requerimientos)

    def disenar(
        self, requerimientos: Requerimientos, contexto: Contexto, previa: Arquitectura
    ) -> Diseno:
        """Selecciona la arquitectura y la parametriza; corrige el diseño previo si lo hay (N8).

        Con errores de validación de N9 solo se vuelve a parametrizar: la elección sigue en
        pie. Si el revisor dejó una observación nueva, se vuelve también a seleccionar, porque
        la observación puede cuestionar la arquitectura elegida.
        """
        aprobados = {r.id_requerimiento for r in requerimientos.requerimientos}
        observacion_nueva = len(previa.observaciones_revisor) > previa.observaciones_atendidas
        if previa.registro_decision is None or previa.especificacion is None or observacion_nueva:
            salida = self.seleccion.invocar_validado(
                mensajes_seleccion(requerimientos, contexto, previa),
                SalidaSeleccion,
                lambda s: validar_seleccion(s, aprobados, frozenset(self.titulos)),
            )
            registro = registro_de_decision(
                salida,
                self.titulos,
                datetime.now(UTC).date(),
                etiquetar(contexto, COLECCIONES_ARQUITECTO),
            )
            elegida = salida.elegida
        else:
            registro = previa.registro_decision
            elegida = previa.especificacion.arquitectura_base
        version = f"0.{previa.disenos + 1}"
        especificacion, capacidades = self.parametrizacion.invocar_validado(
            mensajes_parametrizacion(requerimientos, contexto, previa, elegida, registro),
            SalidaEspecificacion,
            lambda s: (
                especificacion_desde_salida(s, requerimientos, elegida, version),
                tuple(c.strip() for c in s.capacidades_no_cubiertas if c.strip()),
            ),
        )
        return Diseno(
            registro_decision=registro,
            especificacion=especificacion,
            capacidades_no_cubiertas=capacidades,
        )

    def validar(
        self, especificacion: EspecificacionDiseno, requerimientos: Requerimientos
    ) -> list[str]:
        """Aplica las tres validaciones del Anexo B (N9)."""
        return validar_especificacion(
            especificacion, requerimientos, self.catalogo, frozenset(self.titulos)
        )


def crear_agente_arquitecto(
    conexion: ConexionLectura,
    registrador: RegistradorLlamadas,
    cliente: OpenAI | None = None,
    vectorizador: Vectorizador | None = None,
) -> AgenteArquitecto:
    """Crea el agente arquitecto con la configuración del entorno.

    El despliegue sale de MODELO_N8_ARQUITECTURA; el esfuerzo, el límite de salida y el tiempo
    de espera, de ESFUERZO_N8_ARQUITECTURA, MAX_TOKENS_N8_ARQUITECTURA y
    TIEMPO_ESPERA_N8_ARQUITECTURA; los prompts, de
    `prompts/arquitecto/`. Las dos llamadas de N8 usan los parámetros del nodo.

    Args:
        conexion: Conexión con la base de conocimiento.
        registrador: Destino de la traza de cada llamada al modelo.
        cliente: Cliente de la API OpenAI v1; si se omite, se crea con AZURE_OPENAI_*.
        vectorizador: Servicio de embeddings; si se omite, el servicio TEI local.

    Returns:
        Agente listo para inyectarse en el grafo.
    """
    razonamiento = ConfiguracionRazonamiento()
    n8 = ParametrosNodo(
        nodo="N8",
        despliegue=ConfiguracionModelos().n8_arquitectura,
        esfuerzo=razonamiento.esfuerzo_n8_arquitectura,
        max_tokens_salida=razonamiento.max_tokens_n8_arquitectura,
        tiempo_espera_s=razonamiento.tiempo_espera_n8_arquitectura,
    )
    cliente = cliente or crear_cliente(ConfiguracionAzureOpenAI())
    tarifas = cargar_tarifas()
    seleccion = InvocadorNodo(
        cliente, n8, cargar_prompt("arquitecto", "seleccion"), registrador, tarifas
    )
    parametrizacion = InvocadorNodo(
        cliente, n8, cargar_prompt("arquitecto", "parametrizacion"), registrador, tarifas
    )
    recuperador = Recuperador(conexion, vectorizador or VectorizadorTEI(), Agente.ARQUITECTO)
    return AgenteArquitecto(recuperador, seleccion, parametrizacion)
