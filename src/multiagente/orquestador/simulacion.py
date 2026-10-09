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
    EjecucionPruebas,
    FragmentoContexto,
    RegistroCaptura,
    Requerimientos,
    Validacion,
    Veredicto,
    VeredictoCaso,
    VersionCodigo,
)
from multiagente.orquestador.servicios import (
    AnalisisEstatico,
    Dialogo,
    Dictamen,
    Diseno,
    Servicios,
    Sintesis,
    VerificacionCalidad,
)

PREGUNTAS = {
    "rol": "¿Qué rol cumple la persona que usará esta funcionalidad?",
    "funcionalidad": "¿Qué necesita poder hacer?",
    "beneficio": "¿Qué gana con ello?",
    "reglas_negocio": "¿Qué regla de negocio gobierna este proceso?",
    "datos_entrada": "¿Qué información necesita tener a la mano?",
    "datos_salida": "¿Qué debe entregar el sistema como resultado?",
    "excepciones": "¿Qué pasa si el dato llega incompleto o equivocado?",
    "confirmacion": "Le resumo lo que entendí; ¿es correcto?",
}
AFIRMACION = "Sí"
"""Inicio de una respuesta que confirma el resumen en la simulación."""
SIN_DATO = "No especificado"
RUTA_MODULO = "src/simulado/modulo.py"


def _fragmento(documento_id: str, titulo: str) -> FragmentoContexto:
    return FragmentoContexto(
        documento_id=documento_id,
        version_documento="1.0",
        titulo=titulo,
        contenido=f"Contenido simulado de {titulo}",
        similitud=1.0,
    )


def _asignar(registro: RegistroCaptura, respuesta: str) -> RegistroCaptura:
    """Asigna la respuesta al primer atributo pendiente, como haría el modelo al extraerla."""
    pendientes = registro.pendientes
    if not pendientes:
        return registro
    atributo = pendientes[0]
    if atributo == "confirmacion":
        if respuesta.startswith(AFIRMACION):
            return registro.model_copy(update={"resumen_confirmado": True})
        atributo = "reglas_negocio"
    if atributo in ("reglas_negocio", "excepciones"):
        return registro.model_copy(update={atributo: (*getattr(registro, atributo), respuesta)})
    if atributo == "datos_entrada":
        dato = DatoEntrada(nombre=respuesta, tipo="texto", obligatorio=True)
        return registro.model_copy(update={"datos_entrada": (dato,)})
    if atributo == "datos_salida":
        return registro.model_copy(
            update={"datos_salida": (DatoSalida(nombre=respuesta, tipo="texto"),)}
        )
    return registro.model_copy(update={atributo: respuesta})


class ErrorSimulado(RuntimeError):
    """Fallo provocado a propósito para probar la reanudación tras una caída."""


