"""Líneas base de un solo modelo de lenguaje (paso 15, ADR-0019).

**Con diálogo.** Un solo despliegue de Azure OpenAI, con un solo prompt
(`evaluacion/modelo_unico.md`), atiende la necesidad de un caso de principio a fin y sin la
arquitectura del sistema:
1. conversa con el mismo cliente simulado que usa la evaluación del sistema, una intervención por
   turno, hasta que decide que tiene lo suficiente o llega al mismo límite de turnos del cliente;
2. entrega en una sola respuesta el código, las pruebas y `USO.md`.

**De un solo prompt.** El mismo despliegue recibe en un mensaje lo que sabe el cliente
(`evaluacion/llm_un_prompt.md`) y entrega, sin diálogo. Es el mejor caso para un modelo solo, porque
tiene la información completa.

No usa recuperación, puntos de control ni tester. Del entorno recibe lo mismo que N10: la
configuración de estilo del código generado y los paquetes del entorno aislado. Una entrega que
no se puede usar se reintenta una vez, como N10 ante su verificación estructural: sin código, sin
pruebas, sin `USO.md`, con rutas inseguras o con errores de sintaxis de Python 3.11.
"""

import ast
import json
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, ConfigDict

from multiagente.core.configuracion import ConfiguracionModelos, ConfiguracionRazonamiento
from multiagente.core.estilo import EstiloGenerado, cargar_estilo
from multiagente.interfaces.cliente_simulado import (
    RAIZ_EVALUACION,
    CasoElicitacion,
    ClienteSimulado,
)
from multiagente.llm.cliente import ErrorRespuestaModelo
from multiagente.llm.invocador import ErrorValidacionSalida, InvocadorNodo, ParametrosNodo
from multiagente.llm.prompts import leer_prompt
from multiagente.llm.traza import RegistroEnMemoria
from multiagente.orquestador.estado import Conversacion, Emisor, Turno
from multiagente.sandbox.ejecutor import es_ruta_segura
from multiagente.sandbox.requisitos import requisitos_del_entorno

RUTA_PROMPT = RAIZ_EVALUACION / "modelo_unico.md"
"""Prompt de la línea base con diálogo."""
RUTA_PROMPT_UN_PROMPT = RAIZ_EVALUACION / "llm_un_prompt.md"
"""Prompt de la línea base de un solo prompt."""

NODO_DIALOGO = "modelo_unico_dialogo"
NODO_ENTREGA = "modelo_unico_entrega"
NODO_UN_PROMPT = "llm_un_prompt"
SECCION_DEL_CLIENTE = "## Lo que sabes"
"""Desde aquí, la ficha dice lo que sabe el cliente; antes va la instrucción del simulado."""
NODO_CLIENTE = "cliente_simulado"
PYTHON = "3.11"
"""Versión mínima del catálogo tecnológico, la del entorno aislado."""


class PasoDialogo(BaseModel):
    """Salida del modelo único en el diálogo."""

    model_config = ConfigDict(extra="forbid")

    pregunta: str
    listo: bool


class ArchivoEntregado(BaseModel):
    """Un archivo de la entrega."""

    model_config = ConfigDict(extra="forbid")

    ruta: str
    contenido: str


class Entrega(BaseModel):
    """Salida del modelo único en la entrega."""

    model_config = ConfigDict(extra="forbid")

    archivos: list[ArchivoEntregado]


def problemas_de_la_entrega(archivos: dict[str, str]) -> list[str]:
    """Lo que impide usar una entrega: le falta lo mínimo o no compila.

    Args:
        archivos: Contenido de cada archivo por su ruta.

    Returns:
        Un problema por defecto; vacío si la entrega se puede evaluar.
    """
    if not archivos:
        return ["La entrega no trae archivos."]
    problemas = [f"Ruta insegura: {ruta!r}" for ruta in archivos if not es_ruta_segura(ruta)]
    if not any(ruta.startswith("src/") and ruta.endswith(".py") for ruta in archivos):
        problemas.append("Falta el código en src/.")
    if not any(ruta.startswith("tests/") and ruta.endswith(".py") for ruta in archivos):
        problemas.append("Faltan las pruebas en tests/.")
    if "USO.md" not in archivos:
        problemas.append("Falta USO.md.")
    for ruta, contenido in archivos.items():
        if ruta.endswith(".py"):
            try:
                ast.parse(contenido, filename=ruta, feature_version=(3, 11))
            except SyntaxError as error:
                problemas.append(
                    f"{ruta}: error de sintaxis en la línea {error.lineno}: {error.msg}"
                )
    return problemas


