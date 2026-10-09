"""Servicios simulados de los cuatro agentes y guiones para recorrer el grafo (paso 5).

Los servicios simulados producen artefactos válidos según los esquemas de los Anexos A y B, de
modo que el esqueleto ejercita el estado y las transiciones reales sin llamar a modelos de
lenguaje. Los textos de este módulo son datos de simulación, no prompts de ningún agente.
"""

from collections import Counter
from dataclasses import dataclass, field

from langgraph.graph.state import CompiledStateGraph

from multiagente.core.esquemas.comunes import Enunciado, Impacto, Prioridad
from multiagente.core.esquemas.especificacion_diseno import (
    EspecificacionDiseno,
    InterfazPublica,
    Modulo,
    TipoInterfaz,
)
from multiagente.core.esquemas.requerimiento import (
    DatoEntrada,
    DatoSalida,
    Descripcion,
    EscenarioAceptacion,
    HistoriaUsuario,
    RequerimientoFormal,
    TipoSolicitud,
)
from multiagente.orquestador.ejecucion import Avance, RespuestaPausa, avanzar, iniciar_sesion
from multiagente.orquestador.estado import (
    Arquitectura,
    CasoPrueba,
    Contexto,
    Conversacion,
    Emisor,
    Requerimientos,
    Validacion,
    VeredictoCaso,
    VersionCodigo,
)
from multiagente.orquestador.servicios import Dialogo, Dictamen, Diseno, Servicios, Sintesis

PREGUNTAS = {
    "rol": "¿Qué rol cumple la persona que usará esta funcionalidad?",
    "funcionalidad": "¿Qué necesita poder hacer?",
    "beneficio": "¿Para qué le sirve? ¿Qué gana con ello?",
    "reglas_negocio": "¿Qué regla de negocio gobierna este proceso?",
}
SIN_DATO = "No especificado"
RUTA_MODULO = "src/simulado/modulo.py"


class ErrorSimulado(RuntimeError):
    """Fallo provocado a propósito para probar la reanudación tras una caída."""


