"""Servicios que el grafo inyecta en los nodos: el trabajo de cada agente.

El orquestador posee el estado, las transiciones y los puntos de control humano. El trabajo de
modelos de lenguaje, recuperación y ejecución lo aporta un servicio por agente, de modo que un
agente real reemplaza a su versión simulada sin modificar el grafo (RNF-05).
"""

from dataclasses import dataclass
from typing import Protocol, Self

from pydantic import Field, model_validator

from multiagente.core.esquemas.comunes import IdRequerimiento, ModeloEstricto, TextoObligatorio
from multiagente.core.esquemas.especificacion_diseno import EspecificacionDiseno
from multiagente.core.esquemas.requerimiento import HistoriaUsuario, RequerimientoFormal
from multiagente.orquestador.estado import (
    Arquitectura,
    CasoPrueba,
    ConformidadModulo,
    Contexto,
    Conversacion,
    EjecucionPruebas,
    Hallazgo,
    RecorridoEscenario,
    RegistroCaptura,
    Requerimientos,
    Validacion,
    Veredicto,
    VeredictoCaso,
    VersionCodigo,
)


class Dialogo(ModeloEstricto):
    """Resultado de un paso del diálogo (N3): registro actualizado y siguiente pregunta.

    Hay pregunta si y solo si queda algo por preguntar: así el ciclo N3–N4 siempre se detiene a
    esperar al cliente o avanza a la síntesis.
    """

    registro: RegistroCaptura
    siguiente_pregunta: TextoObligatorio | None

    @model_validator(mode="after")
    def _pregunta_si_hay_pendientes(self) -> Self:
        if (self.siguiente_pregunta is None) != (not self.registro.por_preguntar):
            raise ValueError(
                "Debe haber una siguiente pregunta si y solo si queda algo por preguntar: "
                f"{self.registro.por_preguntar}"
            )
        return self