def validar_entrega(entrega: Entrega) -> dict[str, str]:
    """Convierte la entrega en archivos o la rechaza con sus problemas.

    Args:
        entrega: Salida del modelo.

    Returns:
        El contenido de cada archivo por su ruta.

    Raises:
        ErrorValidacionSalida: Si la entrega no se puede evaluar.
    """
    archivos = {archivo.ruta: archivo.contenido for archivo in entrega.archivos}
    if problemas := problemas_de_la_entrega(archivos):
        raise ErrorValidacionSalida(problemas)
    return archivos


class ResultadoModeloUnico(BaseModel):
    """Una corrida de la línea base sobre un caso.

    Attributes:
        caso: Identificador del caso.
        corrida: Identificador de la corrida, que va también en la traza.
        despliegue: Despliegue del modelo único.
        prompt: Identificador y versión del prompt.
        transcripcion: Cada intervención, con su emisor: `cliente` o `modelo`.
        turnos_cliente: Intervenciones del cliente, con la necesidad inicial.
        llego_al_limite: Si el diálogo terminó por el límite de turnos.
        archivos: La entrega; vacía si no la hubo.
        error: Por qué no hubo entrega, si no la hubo.
        reintentos_entrega: Entregas rechazadas antes de la aceptada.
        tiempo_total_s: Tiempo de reloj de la corrida.
        tiempo_cliente_s: Parte del tiempo que tardó el cliente simulado en responder.
        tiempo_entrega_s: Tiempo de la entrega, con su reintento.
        costo_modelo_usd: Costo de las llamadas del modelo único.
        costo_cliente_usd: Costo del cliente simulado, que no se cuenta en el del enfoque.
        llamadas_modelo: Llamadas del modelo único.
    """

    caso: str
    corrida: str
    despliegue: str
    prompt: str
    transcripcion: list[dict[str, str]]
    turnos_cliente: int
    llego_al_limite: bool
    archivos: dict[str, str]
    error: str | None
    reintentos_entrega: int
    tiempo_total_s: float
    tiempo_cliente_s: float
    tiempo_entrega_s: float
    costo_modelo_usd: Decimal
    costo_cliente_usd: Decimal
    llamadas_modelo: int


@dataclass(frozen=True)
class ModeloUnico:
    """El modelo único con sus dos momentos y lo que recibe del entorno.

    Attributes:
        dialogo: Invocador del diálogo, con el prompt único.
        entrega: Invocador de la entrega, con el mismo prompt y más salida y razonamiento.
        estilo: Configuración de estilo del código generado.
        paquetes: Requisitos del entorno aislado, como `fastapi==0.141.1`.
        limite_turnos: Intervenciones del cliente, con la necesidad, en que termina el diálogo.
    """

    dialogo: InvocadorNodo
    entrega: InvocadorNodo
    estilo: EstiloGenerado
    paquetes: tuple[str, ...]
    limite_turnos: int

    def _transcripcion(self, turnos: Sequence[Turno]) -> list[dict[str, str]]:
        return [
            {"emisor": "cliente" if t.emisor is Emisor.CLIENTE else "modelo", "texto": t.texto}
            for t in turnos
        ]

    def _mensaje(self, datos: dict[str, object]) -> list[ChatCompletionMessageParam]:
        return [{"role": "user", "content": json.dumps(datos, ensure_ascii=False)}]

    def resolver(
        self,
        caso: CasoElicitacion,
        cliente: ClienteSimulado,
        registro: RegistroEnMemoria,
        corrida: str,
    ) -> ResultadoModeloUnico:
        """Conversa con el cliente simulado y entrega el módulo.

        Args:
            caso: Caso sintético, con la necesidad y lo que sabe el cliente.
            cliente: Cliente simulado del caso.
            registro: Registro de las llamadas del modelo único y del cliente, del que salen el
                costo y el tiempo del cliente. Debe estar vacío al empezar.
            corrida: Identificador de la corrida.

        Returns:
            El resultado, con la entrega o el error que la impidió.
        """
        inicio = time.perf_counter()
        turnos = [Turno(emisor=Emisor.CLIENTE, texto=caso.necesidad, fecha=datetime.now(UTC))]
        error: str | None = None
        archivos: dict[str, str] = {}
        tiempo_entrega = 0.0
        try:
            while Conversacion(turnos=tuple(turnos)).turnos_cliente < self.limite_turnos:
                restantes = self.limite_turnos - Conversacion(turnos=tuple(turnos)).turnos_cliente
                paso = self.dialogo.invocar(
                    self._mensaje(
                        {
                            "momento": "dialogo",
                            "necesidad": caso.necesidad,
                            "transcripcion": self._transcripcion(turnos),
                            "preguntas_restantes": restantes,
                        }
                    ),
                    PasoDialogo,
                )
                if paso.listo or not paso.pregunta.strip():
                    break
                respuesta = cliente.responder(Conversacion(turnos=tuple(turnos)), paso.pregunta)
                ahora = datetime.now(UTC)
                turnos.append(Turno(emisor=Emisor.ELICITADOR, texto=paso.pregunta, fecha=ahora))
                turnos.append(Turno(emisor=Emisor.CLIENTE, texto=respuesta or "—", fecha=ahora))
            antes_de_entregar = time.perf_counter()
            archivos = self.entrega.invocar_validado(
                self._mensaje(
                    {
                        "momento": "entrega",
                        "necesidad": caso.necesidad,
                        "transcripcion": self._transcripcion(turnos),
                        "entorno": {
                            "python": PYTHON,
                            "paquetes": list(self.paquetes),
                            "ruff": {
                                "archivo": self.estilo.archivo,
                                "contenido": self.estilo.texto,
                            },
                        },
                    }
                ),
                Entrega,
                validar_entrega,
            )
            tiempo_entrega = time.perf_counter() - antes_de_entregar
        except (ErrorRespuestaModelo, ErrorValidacionSalida) as falla:
            error = f"{type(falla).__name__}: {falla}"
        llamadas = registro.llamadas
        del_modelo = [ll for ll in llamadas if ll.nodo in (NODO_DIALOGO, NODO_ENTREGA)]
        del_cliente = [ll for ll in llamadas if ll.nodo == NODO_CLIENTE]
        conversacion = Conversacion(turnos=tuple(turnos))
        return ResultadoModeloUnico(
            caso=caso.id,
            corrida=corrida,
            despliegue=self.entrega.parametros.despliegue,
            prompt=self.entrega.prompt.identificador,
            transcripcion=self._transcripcion(turnos),
            turnos_cliente=conversacion.turnos_cliente,
            llego_al_limite=conversacion.turnos_cliente >= self.limite_turnos,
            archivos=archivos,
            error=error,
            reintentos_entrega=max(0, sum(1 for ll in del_modelo if ll.nodo == NODO_ENTREGA) - 1),
            tiempo_total_s=round(time.perf_counter() - inicio, 2),
            tiempo_cliente_s=round(sum(ll.latencia_ms for ll in del_cliente) / 1000, 2),
            tiempo_entrega_s=round(tiempo_entrega, 2),
            costo_modelo_usd=sum((ll.costo_usd for ll in del_modelo), Decimal(0)),
            costo_cliente_usd=sum((ll.costo_usd for ll in del_cliente), Decimal(0)),
            llamadas_modelo=len(del_modelo),
        )