@dataclass
class ServiciosSimulados:
    """Implementa los servicios de los cuatro agentes con respuestas deterministas.

    Attributes:
        fallos_veredicto: Cuántos dictámenes iniciales marcan todos los casos como no cumplidos.
        defectos_calidad: Cuántas verificaciones de calidad iniciales reportan un defecto.
        errores_validacion: Cuántas validaciones iniciales de la especificación fallan.
        fallos_ejecucion: Cuántas ejecuciones iniciales lanzan `ErrorSimulado`.
        llamadas: Conteo de llamadas por método, para las pruebas.
    """

    fallos_veredicto: int = 1
    defectos_calidad: int = 0
    errores_validacion: int = 0
    fallos_ejecucion: int = 0
    llamadas: Counter[str] = field(default_factory=Counter)

    def como_servicios(self) -> Servicios:
        """Entrega esta simulación como servicios de los cuatro agentes.

        Returns:
            Servicios en los que los cuatro agentes son esta misma simulación.
        """
        return Servicios(elicitador=self, arquitecto=self, desarrollador=self, tester=self)

    def _contar(self, metodo: str) -> int:
        self.llamadas[metodo] += 1
        return self.llamadas[metodo]

    # Elicitador ---------------------------------------------------------------------------

    def recuperar_contexto(self, conversacion: Conversacion) -> Contexto:
        """Simula la recuperación de las colecciones de elicitación y dominio (N2)."""
        self._contar("recuperar_contexto")
        return Contexto(
            fragmentos={
                "elicitacion": ("Plantilla de historia de usuario (simulada)",),
                "dominio_negocio": ("Glosario catastral (simulado)",),
            }
        )

    def dialogar(self, conversacion: Conversacion, contexto: Contexto) -> Dialogo:
        """Asigna la respuesta al primer atributo pendiente y pregunta por el siguiente (N3)."""
        self._contar("dialogar")
        respuesta = next(
            turno.texto for turno in reversed(conversacion.turnos) if turno.emisor is Emisor.CLIENTE
        )
        registro = conversacion.registro
        pendientes = registro.pendientes
        atributo = pendientes[0] if pendientes else "reglas_negocio"
        if atributo == "reglas_negocio":
            registro = registro.model_copy(
                update={"reglas_negocio": (*registro.reglas_negocio, respuesta)}
            )
        else:
            registro = registro.model_copy(update={atributo: respuesta})
        siguientes = registro.pendientes
        return Dialogo(
            registro=registro,
            siguiente_pregunta=PREGUNTAS[siguientes[0]] if siguientes else None,
        )

    def sintetizar(self, conversacion: Conversacion, contexto: Contexto) -> Sintesis:
        """Construye una historia y un requerimiento formal válidos (N5)."""
        self._contar("sintetizar")
        registro = conversacion.registro
        enunciado = Enunciado(
            como=registro.rol or SIN_DATO,
            quiero=registro.funcionalidad or SIN_DATO,
            para=registro.beneficio or SIN_DATO,
        )
        requerimiento = RequerimientoFormal(
            id_requerimiento="RF-01",
            version="0.1",
            proyecto="Simulación del esqueleto",
            tipo_solicitud=TipoSolicitud.NUEVO,
            impacto=Impacto.MEDIO,
            modulo="simulado",
            autor="Agente elicitador (simulado)",
            area_funcional="Simulación",
            titulo=enunciado,
            descripcion=Descripcion(
                precondicion="La sesión de simulación está abierta",
                regla_negocio="; ".join(registro.reglas_negocio) or SIN_DATO,
                datos_entrada=[DatoEntrada(nombre="dato", tipo="texto", obligatorio=True)],
                datos_salida=[DatoSalida(nombre="resultado", tipo="texto")],
            ),
            criterios_aceptacion=[
                EscenarioAceptacion(
                    id="ESC-01",
                    nombre="Camino principal",
                    dado_que="un dato válido",
                    cuando="se ejecuta la funcionalidad",
                    entonces="se obtiene el resultado",
                ),
                EscenarioAceptacion(
                    id="ESC-02",
                    nombre="Dato inválido",
                    dado_que="un dato vacío",
                    cuando="se ejecuta la funcionalidad",
                    entonces="el sistema rechaza la solicitud",
                ),
            ],
            prioridad=Prioridad.MEDIA,
        )
        return Sintesis(
            historias=(HistoriaUsuario(id="HU-01", enunciado=enunciado),),
            requerimientos=(requerimiento,),
        )

    def verificar_calidad(self, requerimientos: Requerimientos) -> list[str]:
        """Reporta un defecto en las primeras verificaciones configuradas (N6)."""
        if self._contar("verificar_calidad") <= self.defectos_calidad:
            return ["Defecto simulado: la regla de negocio es ambigua"]
        return []

    # Arquitecto ---------------------------------------------------------------------------

    def recuperar_catalogo(self, requerimientos: Requerimientos) -> Contexto:
        """Simula la recuperación del catálogo de arquitecturas (N7)."""
        self._contar("recuperar_catalogo")
        return Contexto(fragmentos={"arquitecturas_referencia": ("ARQ-01 (simulado)",)})

    def disenar(
        self, requerimientos: Requerimientos, contexto: Contexto, previa: Arquitectura
    ) -> Diseno:
        """Produce una especificación válida que cubre todos los requerimientos (N8)."""
        self._contar("disenar")
        cubiertos = [r.id_requerimiento for r in requerimientos.requerimientos]
        version = len(previa.observaciones_revisor) + 1
        especificacion = EspecificacionDiseno(
            id_especificacion="ED-01",
            version=f"0.{version}",
            arquitectura_base="ARQ-01",
            requerimientos_cubiertos=cubiertos,
            modulos=[
                Modulo(
                    nombre="simulado.modulo",
                    ruta=RUTA_MODULO,
                    responsabilidad="Funcionalidad simulada",
                    capa="dominio",
                    interfaces_publicas=[
                        InterfazPublica(
                            nombre="ejecutar",
                            tipo=TipoInterfaz.FUNCION,
                            firma="ejecutar(dato: str) -> str",
                            descripcion="Ejecuta la funcionalidad simulada",
                        )
                    ],
                    requerimientos=cubiertos,
                )
            ],
            modelo_datos=[],
            dependencias_externas=[],
            reglas_de_dependencia=["La capa de dominio no importa de ninguna otra capa"],
        )
        return Diseno(
            registro_decision=f"# Registro de decisión simulado, versión 0.{version}",
            especificacion=especificacion,
        )

    def validar(
        self, especificacion: EspecificacionDiseno, requerimientos: Requerimientos
    ) -> list[str]:
        """Reporta un error en las primeras validaciones configuradas (N9)."""
        if self._contar("validar") <= self.errores_validacion:
            return ["Error simulado: un requerimiento aprobado no tiene módulo asignado"]
        return []

    # Desarrollador ------------------------------------------------------------------------

    def generar(
        self,
        requerimientos: Requerimientos,
        especificacion: EspecificacionDiseno,
        validacion: Validacion,
        numero: int,
    ) -> VersionCodigo:
        """Genera una versión que declara los defectos que atiende (N10)."""
        self._contar("generar")
        return VersionCodigo(
            numero=numero,
            archivos={RUTA_MODULO: f'"""Versión {numero} simulada."""\n'},
            defectos_atendidos=validacion.retroalimentacion,
        )

    # Tester -------------------------------------------------------------------------------

    def ejecutar(self, version: VersionCodigo) -> str:
        """Simula la ejecución; falla con `ErrorSimulado` las primeras veces configuradas (N11)."""
        if self._contar("ejecutar") <= self.fallos_ejecucion:
            raise ErrorSimulado("Caída simulada durante la ejecución en el entorno aislado")
        return f"Versión {version.numero}: pruebas ejecutadas (simulado)"

    def analizar(self, version: VersionCodigo, especificacion: EspecificacionDiseno) -> list[str]:
        """Simula un análisis estático sin hallazgos (N12)."""
        self._contar("analizar")
        return []

    def recuperar_criterios(self, version: VersionCodigo) -> Contexto:
        """Simula la recuperación de criterios de calidad (N13)."""
        self._contar("recuperar_criterios")
        return Contexto(fragmentos={"criterios_calidad": ("CAL-AF-001 (simulado)",)})

    def dictaminar(
        self, plan: tuple[CasoPrueba, ...], validacion: Validacion, contexto: Contexto
    ) -> Dictamen:
        """Marca todos los casos como no cumplidos en los primeros dictámenes configurados (N14)."""
        cumple = self._contar("dictaminar") > self.fallos_veredicto
        veredictos = tuple(
            VeredictoCaso(id_caso=caso.id, cumple=cumple, evidencia=f"Prueba simulada de {caso.id}")
            for caso in plan
        )
        retroalimentacion = () if cumple else tuple(f"{caso.id}: no cumple" for caso in plan)
        return Dictamen(veredictos=veredictos, retroalimentacion=retroalimentacion)