class Sintesis(ModeloEstricto):
    """Artefactos que sintetiza el elicitador al cerrar la elicitación (N5)."""

    historias: tuple[HistoriaUsuario, ...]
    requerimientos: tuple[RequerimientoFormal, ...]
    referencias: dict[IdRequerimiento, tuple[TextoObligatorio, ...]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _referencias_de_requerimientos_propios(self) -> Self:
        propios = {requerimiento.id_requerimiento for requerimiento in self.requerimientos}
        if ajenos := sorted(set(self.referencias) - propios):
            raise ValueError(f"Referencias de requerimientos que no existen: {ajenos}")
        return self


class VerificacionCalidad(ModeloEstricto):
    """Resultado de la verificación de calidad de los requerimientos (N6, RF-07).

    Attributes:
        defectos: Defectos encontrados; vacía si los requerimientos cumplen.
        del_cliente: Los defectos que solo se resuelven con información del cliente (preguntas
            abiertas o marcadores de pendiente). N5 no puede corregirlos sin inventar, así que
            escalan al analista sin intentar la corrección automática; los demás sí se corrigen
            (ADR-0015).
    """

    defectos: tuple[TextoObligatorio, ...] = ()
    del_cliente: tuple[TextoObligatorio, ...] = ()

    @model_validator(mode="after")
    def _del_cliente_entre_los_defectos(self) -> Self:
        if faltan := set(self.del_cliente) - set(self.defectos):
            raise ValueError(f"defectos del cliente que no están entre los defectos: {faltan}")
        return self

    @property
    def requiere_cliente(self) -> bool:
        """Si algún defecto solo se resuelve con información del cliente."""
        return bool(self.del_cliente)

    @property
    def corregibles(self) -> tuple[str, ...]:
        """Defectos que N5 puede corregir sin el cliente, en el orden en que se encontraron."""
        return tuple(defecto for defecto in self.defectos if defecto not in self.del_cliente)


class Diseno(ModeloEstricto):
    """Registro de decisión y especificación que produce el arquitecto (N8).

    Attributes:
        capacidades_no_cubiertas: Lo que piden los requerimientos y el catálogo tecnológico no
            permite (regla 4 de arq-004): el diseño las omite y la persona decide en N9.
        recorridos: Cómo se ejecuta cada escenario aprobado con las interfaces del diseño.
        revisiones: Revisiones del registro de decisión, la última incluida si este diseño
            atendió observaciones del revisor.
    """

    registro_decision: TextoObligatorio
    especificacion: EspecificacionDiseno
    capacidades_no_cubiertas: tuple[TextoObligatorio, ...] = ()
    recorridos: tuple[RecorridoEscenario, ...] = ()
    revisiones: tuple[TextoObligatorio, ...] = ()


class AnalisisEstatico(ModeloEstricto):
    """Hallazgos del análisis estático y conformidad arquitectónica de una versión (N12)."""

    hallazgos: tuple[Hallazgo, ...] = ()
    conformidad: tuple[ConformidadModulo, ...] = ()
    no_evaluadas: tuple[TextoObligatorio, ...] = ()


class Dictamen(ModeloEstricto):
    """Veredicto del tester sobre una versión (N14).

    Attributes:
        veredictos: Dictamen de cada caso del plan de pruebas, con su evidencia (RF-21).
        hallazgos: Todos los hallazgos de la versión: los del análisis estático y los de la
            ejecución y los casos.
        veredicto: Veredicto único según la regla de cal-sv.
        retroalimentacion: Defectos para el desarrollador, uno por línea (RF-24).
        reporte: Reporte de validación en Markdown, para la persona.
    """

    veredictos: tuple[VeredictoCaso, ...]
    hallazgos: tuple[Hallazgo, ...] = ()
    veredicto: Veredicto
    retroalimentacion: tuple[TextoObligatorio, ...]
    reporte: TextoObligatorio


class ServiciosElicitador(Protocol):
    """Trabajo del agente elicitador en N2, N3, N5 y N6, también al enmendar desde N17."""

    def recuperar_contexto(self, conversacion: Conversacion) -> Contexto:
        """Recupera contexto de elicitación y de dominio de negocio (N2)."""
        ...

    def dialogar(self, conversacion: Conversacion, contexto: Contexto) -> Dialogo:
        """Procesa la respuesta nueva del cliente, si la hay, y formula la siguiente pregunta (N3).

        Sin respuesta nueva (tras un rechazo en N6) solo formula la pregunta que atiende las
        observaciones del revisor; la confirmación del resumen exige una respuesta nueva.
        """
        ...

    def sintetizar(
        self,
        conversacion: Conversacion,
        contexto: Contexto,
        previos: Requerimientos,
        proyecto: str,
    ) -> Sintesis:
        """Sintetiza historias y requerimientos formales; corrige los defectos previos (N5)."""
        ...

    def enmendar(
        self, conversacion: Conversacion, requerimientos: Requerimientos, proyecto: str
    ) -> Sintesis:
        """Incorpora a los requerimientos vigentes la enmienda en curso desde N17 (N5).

        Atiende también las observaciones del analista y los defectos de N6. Solo cambia la
        regla y los escenarios de los requerimientos afectados, que suben de versión: no agrega,
        quita ni renumera requerimientos, no elimina escenarios, y conserva la historia, los
        títulos y las referencias (ADR-0015).
        """
        ...

    def verificar_calidad(self, requerimientos: Requerimientos) -> VerificacionCalidad:
        """Verifica los atributos de calidad de los requerimientos (N6, RF-07)."""
        ...


class ServiciosArquitecto(Protocol):
    """Trabajo del agente arquitecto en N7, N8 y N9."""

    def recuperar_catalogo(self, requerimientos: Requerimientos) -> Contexto:
        """Recupera del catálogo las arquitecturas de referencia aplicables (N7)."""
        ...

    def disenar(
        self, requerimientos: Requerimientos, contexto: Contexto, previa: Arquitectura
    ) -> Diseno:
        """Selecciona y parametriza la arquitectura; atiende las observaciones previas (N8)."""
        ...

    def validar(
        self,
        especificacion: EspecificacionDiseno,
        requerimientos: Requerimientos,
        recorridos: tuple[RecorridoEscenario, ...] = (),
    ) -> list[str]:
        """Devuelve los errores de la especificación y de los recorridos de sus escenarios (N9)."""
        ...


class Rediseno(ModeloEstricto):
    """Lo que recibe el desarrollador cuando la especificación cambió tras su última versión.

    La versión previa ya no se corrige, porque su especificación es otra: sirve de referencia
    para conservar lo que sigue valiendo y atender la retroalimentación que motivó el rediseño
    (ADR-0015).

    Attributes:
        version_previa: Versión vigente antes del rediseño.
        revision: Última revisión del registro de decisión, con las observaciones, la respuesta
            del arquitecto y los cambios de la especificación; None si el rediseño no dejó una.
    """

    version_previa: VersionCodigo
    revision: TextoObligatorio | None = None


class ServiciosDesarrollador(Protocol):
    """Trabajo del agente desarrollador en N10. No recibe contexto recuperado."""

    def generar(
        self,
        requerimientos: Requerimientos,
        especificacion: EspecificacionDiseno,
        validacion: Validacion,
        previa: VersionCodigo | None,
        rediseno: Rediseno | None = None,
    ) -> VersionCodigo:
        """Genera una versión del módulo atendiendo la retroalimentación vigente (N10).

        Sin versión previa genera el módulo completo; con ella, corrige solo lo necesario para
        atender la retroalimentación (RF-19). Tras un rediseño no hay versión previa que
        corregir, pero la anterior llega como referencia. La versión nueva lleva el número
        siguiente.
        """
        ...


class ServiciosTester(Protocol):
    """Trabajo del agente tester en N11 a N14. No modifica el código (decisión 6)."""

    def ejecutar(
        self, version: VersionCodigo, especificacion: EspecificacionDiseno
    ) -> EjecucionPruebas:
        """Importa los módulos y ejecuta las pruebas en el entorno aislado (N11, RF-20)."""
        ...

    def analizar(
        self,
        version: VersionCodigo,
        especificacion: EspecificacionDiseno,
        requerimientos: Requerimientos,
    ) -> AnalisisEstatico:
        """Aplica el análisis estático y la conformidad arquitectónica (N12, RF-22, RF-23)."""
        ...

    def recuperar_criterios(self, validacion: Validacion) -> Contexto:
        """Recupera los criterios de calidad aplicables a los hallazgos y a los casos (N13)."""
        ...

    def dictaminar(
        self,
        plan: tuple[CasoPrueba, ...],
        validacion: Validacion,
        contexto: Contexto,
        version: VersionCodigo,
        especificacion: EspecificacionDiseno | None = None,
    ) -> Dictamen:
        """Emite el veredicto por caso y el único, y la retroalimentación (N14, RF-21, RF-24).

        La especificación le dice al juez qué interfaces y qué datos ofrece el módulo.
        """
        ...


@dataclass(frozen=True)
class Servicios:
    """Servicios de los cuatro agentes que recibe el grafo."""

    elicitador: ServiciosElicitador
    arquitecto: ServiciosArquitecto
    desarrollador: ServiciosDesarrollador
    tester: ServiciosTester
