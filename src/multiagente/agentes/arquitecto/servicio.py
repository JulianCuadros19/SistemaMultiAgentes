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
from multiagente.agentes.arquitecto.recorridos import (
    anotar_escenarios,
    errores_de_recorridos,
    recorridos_desde_salida,
)
from multiagente.agentes.arquitecto.seleccion import (
    SalidaSeleccion,
    con_revisiones,
    entrada_de_revision,
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
from multiagente.core.esquemas.especificacion_diseno import EspecificacionDiseno, diferencias
from multiagente.llm.cliente import crear_cliente
from multiagente.llm.costos import cargar_tarifas
from multiagente.llm.invocador import ErrorValidacionSalida, InvocadorNodo, ParametrosNodo
from multiagente.llm.prompts import cargar_prompt
from multiagente.llm.traza import RegistradorLlamadas
from multiagente.orquestador.estado import (
    Arquitectura,
    Contexto,
    RecorridoEscenario,
    Requerimientos,
)
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
        la observación puede cuestionar la arquitectura elegida, y el registro de decisión gana
        una revisión con la respuesta y los cambios de la especificación.

        La parametrización se valida con el esquema del Anexo B y con los recorridos de los
        escenarios; si incumple, el modelo reintenta una vez con los problemas a la vista. La
        especificación que se entrega lleva los escenarios anotados en sus interfaces.
        """
        aprobados = {r.id_requerimiento for r in requerimientos.requerimientos}
        nuevas = previa.observaciones_revisor[previa.observaciones_atendidas :]
        respuesta = ""
        if previa.registro_decision is None or previa.especificacion is None or nuevas:
            salida = self.seleccion.invocar_validado(
                mensajes_seleccion(requerimientos, contexto, previa),
                SalidaSeleccion,
                lambda s: validar_seleccion(s, aprobados, frozenset(self.titulos), bool(nuevas)),
            )
            registro = registro_de_decision(
                salida,
                self.titulos,
                datetime.now(UTC).date(),
                etiquetar(contexto, COLECCIONES_ARQUITECTO),
            )
            elegida = salida.elegida
            respuesta = salida.respuesta_observaciones
        else:
            registro = previa.registro_decision
            elegida = previa.especificacion.arquitectura_base
        version = f"0.{previa.disenos + 1}"
        revisiones = previa.revisiones
        numero = len(revisiones) + 1
        # La parametrización ve la revisión en curso con la respuesta de la selección; sus
        # cambios se conocen al final.
        en_curso = (
            (entrada_de_revision(numero, version, nuevas, respuesta, None),) if nuevas else ()
        )
        registro = con_revisiones(registro, (*revisiones, *en_curso))
        especificacion, capacidades, recorridos = self.parametrizacion.invocar_validado(
            mensajes_parametrizacion(requerimientos, contexto, previa, elegida, registro),
            SalidaEspecificacion,
            lambda s: self._parametrizacion_validada(s, requerimientos, elegida, version),
        )
        if nuevas:
            cambios = (
                diferencias(previa.especificacion, especificacion)
                if previa.especificacion is not None
                else ["Primera especificación de la sesión."]
            )
            revisiones = (
                *revisiones,
                entrada_de_revision(numero, version, nuevas, respuesta, cambios),
            )
            registro = con_revisiones(registro, revisiones)
        return Diseno(
            registro_decision=registro,
            especificacion=anotar_escenarios(especificacion, recorridos),
            capacidades_no_cubiertas=capacidades,
            recorridos=recorridos,
            revisiones=revisiones,
        )

    @staticmethod
    def _parametrizacion_validada(
        salida: SalidaEspecificacion,
        requerimientos: Requerimientos,
        elegida: str,
        version: str,
    ) -> tuple[EspecificacionDiseno, tuple[str, ...], tuple[RecorridoEscenario, ...]]:
        especificacion = especificacion_desde_salida(salida, requerimientos, elegida, version)
        recorridos = recorridos_desde_salida(salida.recorridos)
        if errores := errores_de_recorridos(especificacion, requerimientos, recorridos):
            raise ErrorValidacionSalida(errores)
        capacidades = tuple(c.strip() for c in salida.capacidades_no_cubiertas if c.strip())
        return especificacion, capacidades, recorridos

    def validar(
        self,
        especificacion: EspecificacionDiseno,
        requerimientos: Requerimientos,
        recorridos: tuple[RecorridoEscenario, ...] = (),
    ) -> list[str]:
        """Aplica las tres validaciones del Anexo B y verifica los recorridos (N9)."""
        return [
            *validar_especificacion(
                especificacion, requerimientos, self.catalogo, frozenset(self.titulos)
            ),
            *errores_de_recorridos(especificacion, requerimientos, recorridos),
        ]


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
