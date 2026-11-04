"""Grafo de 17 nodos con sus ciclos, retornos y tres puntos de control humano.

Las aristas, los enrutadores y los nodos determinísticos son la implementación real del
orquestador. El trabajo de modelos de lenguaje, recuperación y ejecución llega por los
servicios inyectados (`multiagente.orquestador.servicios`).
"""

import logging
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import ValidationError

from multiagente.core.configuracion import ConfiguracionOrquestador
from multiagente.llm.cliente import ErrorRespuestaModelo
from multiagente.llm.invocador import ErrorValidacionSalida
from multiagente.orquestador.estado import (
    AprobacionHumana,
    Arquitectura,
    CasoPrueba,
    Codigo,
    Contexto,
    Control,
    Conversacion,
    Decision,
    Destino,
    Emisor,
    EntradaSesion,
    EstadoGrafo,
    Fase,
    PuntoControl,
    Requerimientos,
    RespuestaHumana,
    Sesion,
    Turno,
    Validacion,
    Veredicto,
)
from multiagente.orquestador.servicios import Servicios, VerificacionCalidad

_log = logging.getLogger(__name__)

PREGUNTA_REINTENTO = (
    "No pude procesar su respuesta en este momento. ¿Puede repetirla o decirla de otra forma?"
)
"""Pregunta de N3 cuando falla el procesamiento de una respuesta del cliente."""


FALLAS_DEL_MODELO = (ErrorRespuestaModelo, ErrorValidacionSalida)
"""Fallas en que el modelo respondió sin una salida utilizable, tras el reintento del nodo.

Son las de un contenido filtrado, rechazado, truncado o inválido: reanudar puede repetirlas, así
que N5, N8 y N10 las convierten en una decisión del flujo. Las de transporte (red, tiempo de
espera) se propagan: la sesión queda detenida y reanudarla las resuelve.
"""


def _problemas(error: Exception) -> tuple[str, ...]:
    """Problemas de una falla del modelo, para mostrarlos o entregarlos como retroalimentación."""
    return tuple(getattr(error, "problemas", None) or (str(error),))


class Nodo(StrEnum):
    """Identificadores de los nodos del grafo (arquitectura, Tabla 1)."""

    N1 = "n1_apertura"
    N2 = "n2_contexto_elicitacion"
    N3 = "n3_dialogo"
    N4 = "n4_suficiencia"
    N5 = "n5_sintesis"
    N6 = "n6_aprobacion_requerimientos"
    N7 = "n7_catalogo_arquitecturas"
    N8 = "n8_diseno"
    N9 = "n9_aprobacion_especificacion"
    N10 = "n10_generacion"
    N11 = "n11_ejecucion"
    N12 = "n12_analisis_estatico"
    N13 = "n13_criterios_calidad"
    N14 = "n14_veredicto"
    N15 = "n15_decision"
    N16 = "n16_plan_pruebas"
    N17 = "n17_aprobacion_final"


def _ahora() -> datetime:
    return datetime.now(UTC)


def _motivo(error: ValidationError) -> str:
    """Mensaje legible de una respuesta humana inválida."""
    return "; ".join(
        str(detalle["msg"]).removeprefix("Value error, ") for detalle in error.errors()
    )


def _pedir_decision(
    punto: PuntoControl,
    datos: dict[str, Any],
    bloqueo: str | None = None,
) -> AprobacionHumana:
    """Pausa hasta recibir una decisión humana válida y la registra con su momento.

    Una respuesta inválida (un rechazo sin observaciones, o una aprobación bloqueada) no hace
    fallar el nodo: LangGraph conservaría esa respuesta y la repetiría en cada reanudación,
    dejando la sesión detenida para siempre. En su lugar, se vuelve a pausar con un aviso; al
    reanudar, LangGraph entrega las respuestas en orden y el nodo llega a la válida.

    Args:
        punto: Punto de control.
        datos: Lo que la persona revisa en la pausa.
        bloqueo: Si se indica, la aprobación no se admite y este es el motivo. Va también en los
            datos de la pausa, para que las interfaces no ofrezcan aprobar.

    Returns:
        La decisión válida, registrada con el punto y la fecha.
    """
    aviso: str | None = None
    while True:
        respuesta = interrupt({**datos, "punto": punto.value, "aviso": aviso, "bloqueo": bloqueo})
        try:
            validada = RespuestaHumana.model_validate(respuesta)
        except ValidationError as error:
            aviso = f"Respuesta inválida: {_motivo(error)}"
            continue
        if bloqueo is not None and validada.decision is Decision.APROBADO:
            aviso = bloqueo
            continue
        if validada.pruebas_propias is not None and punto is not PuntoControl.FINAL:
            aviso = "Las pruebas propias solo se registran en la aprobación final del módulo."
            continue
        if validada.destino is not None and punto is not PuntoControl.FINAL:
            aviso = "El destino de un rechazo solo se elige en la aprobación final del módulo."
            continue
        return AprobacionHumana(**validada.model_dump(), punto=punto, fecha=_ahora())