@dataclass
class ServiciosSimulados:
    """Implementa los servicios de los cuatro agentes con respuestas deterministas.

    Attributes:
        fallos_veredicto: Cuántos dictámenes iniciales marcan todos los casos como no cumplidos.
        defectos_calidad: Cuántas verificaciones de calidad iniciales reportan un defecto.
        defectos_requieren_cliente: Si esos defectos solo se resuelven con el cliente.
        errores_validacion: Cuántas validaciones iniciales de la especificación fallan.
        fallos_ejecucion: Cuántas ejecuciones iniciales lanzan `ErrorSimulado`.
        llamadas: Conteo de llamadas por método, para las pruebas.
    """

    fallos_veredicto: int = 1
    defectos_calidad: int = 0
    defectos_requieren_cliente: bool = False
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
                "elicitacion": (_fragmento("eli-006", "Guía de preguntas (simulada)"),),
                "dominio_negocio": (_fragmento("dom-001", "Glosario catastral (simulado)"),),
            }
        )

    def dialogar(self, conversacion: Conversacion, contexto: Contexto) -> Dialogo:
        """Asigna la respuesta nueva al primer atributo pendiente y pregunta el siguiente (N3).

        La necesidad inicial se toma como la funcionalidad.
        """
        self._contar("dialogar")
        registro = conversacion.registro
        respuesta = conversacion.respuesta_nueva
        if respuesta is not None and conversacion.turnos_procesados == 0:
            registro = registro.model_copy(update={"funcionalidad": respuesta})
        elif respuesta is not None:
            registro = _asignar(registro, respuesta)
        siguientes = registro.pendientes
        return Dialogo(
            registro=registro,
            siguiente_pregunta=PREGUNTAS[siguientes[0]] if siguientes else None,
        )

    def sintetizar(
        self,
        conversacion: Conversacion,
        contexto: Contexto,
        previos: Requerimientos,
        proyecto: str,
    ) -> Sintesis:
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
            version=f"0.{previos.sintesis + 1}",
            proyecto=proyecto,
            tipo_solicitud=TipoSolicitud.NUEVO,
            impacto=Impacto.MEDIO,
            modulo="simulado",
            autor="Agente elicitador (simulado)",
            area_funcional="Simulación",
            titulo=enunciado,
            descripcion=Descripcion(
                precondicion="La sesión de simulación está abierta",
                regla_negocio="; ".join(registro.reglas_negocio) or SIN_DATO,
                datos_entrada=list(registro.datos_entrada)
                or [DatoEntrada(nombre="dato", tipo="texto", obligatorio=True)],
                datos_salida=list(registro.datos_salida)
                or [DatoSalida(nombre="resultado", tipo="texto")],
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
        referencias = tuple(
            fragmento.referencia
            for fragmentos in contexto.fragmentos.values()
            for fragmento in fragmentos
        )
        return Sintesis(
            historias=(HistoriaUsuario(id="HU-01", enunciado=enunciado),),
            requerimientos=(requerimiento,),
            referencias={"RF-01": referencias},
        )

    def verificar_calidad(self, requerimientos: Requerimientos) -> VerificacionCalidad:
        """Reporta un defecto en las primeras verificaciones configuradas (N6)."""
        if self._contar("verificar_calidad") <= self.defectos_calidad:
            return VerificacionCalidad(
                defectos=("Defecto simulado: la regla de negocio es ambigua",),
                requiere_cliente=self.defectos_requieren_cliente,
            )
        return VerificacionCalidad()

    # Arquitecto ---------------------------------------------------------------------------

    def recuperar_catalogo(self, requerimientos: Requerimientos) -> Contexto:
        """Simula la recuperación del catálogo de arquitecturas (N7)."""
        self._contar("recuperar_catalogo")
        return Contexto(
            fragmentos={"arquitecturas_referencia": (_fragmento("ARQ-01", "Capas (simulada)"),)}
        )

    def disenar(
        self, requerimientos: Requerimientos, contexto: Contexto, previa: Arquitectura
    ) -> Diseno:
        """Produce una especificación válida que cubre todos los requerimientos (N8)."""
        self._contar("disenar")
        cubiertos = [r.id_requerimiento for r in requerimientos.requerimientos]
        version = previa.disenos + 1
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
        previa: VersionCodigo | None,
    ) -> VersionCodigo:
        """Genera una versión que declara los defectos que atiende (N10)."""
        self._contar("generar")
        numero = previa.numero + 1 if previa is not None else 1
        return VersionCodigo(
            numero=numero,
            archivos={RUTA_MODULO: f'"""Versión {numero} simulada."""\n'},
            defectos_atendidos=validacion.retroalimentacion,
        )

    # Tester -------------------------------------------------------------------------------

    def ejecutar(
        self, version: VersionCodigo, especificacion: EspecificacionDiseno
    ) -> EjecucionPruebas:
        """Simula la ejecución; falla con `ErrorSimulado` las primeras veces configuradas (N11)."""
        if self._contar("ejecutar") <= self.fallos_ejecucion:
            raise ErrorSimulado("Caída simulada durante la ejecución en el entorno aislado")
        return EjecucionPruebas(salida=f"Versión {version.numero}: pruebas ejecutadas (simulado)")

    def analizar(
        self,
        version: VersionCodigo,
        especificacion: EspecificacionDiseno,
        requerimientos: Requerimientos,
    ) -> AnalisisEstatico:
        """Simula un análisis estático sin hallazgos (N12)."""
        self._contar("analizar")
        return AnalisisEstatico()

    def recuperar_criterios(self, validacion: Validacion) -> Contexto:
        """Simula la recuperación de criterios de calidad (N13)."""
        self._contar("recuperar_criterios")
        return Contexto(
            fragmentos={"criterios_calidad": (_fragmento("cal-fs", "CAL-FS-001 (simulado)"),)}
        )

    def dictaminar(
        self,
        plan: tuple[CasoPrueba, ...],
        validacion: Validacion,
        contexto: Contexto,
        version: VersionCodigo,
    ) -> Dictamen:
        """Marca todos los casos como no cumplidos en los primeros dictámenes configurados (N14)."""
        cumple = self._contar("dictaminar") > self.fallos_veredicto
        veredictos = tuple(
            VeredictoCaso(id_caso=caso.id, cumple=cumple, evidencia=f"Prueba simulada de {caso.id}")
            for caso in plan
        )
        retroalimentacion = () if cumple else tuple(f"{caso.id}: no cumple" for caso in plan)
        veredicto = Veredicto.APROBADO if cumple else Veredicto.RECHAZADO
        return Dictamen(
            veredictos=veredictos,
            hallazgos=validacion.hallazgos,
            veredicto=veredicto,
            retroalimentacion=retroalimentacion,
            reporte=f"# Reporte simulado de la versión {version.numero}: {veredicto.value}",
        )