def lo_que_sabe_el_cliente(caso: CasoElicitacion) -> str:
    """Extrae de la ficha lo que sabe el cliente y lo que queda fuera.

    Args:
        caso: Caso sintético.

    Returns:
        La ficha desde «Lo que sabes», sin la instrucción para el cliente simulado.

    Raises:
        ValueError: Si la ficha no trae esa sección.
    """
    inicio = caso.conocimiento.find(SECCION_DEL_CLIENTE)
    if inicio < 0:
        raise ValueError(f"La ficha {caso.id} no trae la sección «Lo que sabes».")
    return caso.conocimiento[inicio:].strip()


@dataclass(frozen=True)
class LlmUnPrompt:
    """Un modelo que recibe todo en un solo prompt y entrega, sin diálogo.

    Attributes:
        entrega: Invocador de la entrega.
        estilo: Configuración de estilo del código generado.
        paquetes: Requisitos del entorno aislado.
    """

    entrega: InvocadorNodo
    estilo: EstiloGenerado
    paquetes: tuple[str, ...]

    def resolver(
        self, caso: CasoElicitacion, registro: RegistroEnMemoria, corrida: str
    ) -> ResultadoModeloUnico:
        """Entrega el módulo de un caso con un solo prompt.

        Args:
            caso: Caso sintético.
            registro: Registro de las llamadas, del que sale el costo. Debe estar vacío al empezar.
            corrida: Identificador de la corrida.

        Returns:
            El resultado, con la entrega o el error que la impidió.
        """
        inicio = time.perf_counter()
        archivos: dict[str, str] = {}
        error: str | None = None
        try:
            archivos = self.entrega.invocar_validado(
                [
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "necesidad": caso.necesidad,
                                "lo_que_sabe_el_cliente": lo_que_sabe_el_cliente(caso),
                                "entorno": {
                                    "python": PYTHON,
                                    "paquetes": list(self.paquetes),
                                    "ruff": {
                                        "archivo": self.estilo.archivo,
                                        "contenido": self.estilo.texto,
                                    },
                                },
                            },
                            ensure_ascii=False,
                        ),
                    }
                ],
                Entrega,
                validar_entrega,
            )
        except (ErrorRespuestaModelo, ErrorValidacionSalida) as falla:
            error = f"{type(falla).__name__}: {falla}"
        tiempo = time.perf_counter() - inicio
        llamadas = registro.llamadas
        return ResultadoModeloUnico(
            caso=caso.id,
            corrida=corrida,
            despliegue=self.entrega.parametros.despliegue,
            prompt=self.entrega.prompt.identificador,
            transcripcion=[],
            turnos_cliente=0,
            llego_al_limite=False,
            archivos=archivos,
            error=error,
            reintentos_entrega=max(0, len(llamadas) - 1),
            tiempo_total_s=round(tiempo, 2),
            tiempo_cliente_s=0.0,
            tiempo_entrega_s=round(tiempo, 2),
            costo_modelo_usd=sum((ll.costo_usd for ll in llamadas), Decimal(0)),
            costo_cliente_usd=Decimal(0),
            llamadas_modelo=len(llamadas),
        )