def _volver_a_preguntar(conversacion: Conversacion) -> Conversacion:
    """Pide al cliente que repita su respuesta, que queda en el historial como ya procesada."""
    turnos = (
        *conversacion.turnos,
        Turno(emisor=Emisor.ELICITADOR, texto=PREGUNTA_REINTENTO, fecha=_ahora()),
    )
    return conversacion.model_copy(
        update={
            "turnos": turnos,
            "turnos_procesados": len(turnos),
            "pregunta_pendiente": PREGUNTA_REINTENTO,
        }
    )


def _con_aprobacion(sesion: Sesion, aprobacion: AprobacionHumana, fase: Fase | None) -> Sesion:
    actualizacion: dict[str, Any] = {"aprobaciones": (*sesion.aprobaciones, aprobacion)}
    if fase is not None:
        actualizacion["fase"] = fase
    return sesion.model_copy(update=actualizacion)


def ruta_tras_suficiencia(estado: EstadoGrafo) -> Nodo:
    """Decide si la elicitación continúa (N3) o se cierra (N5).

    Args:
        estado: Estado tras N4.

    Returns:
        N5 si no queda nada por preguntar, incluida la confirmación del resumen, o se alcanzó el
        límite de turnos; si no, N3. Lo que el cliente no supo responder no retiene el diálogo.
    """
    conversacion = estado["conversacion"]
    agotado = conversacion.turnos_cliente >= estado["control"].limite_turnos
    return Nodo.N5 if not conversacion.registro.por_preguntar or agotado else Nodo.N3


def ruta_tras_requerimientos(estado: EstadoGrafo) -> Nodo | list[Nodo]:
    """Enruta después de N6.

    Args:
        estado: Estado tras N6.

    Returns:
        N5 si hay defectos de calidad por corregir (RF-07); N3 si la persona rechazó; N7 y N16
        en paralelo si aprobó.
    """
    if estado["requerimientos"].defectos:
        return Nodo.N5
    aprobacion = estado["sesion"].ultima_aprobacion(PuntoControl.REQUERIMIENTOS)
    if aprobacion is None or aprobacion.decision is Decision.RECHAZADO:
        return Nodo.N3
    return [Nodo.N7, Nodo.N16]


def ruta_tras_especificacion(estado: EstadoGrafo) -> Nodo:
    """Enruta después de N9.

    Args:
        estado: Estado tras N9.

    Returns:
        N8 si la especificación tiene errores o la persona la rechazó; si no, N10.
    """
    if estado["arquitectura"].errores_validacion:
        return Nodo.N8
    aprobacion = estado["sesion"].ultima_aprobacion(PuntoControl.ESPECIFICACION)
    if aprobacion is None or aprobacion.decision is Decision.RECHAZADO:
        return Nodo.N8
    return Nodo.N10


def ruta_tras_generacion(estado: EstadoGrafo) -> Nodo:
    """Enruta después de N10.

    Args:
        estado: Estado tras N10.

    Returns:
        N15 si la generación falló, para contar la iteración sin ejecutar nada; si no, N11.
    """
    return Nodo.N15 if estado["codigo"].fallo_generacion else Nodo.N11