def aprobar(revisor: str = "Revisor simulado") -> dict[str, str]:
    """Respuesta de aprobación para un punto de control."""
    return {"decision": "aprobado", "revisor": revisor}


def rechazar(observaciones: str, revisor: str = "Revisor simulado") -> dict[str, str]:
    """Respuesta de rechazo con observaciones para un punto de control."""
    return {"decision": "rechazado", "revisor": revisor, "observaciones": observaciones}


@dataclass
class Guion:
    """Respuestas que se entregan, en orden, en cada tipo de pausa.

    Attributes:
        respuestas_cliente: Respuestas del cliente en las pausas de diálogo (N3).
        decisiones: Decisiones por punto de control: `requerimientos`, `especificacion` y
            `final`.
    """

    respuestas_cliente: list[str]
    decisiones: dict[str, list[dict[str, str]]]

    def responder(self, punto: str) -> RespuestaPausa:
        """Toma la siguiente respuesta del guion para la pausa indicada.

        Args:
            punto: Punto de la pausa pendiente.

        Returns:
            La respuesta del cliente o la decisión humana correspondiente.
        """
        if punto == "dialogo":
            return self.respuestas_cliente.pop(0)
        return self.decisiones[punto].pop(0)


@dataclass
class Recorrido:
    """Historia de una sesión ejecutada con un guion."""

    id_sesion: str
    avances: list[Avance]

    @property
    def nodos(self) -> list[str]:
        """Nodos ejecutados, en orden y con repeticiones."""
        return [nodo for avance in self.avances for nodo in avance.nodos]

    @property
    def final(self) -> Avance:
        """Último avance de la sesión."""
        return self.avances[-1]


def continuar(app: CompiledStateGraph, id_sesion: str, guion: Guion, avance: Avance) -> Recorrido:
    """Responde con el guion cada pausa hasta que la sesión termina.

    Args:
        app: Grafo compilado con checkpointer.
        id_sesion: Identificador de la sesión.
        guion: Respuestas a entregar.
        avance: Avance desde el que se continúa.

    Returns:
        El recorrido desde ese avance hasta el final.
    """
    avances = [avance]
    while avance.pausa is not None:
        avance = avanzar(app, id_sesion, guion.responder(avance.pausa.punto))
        avances.append(avance)
    return Recorrido(id_sesion=id_sesion, avances=avances)


def recorrer(
    app: CompiledStateGraph,
    guion: Guion,
    cliente: str = "Cliente simulado",
    id_sesion: str | None = None,
) -> Recorrido:
    """Abre una sesión y la recorre completa respondiendo con el guion.

    Args:
        app: Grafo compilado con checkpointer.
        guion: Respuestas a entregar.
        cliente: Nombre del cliente de la sesión.
        id_sesion: Identificador a usar; si se omite, se genera uno.

    Returns:
        El recorrido completo de la sesión.
    """
    id_sesion, avance = iniciar_sesion(app, cliente, id_sesion)
    return continuar(app, id_sesion, guion, avance)


def guion_completo() -> Guion:
    """Guion que ejercita ambos ciclos y los retornos de los tres puntos de control."""
    return Guion(
        respuestas_cliente=[
            "Analista de conservación catastral",
            "Registrar solicitudes de mutación con su documento soporte",
            "Tramitar el cambio del predio y hacerle seguimiento",
            "La solicitud se acepta solo si el predio existe",
            "El documento soporte no puede tener fecha posterior a la radicación",
        ],
        decisiones={
            "requerimientos": [rechazar("Falta la regla sobre la fecha del documento"), aprobar()],
            "especificacion": [rechazar("Separar la validación en su propio módulo"), aprobar()],
            "final": [rechazar("El radicado debe incluir el año"), aprobar()],
        },
    )