def crear_llm_un_prompt(
    cliente: OpenAI,
    registro: RegistroEnMemoria,
    modelos: ConfiguracionModelos,
    razonamiento: ConfiguracionRazonamiento,
    estilo: EstiloGenerado | None = None,
    paquetes: Sequence[str] | None = None,
) -> LlmUnPrompt:
    """Arma la línea base de un solo prompt, con el despliegue y los límites de N10.

    Args:
        cliente: Cliente de la API OpenAI v1.
        registro: Destino de la traza de cada llamada.
        modelos: Despliegues de los nodos.
        razonamiento: Esfuerzo, límite de salida y tiempo de espera de los nodos.
        estilo: Configuración de estilo; si se omite, la de `config/estilo_generado/`.
        paquetes: Requisitos del entorno; si se omiten, los de la imagen del entorno aislado.

    Returns:
        La línea base lista para resolver casos.
    """
    requisitos = paquetes if paquetes is not None else list(requisitos_del_entorno().values())
    entrega = InvocadorNodo(
        cliente,
        ParametrosNodo(
            nodo=NODO_UN_PROMPT,
            despliegue=modelos.n10_generacion,
            esfuerzo=razonamiento.esfuerzo_n10_generacion,
            max_tokens_salida=razonamiento.max_tokens_n10_generacion,
            tiempo_espera_s=razonamiento.tiempo_espera_n10_generacion,
        ),
        leer_prompt(RUTA_PROMPT_UN_PROMPT),
        registro,
    )
    return LlmUnPrompt(entrega, estilo or cargar_estilo(), tuple(requisitos))


def crear_modelo_unico(
    cliente: OpenAI,
    registro: RegistroEnMemoria,
    modelos: ConfiguracionModelos,
    razonamiento: ConfiguracionRazonamiento,
    limite_turnos: int,
    estilo: EstiloGenerado | None = None,
    paquetes: Sequence[str] | None = None,
) -> ModeloUnico:
    """Arma el modelo único con la configuración del sistema, sin identificadores en el código.

    Usa el despliegue de N10, el más capaz del sistema. El diálogo lleva el esfuerzo y el límite
    de salida de N3, y la entrega, los de N10 con su tiempo de espera.

    Args:
        cliente: Cliente de la API OpenAI v1.
        registro: Destino de la traza de cada llamada.
        modelos: Despliegues de los nodos.
        razonamiento: Esfuerzo, límite de salida y tiempo de espera de los nodos.
        limite_turnos: Intervenciones del cliente, con la necesidad, en que termina el diálogo.
        estilo: Configuración de estilo; si se omite, la de `config/estilo_generado/`.
        paquetes: Requisitos del entorno; si se omiten, los de la imagen del entorno aislado.

    Returns:
        El modelo único listo para resolver casos.
    """
    prompt = leer_prompt(RUTA_PROMPT)
    despliegue = modelos.n10_generacion
    dialogo = InvocadorNodo(
        cliente,
        ParametrosNodo(
            nodo=NODO_DIALOGO,
            despliegue=despliegue,
            esfuerzo=razonamiento.esfuerzo_n3_dialogo,
            max_tokens_salida=razonamiento.max_tokens_n3_dialogo,
        ),
        prompt,
        registro,
    )
    entrega = InvocadorNodo(
        cliente,
        ParametrosNodo(
            nodo=NODO_ENTREGA,
            despliegue=despliegue,
            esfuerzo=razonamiento.esfuerzo_n10_generacion,
            max_tokens_salida=razonamiento.max_tokens_n10_generacion,
            tiempo_espera_s=razonamiento.tiempo_espera_n10_generacion,
        ),
        prompt,
        registro,
    )
    requisitos = paquetes if paquetes is not None else list(requisitos_del_entorno().values())
    return ModeloUnico(
        dialogo, entrega, estilo or cargar_estilo(), tuple(requisitos), limite_turnos
    )