@dataclass
class ElicitadorFijo:
    """Elicitador que entrega requerimientos ya redactados, sin conversar.

    Sirve para probar a los agentes posteriores con requerimientos conocidos y sin el costo de
    una elicitación: el diálogo se da por completo y confirmado en N3, N5 devuelve la síntesis
    dada y N6 no encuentra defectos, de modo que la sesión llega a la aprobación humana.

    Attributes:
        sintesis: Historias, requerimientos y referencias que se entregan en N5.
    """

    sintesis: Sintesis

    def recuperar_contexto(self, conversacion: Conversacion) -> Contexto:
        """No recupera nada: los requerimientos ya están redactados (N2)."""
        return Contexto()

    def dialogar(self, conversacion: Conversacion, contexto: Contexto) -> Dialogo:
        """Da por capturado y confirmado el registro, a partir de la síntesis dada (N3)."""
        historia = self.sintesis.historias[0].enunciado
        primero = self.sintesis.requerimientos[0]
        registro = RegistroCaptura(
            rol=historia.como,
            funcionalidad=historia.quiero,
            beneficio=historia.para,
            reglas_negocio=tuple(r.descripcion.regla_negocio for r in self.sintesis.requerimientos),
            datos_entrada=tuple(primero.descripcion.datos_entrada),
            datos_salida=tuple(primero.descripcion.datos_salida),
            excepciones=tuple(e.entonces for e in primero.criterios_aceptacion[-1:]),
            resumen_confirmado=True,
        )
        return Dialogo(registro=registro, siguiente_pregunta=None)

    def sintetizar(
        self,
        conversacion: Conversacion,
        contexto: Contexto,
        previos: Requerimientos,
        proyecto: str,
    ) -> Sintesis:
        """Devuelve la síntesis dada (N5)."""
        return self.sintesis

    def verificar_calidad(self, requerimientos: Requerimientos) -> VerificacionCalidad:
        """No reporta defectos: los requerimientos dados se suponen verificados (N6)."""
        return VerificacionCalidad()


@dataclass
class ArquitectoFijo:
    """Arquitecto que entrega un diseño ya aprobado, sin diseñar.

    Sirve para probar al desarrollador con especificaciones conocidas y sin el costo del diseño:
    N7 no recupera nada, N8 devuelve el diseño dado y N9 no encuentra errores, de modo que la
    sesión llega a la aprobación humana de la especificación.

    Attributes:
        diseno: Registro de decisión y especificación que se entregan en N8.
    """

    diseno: Diseno

    def recuperar_catalogo(self, requerimientos: Requerimientos) -> Contexto:
        """No recupera nada: el diseño ya está hecho (N7)."""
        return Contexto()

    def disenar(
        self, requerimientos: Requerimientos, contexto: Contexto, previa: Arquitectura
    ) -> Diseno:
        """Devuelve el diseño dado (N8)."""
        return self.diseno

    def validar(
        self, especificacion: EspecificacionDiseno, requerimientos: Requerimientos
    ) -> list[str]:
        """No reporta errores: el diseño dado ya pasó las validaciones del Anexo B (N9)."""
        return []


def aprobar(revisor: str = "Revisor simulado") -> dict[str, str]:
    """Respuesta de aprobación para un punto de control."""
    return {"decision": "aprobado", "revisor": revisor}


def rechazar(observaciones: str, revisor: str = "Revisor simulado") -> dict[str, str]:
    """Respuesta de rechazo con observaciones para un punto de control."""
    return {"decision": "rechazado", "revisor": revisor, "observaciones": observaciones}


@dataclass
class Guion:
    """Necesidad inicial y respuestas que se entregan, en orden, en cada tipo de pausa.

    Attributes:
        necesidad: Necesidad con que el cliente abre la sesión.
        respuestas_cliente: Respuestas del cliente en las pausas de diálogo (N3).
        decisiones: Decisiones por punto de control: `requerimientos`, `especificacion` y
            `final`.
        proyecto: Proyecto de la sesión.
    """

    necesidad: str
    respuestas_cliente: list[str]
    decisiones: dict[str, list[dict[str, str]]]
    proyecto: str = "Proyecto simulado"

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
    id_sesion, avance = iniciar_sesion(app, cliente, guion.proyecto, guion.necesidad, id_sesion)
    return continuar(app, id_sesion, guion, avance)


def guion_completo() -> Guion:
    """Guion que ejercita ambos ciclos y los retornos de los tres puntos de control."""
    return Guion(
        necesidad="Registrar solicitudes de mutación con su documento soporte",
        respuestas_cliente=[
            "Analista de conservación catastral",
            "Tramitar el cambio del predio y hacerle seguimiento",
            "La solicitud se acepta solo si el predio existe",
            "Número predial",
            "Radicado",
            "Si el predio no existe, la solicitud se rechaza",
            "Sí, el resumen es correcto",
            # Tras el rechazo de los requerimientos, la regla que faltaba y una nueva confirmación.
            "El documento soporte no puede tener fecha posterior a la radicación",
            "Sí, el resumen es correcto",
        ],
        decisiones={
            "requerimientos": [rechazar("Falta la regla sobre la fecha del documento"), aprobar()],
            "especificacion": [rechazar("Separar la validación en su propio módulo"), aprobar()],
            "final": [rechazar("El radicado debe incluir el año"), aprobar()],
        },
    )
