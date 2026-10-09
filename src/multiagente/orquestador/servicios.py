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
    Contexto,
    Conversacion,
    RegistroCaptura,
    Requerimientos,
    Validacion,
    VeredictoCaso,
    VersionCodigo,
)


class Dialogo(ModeloEstricto):
    """Resultado de un paso del diálogo (N3): registro actualizado y siguiente pregunta.

    Hay pregunta si y solo si queda algún atributo pendiente: así el ciclo N3–N4 siempre se
    detiene a esperar al cliente o avanza a la síntesis.
    """

    registro: RegistroCaptura
    siguiente_pregunta: TextoObligatorio | None

    @model_validator(mode="after")
    def _pregunta_si_hay_pendientes(self) -> Self:
        if (self.siguiente_pregunta is None) != (not self.registro.pendientes):
            raise ValueError(
                "Debe haber una siguiente pregunta si y solo si quedan atributos pendientes: "
                f"{self.registro.pendientes}"
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
        requiere_cliente: Algún defecto solo se resuelve con información del cliente (preguntas
            abiertas o marcadores de pendiente): N5 no puede corregirlo sin inventar, así que
            se escala al analista sin intentar la corrección automática.
    """

    defectos: tuple[TextoObligatorio, ...] = ()
    requiere_cliente: bool = False


class Diseno(ModeloEstricto):
    """Registro de decisión y especificación que produce el arquitecto (N8)."""

    registro_decision: TextoObligatorio
    especificacion: EspecificacionDiseno


class Dictamen(ModeloEstricto):
    """Veredicto por caso y retroalimentación al desarrollador (N14)."""

    veredictos: tuple[VeredictoCaso, ...]
    retroalimentacion: tuple[TextoObligatorio, ...]


class ServiciosElicitador(Protocol):
    """Trabajo del agente elicitador en N2, N3, N5 y N6."""

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
        self, especificacion: EspecificacionDiseno, requerimientos: Requerimientos
    ) -> list[str]:
        """Devuelve los errores de cobertura y de catálogo de la especificación (N9)."""
        ...


class ServiciosDesarrollador(Protocol):
    """Trabajo del agente desarrollador en N10. No recibe contexto recuperado."""

    def generar(
        self,
        requerimientos: Requerimientos,
        especificacion: EspecificacionDiseno,
        validacion: Validacion,
        numero: int,
    ) -> VersionCodigo:
        """Genera una versión del módulo atendiendo la retroalimentación vigente (N10)."""
        ...


class ServiciosTester(Protocol):
    """Trabajo del agente tester en N11 a N14."""

    def ejecutar(self, version: VersionCodigo) -> str:
        """Ejecuta el código y sus pruebas en el entorno aislado (N11)."""
        ...

    def analizar(self, version: VersionCodigo, especificacion: EspecificacionDiseno) -> list[str]:
        """Aplica el análisis estático y la conformidad arquitectónica (N12)."""
        ...

    def recuperar_criterios(self, version: VersionCodigo) -> Contexto:
        """Recupera los criterios de calidad aplicables al módulo (N13)."""
        ...

    def dictaminar(
        self,
        plan: tuple[CasoPrueba, ...],
        validacion: Validacion,
        contexto: Contexto,
    ) -> Dictamen:
        """Emite un veredicto por caso del plan y la retroalimentación (N14)."""
        ...


@dataclass(frozen=True)
class Servicios:
    """Servicios de los cuatro agentes que recibe el grafo."""

    elicitador: ServiciosElicitador
    arquitecto: ServiciosArquitecto
    desarrollador: ServiciosDesarrollador
    tester: ServiciosTester