def ruta_tras_decision(estado: EstadoGrafo) -> str:
    """Enruta después de N15 (RF-27).

    Args:
        estado: Estado tras N15.

    Returns:
        N17 si todos los casos cumplen o si se agotaron las iteraciones del ciclo, para que una
        persona decida cómo seguir (escalamiento); si no, N10.
    """
    fase = estado["sesion"].fase
    if fase in (Fase.APROBACION_FINAL, Fase.REQUIERE_INTERVENCION):
        return Nodo.N17
    return Nodo.N10


def ruta_tras_aprobacion_final(estado: EstadoGrafo) -> str:
    """Enruta después de N17.

    Args:
        estado: Estado tras N17.

    Returns:
        FIN si la persona aprobó el módulo o cerró la sesión; N8 si lo devolvió al arquitecto;
        si no, N10.
    """
    fase = estado["sesion"].fase
    if fase in (Fase.VALIDADO, Fase.CERRADA):
        return END
    if fase is Fase.DISENO:
        return Nodo.N8
    return Nodo.N10


class NodosGrafo:
    """Implementación de los 17 nodos sobre los servicios de los agentes."""

    def __init__(self, servicios: Servicios, configuracion: ConfiguracionOrquestador) -> None:
        """Guarda los servicios y los límites de la configuración.

        Args:
            servicios: Trabajo de los cuatro agentes.
            configuracion: Límites de iteraciones y de turnos.
        """
        self.servicios = servicios
        self.configuracion = configuracion

    def n1_apertura(self, estado: EstadoGrafo, config: RunnableConfig) -> dict[str, Any]:
        """Abre la sesión: identificador, necesidad del cliente y límites configurados.

        La necesidad queda como primer turno del cliente, para que N2 recupere con ella el
        contexto de dominio (RF-01, RF-04).
        """
        momento = _ahora()
        return {
            "sesion": Sesion(
                id_sesion=config["configurable"]["thread_id"],
                cliente=estado["cliente"],
                proyecto=estado["proyecto"],
                fase=Fase.ELICITACION,
                creada=momento,
            ),
            "conversacion": Conversacion(
                turnos=(Turno(emisor=Emisor.CLIENTE, texto=estado["necesidad"], fecha=momento),)
            ),
            "requerimientos": Requerimientos(),
            "arquitectura": Arquitectura(),
            "codigo": Codigo(),
            "validacion": Validacion(),
            "contexto": Contexto(),
            "control": Control(
                limite_iteraciones=self.configuracion.max_iteraciones_correccion,
                limite_turnos=self.configuracion.max_turnos_elicitacion,
                limite_correcciones=self.configuracion.max_correcciones_calidad,
                limite_correcciones_diseno=self.configuracion.max_correcciones_diseno,
            ),
        }

    def n2_contexto_elicitacion(self, estado: EstadoGrafo) -> dict[str, Any]:
        """Recupera el contexto de elicitación y de dominio de negocio."""
        recuperado = self.servicios.elicitador.recuperar_contexto(estado["conversacion"])
        return {"contexto": estado["contexto"].combinar(recuperado)}

    def n3_dialogo(self, estado: EstadoGrafo) -> dict[str, Any]:
        """Espera la respuesta a la pregunta pendiente, la procesa y formula la siguiente.

        Sin pregunta pendiente (al abrir la sesión o tras un rechazo en N6) no espera: procesa
        la necesidad inicial o las observaciones del revisor y formula la primera pregunta. La
        espera va al inicio: al reanudar, LangGraph repite el nodo desde el principio, y así el
        trabajo del modelo de lenguaje se ejecuta una sola vez por respuesta.

        Si procesar una respuesta falla, el nodo no falla: al reanudarlo, LangGraph repetiría la
        misma respuesta y descartaría cualquier otra, de modo que una falla persistente, como el
        filtro de contenido, dejaría la sesión atascada. En su lugar, pide al cliente que repita
        o reformule su respuesta.
        """
        conversacion = estado["conversacion"]
        if conversacion.pregunta_pendiente is not None:
            datos = {
                "punto": "dialogo",
                "pregunta": conversacion.pregunta_pendiente,
                "observaciones_revisor": list(conversacion.observaciones_revisor),
                "turno": conversacion.turnos_cliente + 1,
                "aviso": None,
            }
            # Una respuesta vacía vuelve a pausar con un aviso, en lugar de hacer fallar el nodo.
            while not (respuesta := str(interrupt(datos)).strip()):
                datos = {**datos, "aviso": "La respuesta no puede estar vacía."}
            turno = Turno(emisor=Emisor.CLIENTE, texto=respuesta, fecha=_ahora())
            conversacion = conversacion.model_copy(update={"turnos": (*conversacion.turnos, turno)})
            try:
                dialogo = self.servicios.elicitador.dialogar(conversacion, estado["contexto"])
            except Exception:
                _log.exception("N3 no pudo procesar la respuesta del cliente; vuelve a preguntar")
                return {"conversacion": _volver_a_preguntar(conversacion)}
        else:
            dialogo = self.servicios.elicitador.dialogar(conversacion, estado["contexto"])
        turnos = conversacion.turnos
        if dialogo.siguiente_pregunta is not None:
            pregunta = Turno(
                emisor=Emisor.ELICITADOR, texto=dialogo.siguiente_pregunta, fecha=_ahora()
            )
            turnos = (*turnos, pregunta)
        return {
            "conversacion": conversacion.model_copy(
                update={
                    "turnos": turnos,
                    "turnos_procesados": len(turnos),
                    "registro": dialogo.registro,
                    "pregunta_pendiente": dialogo.siguiente_pregunta,
                }
            )
        }

    def n4_suficiencia(self, estado: EstadoGrafo) -> dict[str, Any]:
        """Control de suficiencia: la decisión la toma `ruta_tras_suficiencia`."""
        return {}

    def n5_sintesis(self, estado: EstadoGrafo) -> dict[str, Any]:
        """Sintetiza historias y requerimientos formales, corrigiendo los defectos previos.

        Si el modelo no da una síntesis válida, conserva los requerimientos previos y deja el
        motivo en `fallo_sintesis`, que N6 trata como un defecto.
        """
        previos = estado["requerimientos"]
        try:
            sintesis = self.servicios.elicitador.sintetizar(
                estado["conversacion"], estado["contexto"], previos, estado["sesion"].proyecto
            )
        except FALLAS_DEL_MODELO as error:
            # Sin síntesis válida, N6 lo trata como un defecto: la corrige o escala a la persona.
            _log.warning("N5 no obtuvo una síntesis válida: %s", error)
            return {
                "requerimientos": previos.model_copy(
                    update={
                        "fallo_sintesis": "; ".join(_problemas(error)),
                        "sintesis": previos.sintesis + 1,
                    }
                )
            }
        return {
            "requerimientos": Requerimientos(
                historias=sintesis.historias,
                requerimientos=sintesis.requerimientos,
                referencias=sintesis.referencias,
                sintesis=previos.sintesis + 1,
                correcciones=previos.correcciones,
            )
        }

    def n6_aprobacion_requerimientos(self, estado: EstadoGrafo) -> dict[str, Any]:
        """Verifica la calidad (RF-07) y somete los requerimientos a aprobación humana.

        Con defectos que N5 puede corregir, los devuelve a N5 sin intervención humana hasta
        agotar el límite de correcciones. Al agotarlo, o si algún defecto requiere información
        del cliente, escala a la persona con los defectos a la vista. Un rechazo devuelve el
        flujo al diálogo con las observaciones y exige confirmar un nuevo resumen.
        """
        requerimientos = estado["requerimientos"]
        if requerimientos.requerimientos:
            verificacion = self.servicios.elicitador.verificar_calidad(requerimientos)
        else:
            verificacion = VerificacionCalidad(defectos=("No hay requerimientos sintetizados.",))
        defectos = verificacion.defectos
        if requerimientos.fallo_sintesis:
            defectos = (f"La síntesis falló: {requerimientos.fallo_sintesis}", *defectos)
        corregible = not verificacion.requiere_cliente
        if (
            defectos
            and corregible
            and requerimientos.correcciones < estado["control"].limite_correcciones
        ):
            return {
                "requerimientos": requerimientos.model_copy(
                    update={"defectos": defectos, "correcciones": requerimientos.correcciones + 1}
                )
            }
        aprobacion = _pedir_decision(
            PuntoControl.REQUERIMIENTOS,
            {
                "historias": [h.model_dump(mode="json") for h in requerimientos.historias],
                "requerimientos": [
                    r.model_dump(mode="json") for r in requerimientos.requerimientos
                ],
                "referencias": {
                    id_requerimiento: list(referencias)
                    for id_requerimiento, referencias in requerimientos.referencias.items()
                },
                "defectos": list(defectos),
            },
            bloqueo=(
                None
                if requerimientos.requerimientos
                else "No hay requerimientos que aprobar: recházelos con observaciones para volver "
                "al diálogo, o cierre la sesión."
            ),
        )
        sesion = estado["sesion"]
        aprobado = aprobacion.decision is Decision.APROBADO
        cambios: dict[str, Any] = {
            "sesion": _con_aprobacion(sesion, aprobacion, Fase.DISENO if aprobado else None),
            "requerimientos": requerimientos.model_copy(
                update={"defectos": (), "correcciones": 0, "defectos_escalados": defectos}
            ),
        }
        if not aprobado:
            conversacion = estado["conversacion"]
            cambios["conversacion"] = conversacion.model_copy(
                update={
                    "observaciones_revisor": (
                        *conversacion.observaciones_revisor,
                        aprobacion.observaciones,
                    ),
                    "pregunta_pendiente": None,
                    "registro": conversacion.registro.model_copy(
                        update={"resumen_confirmado": False}
                    ),
                }
            )
        return cambios

    def n7_catalogo_arquitecturas(self, estado: EstadoGrafo) -> dict[str, Any]:
        """Recupera las arquitecturas de referencia aplicables."""
        recuperado = self.servicios.arquitecto.recuperar_catalogo(estado["requerimientos"])
        return {"contexto": estado["contexto"].combinar(recuperado)}

    def n8_diseno(self, estado: EstadoGrafo) -> dict[str, Any]:
        """Selecciona y parametriza la arquitectura: registro de decisión y especificación.

        Si el modelo no da un diseño válido, conserva el previo y deja el motivo en
        `fallo_diseno`, que N9 trata como un error de validación.
        """
        previa = estado["arquitectura"]
        try:
            diseno = self.servicios.arquitecto.disenar(
                estado["requerimientos"], estado["contexto"], previa
            )
        except FALLAS_DEL_MODELO as error:
            # Sin diseño válido, N9 lo trata como un error: lo corrige o escala a la persona. La
            # observación pendiente sigue sin atender, para que el próximo diseño la considere.
            _log.warning("N8 no obtuvo un diseño válido: %s", error)
            return {
                "arquitectura": previa.model_copy(
                    update={
                        "fallo_diseno": "; ".join(_problemas(error)),
                        "disenos": previa.disenos + 1,
                    }
                )
            }
        return {
            "arquitectura": previa.model_copy(
                update={
                    "registro_decision": diseno.registro_decision,
                    "especificacion": diseno.especificacion,
                    "errores_validacion": (),
                    "disenos": previa.disenos + 1,
                    "observaciones_atendidas": len(previa.observaciones_revisor),
                    "fallo_diseno": None,
                    "capacidades_no_cubiertas": diseno.capacidades_no_cubiertas,
                }
            )
        }

    def n9_aprobacion_especificacion(self, estado: EstadoGrafo) -> dict[str, Any]:
        """Valida la especificación (Anexo B) y la somete a aprobación humana.

        Con errores, la devuelve a N8 sin intervención humana hasta agotar el límite de
        correcciones. Al agotarlo, pausa con los errores a la vista, pero la persona solo puede
        rechazar con observaciones: el Anexo B exige las tres validaciones antes de habilitar la
        generación de código.
        """
        arquitectura = estado["arquitectura"]
        errores: tuple[str, ...] = ()
        if arquitectura.fallo_diseno:
            errores = (f"El diseño falló: {arquitectura.fallo_diseno}",)
        if arquitectura.especificacion is None:
            errores = errores or ("No hay especificación de diseño.",)
        else:
            errores += tuple(
                self.servicios.arquitecto.validar(
                    arquitectura.especificacion, estado["requerimientos"]
                )
            )
        limite = estado["control"].limite_correcciones_diseno
        if errores and arquitectura.correcciones < limite:
            return {
                "arquitectura": arquitectura.model_copy(
                    update={
                        "errores_validacion": errores,
                        "correcciones": arquitectura.correcciones + 1,
                    }
                )
            }
        aprobacion = _pedir_decision(
            PuntoControl.ESPECIFICACION,
            {
                "registro_decision": arquitectura.registro_decision,
                "especificacion": (
                    arquitectura.especificacion.model_dump(mode="json")
                    if arquitectura.especificacion
                    else None
                ),
                "errores": list(errores),
                "capacidades_no_cubiertas": list(arquitectura.capacidades_no_cubiertas),
            },
            bloqueo=(
                "La especificación no pasa las validaciones del Anexo B y no puede aprobarse: "
                "recházela con observaciones para que el arquitecto la corrija, o cierre la sesión."
                if errores
                else None
            ),
        )
        sesion = estado["sesion"]
        aprobado = aprobacion.decision is Decision.APROBADO
        actualizacion: dict[str, Any] = {"correcciones": 0, "errores_validacion": errores}
        if not aprobado:
            actualizacion["observaciones_revisor"] = (
                *arquitectura.observaciones_revisor,
                aprobacion.observaciones,
            )
        return {
            "sesion": _con_aprobacion(sesion, aprobacion, Fase.DESARROLLO if aprobado else None),
            "arquitectura": arquitectura.model_copy(update=actualizacion),
        }

    def n10_generacion(self, estado: EstadoGrafo) -> dict[str, Any]:
        """Genera una nueva versión del módulo sin recuperación de contexto.

        Recibe la versión vigente, si la hay, para corregirla en lugar de reescribirla (RF-19);
        tras un rediseño, la especificación cambió y el módulo se genera de cero. Si el modelo no
        da una versión válida, deja el motivo en `fallo_generacion` y una validación rechazada con
        los problemas: el flujo salta a N15, que cuenta la iteración.
        """
        codigo = estado["codigo"]
        validacion = estado["validacion"]
        especificacion = estado["arquitectura"].especificacion
        clave = f"{especificacion.id_especificacion} v{especificacion.version}"
        previa = codigo.vigente
        if previa is not None and previa.especificacion not in (None, clave):
            previa = None
        try:
            version = self.servicios.desarrollador.generar(
                estado["requerimientos"], especificacion, validacion, previa
            )
        except FALLAS_DEL_MODELO as error:
            # Sin versión válida, la iteración cuenta como fallida: N15 la registra y decide.
            _log.warning("N10 no obtuvo una versión válida: %s", error)
            problemas = _problemas(error)
            reporte = "\n".join(
                [
                    "# La generación del módulo falló",
                    "",
                    "El desarrollador no produjo una versión válida en sus dos intentos:",
                    "",
                    *(f"- {problema}" for problema in problemas),
                ]
            )
            return {
                "codigo": codigo.model_copy(update={"fallo_generacion": "; ".join(problemas)}),
                "validacion": Validacion(
                    plan_pruebas=validacion.plan_pruebas,
                    veredicto=Veredicto.RECHAZADO,
                    retroalimentacion=tuple(f"[generación] {p}" for p in problemas),
                    reporte=reporte + "\n",
                ),
            }
        version = version.model_copy(
            update={"numero": len(codigo.versiones) + 1, "especificacion": clave}
        )
        return {
            "codigo": codigo.model_copy(
                update={"versiones": (*codigo.versiones, version), "fallo_generacion": None}
            )
        }

    def n11_ejecucion(self, estado: EstadoGrafo) -> dict[str, Any]:
        """Importa los módulos y ejecuta las pruebas en el entorno aislado."""
        ejecucion = self.servicios.tester.ejecutar(
            estado["codigo"].vigente, estado["arquitectura"].especificacion
        )
        return {"validacion": estado["validacion"].model_copy(update={"ejecucion": ejecucion})}

    def n12_analisis_estatico(self, estado: EstadoGrafo) -> dict[str, Any]:
        """Aplica el análisis estático y la verificación de conformidad arquitectónica."""
        analisis = self.servicios.tester.analizar(
            estado["codigo"].vigente,
            estado["arquitectura"].especificacion,
            estado["requerimientos"],
        )
        return {
            "validacion": estado["validacion"].model_copy(
                update={
                    "hallazgos": analisis.hallazgos,
                    "conformidad": analisis.conformidad,
                    "no_evaluadas": analisis.no_evaluadas,
                }
            )
        }

    def n13_criterios_calidad(self, estado: EstadoGrafo) -> dict[str, Any]:
        """Recupera los criterios de calidad aplicables a los hallazgos y a los casos."""
        recuperado = self.servicios.tester.recuperar_criterios(estado["validacion"])
        return {"contexto": estado["contexto"].combinar(recuperado)}

    def n14_veredicto(self, estado: EstadoGrafo) -> dict[str, Any]:
        """Emite el veredicto por caso y el único, la retroalimentación y el reporte."""
        validacion = estado["validacion"]
        dictamen = self.servicios.tester.dictaminar(
            validacion.plan_pruebas,
            validacion,
            estado["contexto"],
            estado["codigo"].vigente,
            estado["arquitectura"].especificacion,
        )
        return {
            "validacion": validacion.model_copy(
                update={
                    "veredictos": dictamen.veredictos,
                    "hallazgos": dictamen.hallazgos,
                    "veredicto": dictamen.veredicto,
                    "retroalimentacion": dictamen.retroalimentacion,
                    "reporte": dictamen.reporte,
                }
            )
        }

    def n15_decision(self, estado: EstadoGrafo) -> dict[str, Any]:
        """Cuenta la iteración y decide: aprobación final, corrección o escalamiento.

        Cada devolución de la persona en N17 abre un ciclo de corrección nuevo, que empieza en
        la iteración 1: trae información nueva, no es un fallo del desarrollador. El límite del
        RF-27 se aplica por ciclo. Al agotarlo, la sesión escala a N17.
        """
        control = estado["control"]
        retornos = sum(
            1
            for aprobacion in estado["sesion"].aprobaciones
            if aprobacion.punto is PuntoControl.FINAL and aprobacion.decision is Decision.RECHAZADO
        )
        iteracion = 1 if retornos > control.retornos_humanos else control.iteracion + 1
        if estado["validacion"].aprobado:
            fase = Fase.APROBACION_FINAL
        elif iteracion >= control.limite_iteraciones:
            fase = Fase.REQUIERE_INTERVENCION
        else:
            fase = Fase.DESARROLLO
        return {
            "control": control.model_copy(
                update={"iteracion": iteracion, "retornos_humanos": retornos}
            ),
            "sesion": estado["sesion"].model_copy(update={"fase": fase}),
        }

    def n16_plan_pruebas(self, estado: EstadoGrafo) -> dict[str, Any]:
        """Deriva un caso de prueba de aceptación por cada escenario aprobado."""
        plan = tuple(
            CasoPrueba(
                id=f"CP-{requerimiento.id_requerimiento}-{escenario.id}",
                id_requerimiento=requerimiento.id_requerimiento,
                id_escenario=escenario.id,
                dado_que=escenario.dado_que,
                cuando=escenario.cuando,
                entonces=escenario.entonces,
            )
            for requerimiento in estado["requerimientos"].requerimientos
            for escenario in requerimiento.criterios_aceptacion
        )
        return {"validacion": Validacion(plan_pruebas=plan)}

    def n17_aprobacion_final(self, estado: EstadoGrafo) -> dict[str, Any]:
        """Somete el módulo validado por el tester a la aprobación humana final.

        La persona revisa el código, el veredicto por caso, los hallazgos, la conformidad por
        módulo y el reporte de validación, y puede registrar con su decisión las pruebas propias
        que ejecutó (RF-38). Si rechaza, devuelve el módulo al desarrollador, que corrige con sus
        observaciones y los hallazgos del tester, o al arquitecto, que rediseña.

        También recibe las sesiones escaladas por agotar el ciclo de corrección (RF-27): la
        aprobación queda bloqueada, porque el tester no aprobó la versión, y la persona decide
        cómo seguir. Puede que no haya versión, si ninguna generación fue válida.
        """
        validacion = estado["validacion"]
        version = estado["codigo"].vigente
        control = estado["control"]
        sesion = estado["sesion"]
        escalado = sesion.fase is Fase.REQUIERE_INTERVENCION
        aprobacion = _pedir_decision(
            PuntoControl.FINAL,
            {
                "escalado": escalado,
                "iteracion": control.iteracion,
                "limite_iteraciones": control.limite_iteraciones,
                "version": version.numero if version else None,
                "archivos": sorted(version.archivos) if version else [],
                "veredicto": validacion.veredicto.value if validacion.veredicto else None,
                "veredictos": [v.model_dump(mode="json") for v in validacion.veredictos],
                "hallazgos": [h.model_dump(mode="json") for h in validacion.hallazgos],
                "conformidad": [c.model_dump(mode="json") for c in validacion.conformidad],
                "no_evaluadas": list(validacion.no_evaluadas),
                "reporte": validacion.reporte,
            },
            bloqueo=(
                "El tester no aprobó el módulo y no puede aprobarse: devuélvalo al "
                "desarrollador o al arquitecto con observaciones, o cierre la sesión."
                if escalado
                else None
            ),
        )
        if aprobacion.decision is Decision.APROBADO:
            return {"sesion": _con_aprobacion(sesion, aprobacion, Fase.VALIDADO)}
        # La persona y el tester hablan al desarrollador a la vez: sus observaciones primero y
        # luego cada hallazgo de la versión, incluidos los de severidad baja.
        retroalimentacion = (
            aprobacion.observaciones,
            *(hallazgo.como_linea() for hallazgo in validacion.hallazgos),
        )
        cambios: dict[str, Any] = {
            "validacion": validacion.model_copy(update={"retroalimentacion": retroalimentacion})
        }
        if aprobacion.destino is Destino.ARQUITECTO:
            arquitectura = estado["arquitectura"]
            cambios["arquitectura"] = arquitectura.model_copy(
                update={
                    "observaciones_revisor": (
                        *arquitectura.observaciones_revisor,
                        aprobacion.observaciones,
                    )
                }
            )
            cambios["sesion"] = _con_aprobacion(sesion, aprobacion, Fase.DISENO)
        else:
            cambios["sesion"] = _con_aprobacion(sesion, aprobacion, Fase.DESARROLLO)
        return cambios


def construir_grafo(
    servicios: Servicios, configuracion: ConfiguracionOrquestador | None = None
) -> StateGraph:
    """Construye el grafo de 17 nodos con sus aristas y enrutadores.

    Args:
        servicios: Trabajo de los cuatro agentes, real o simulado.
        configuracion: Límites de los ciclos; si se omite, se lee del entorno.

    Returns:
        Grafo sin compilar; se compila con un checkpointer para habilitar las pausas humanas.
    """
    nodos = NodosGrafo(servicios, configuracion or ConfiguracionOrquestador())
    grafo = StateGraph(EstadoGrafo, input_schema=EntradaSesion)
    for nodo in Nodo:
        grafo.add_node(nodo.value, getattr(nodos, nodo.value))

    grafo.add_edge(START, Nodo.N1)
    for origen, destino in [
        (Nodo.N1, Nodo.N2),
        (Nodo.N2, Nodo.N3),
        (Nodo.N3, Nodo.N4),
        (Nodo.N5, Nodo.N6),
        (Nodo.N7, Nodo.N8),
        (Nodo.N8, Nodo.N9),
        (Nodo.N11, Nodo.N12),
        (Nodo.N12, Nodo.N13),
        (Nodo.N13, Nodo.N14),
        (Nodo.N14, Nodo.N15),
    ]:
        grafo.add_edge(origen, destino)

    grafo.add_conditional_edges(Nodo.N4, ruta_tras_suficiencia, [Nodo.N3, Nodo.N5])
    grafo.add_conditional_edges(
        Nodo.N6, ruta_tras_requerimientos, [Nodo.N3, Nodo.N5, Nodo.N7, Nodo.N16]
    )
    grafo.add_conditional_edges(Nodo.N9, ruta_tras_especificacion, [Nodo.N8, Nodo.N10])
    grafo.add_conditional_edges(Nodo.N10, ruta_tras_generacion, [Nodo.N11, Nodo.N15])
    grafo.add_conditional_edges(Nodo.N15, ruta_tras_decision, [Nodo.N10, Nodo.N17])
    grafo.add_conditional_edges(Nodo.N17, ruta_tras_aprobacion_final, [Nodo.N8, Nodo.N10, END])
    return grafo
