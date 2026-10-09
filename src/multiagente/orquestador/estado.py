"""Estado tipado del grafo: las ocho particiones de la arquitectura (Tabla 4).

Cada partición es inmutable. Un nodo lee el estado y devuelve particiones nuevas construidas con
`model_copy`; nunca modifica las que recibe. Los agentes se comunican exclusivamente a través de
este estado.
"""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Self, TypedDict

from pydantic import ConfigDict, Field, NonNegativeInt, PositiveInt, model_validator

from multiagente.core.esquemas.comunes import (
    IdEscenario,
    IdRequerimiento,
    ModeloEstricto,
    TextoObligatorio,
    Version,
)
from multiagente.core.esquemas.especificacion_diseno import EspecificacionDiseno
from multiagente.core.esquemas.requerimiento import (
    DatoEntrada,
    DatoSalida,
    HistoriaUsuario,
    RequerimientoFormal,
)


class Fase(StrEnum):
    """Fase en la que se encuentra la sesión."""

    ELICITACION = "elicitacion"
    DISENO = "diseno"
    DESARROLLO = "desarrollo"
    APROBACION_FINAL = "aprobacion_final"
    VALIDADO = "validado"
    REQUIERE_INTERVENCION = "requiere_intervencion_humana"


class PuntoControl(StrEnum):
    """Puntos de control humano del flujo: N6, N9 y N17."""

    REQUERIMIENTOS = "requerimientos"
    ESPECIFICACION = "especificacion"
    FINAL = "final"


class Decision(StrEnum):
    """Decisión de la persona en un punto de control."""

    APROBADO = "aprobado"
    RECHAZADO = "rechazado"


class RespuestaHumana(ModeloEstricto):
    """Respuesta que entrega la persona al reanudar un punto de control."""

    decision: Decision
    revisor: TextoObligatorio
    observaciones: TextoObligatorio | None = None

    @model_validator(mode="after")
    def _rechazo_con_observaciones(self) -> Self:
        if self.decision is Decision.RECHAZADO and self.observaciones is None:
            raise ValueError("Un rechazo debe incluir observaciones para el agente anterior")
        return self


class AprobacionHumana(RespuestaHumana):
    """Decisión registrada en un punto de control, con su momento (RF-33)."""

    punto: PuntoControl
    fecha: datetime


class Particion(ModeloEstricto):
    """Base de las particiones del estado: inmutables una vez creadas."""

    model_config = ConfigDict(frozen=True)


class Sesion(Particion):
    """Identificación de la sesión, su fase y el historial de aprobaciones humanas."""

    id_sesion: TextoObligatorio
    cliente: TextoObligatorio
    proyecto: TextoObligatorio
    fase: Fase
    creada: datetime
    aprobaciones: tuple[AprobacionHumana, ...] = ()

    def ultima_aprobacion(self, punto: PuntoControl) -> AprobacionHumana | None:
        """Devuelve la decisión más reciente tomada en un punto de control.

        Args:
            punto: Punto de control consultado.

        Returns:
            La última aprobación registrada en ese punto, o None si no hay ninguna.
        """
        decisiones = [aprobacion for aprobacion in self.aprobaciones if aprobacion.punto is punto]
        return decisiones[-1] if decisiones else None


class Emisor(StrEnum):
    """Quién emite un turno de la conversación."""

    CLIENTE = "cliente"
    ELICITADOR = "elicitador"


class Turno(ModeloEstricto):
    """Turno de la conversación de elicitación."""

    emisor: Emisor
    texto: TextoObligatorio
    fecha: datetime


class RegistroCaptura(ModeloEstricto):
    """Información capturada durante la elicitación (RF-03).

    El criterio de suficiencia sigue la guía de preguntas estratégicas (eli-006): rol,
    funcionalidad, beneficio, reglas de negocio, datos de entrada y de salida, al menos un caso
    de error o excepción y la confirmación explícita del resumen por el cliente (RNF-08).
    """

    model_config = ConfigDict(frozen=True)

    rol: TextoObligatorio | None = None
    funcionalidad: TextoObligatorio | None = None
    beneficio: TextoObligatorio | None = None
    reglas_negocio: tuple[TextoObligatorio, ...] = ()
    datos_entrada: tuple[DatoEntrada, ...] = ()
    datos_salida: tuple[DatoSalida, ...] = ()
    excepciones: tuple[TextoObligatorio, ...] = ()
    supuestos: tuple[TextoObligatorio, ...] = ()
    preguntas_abiertas: tuple[TextoObligatorio, ...] = ()
    resumen_confirmado: bool = False

    @model_validator(mode="after")
    def _confirmacion_con_registro_completo(self) -> Self:
        if self.resumen_confirmado and self._faltantes():
            raise ValueError("El resumen solo puede confirmarse cuando no falta ningún atributo")
        return self

    def _faltantes(self) -> list[str]:
        faltantes = [
            nombre
            for nombre in ("rol", "funcionalidad", "beneficio")
            if getattr(self, nombre) is None
        ]
        faltantes.extend(
            nombre
            for nombre in ("reglas_negocio", "datos_entrada", "datos_salida", "excepciones")
            if not getattr(self, nombre)
        )
        return faltantes

    @property
    def pendientes(self) -> list[str]:
        """Atributos que aún faltan, en el orden en que se preguntan; la confirmación al final."""
        faltantes = self._faltantes()
        if not self.resumen_confirmado:
            faltantes.append("confirmacion")
        return faltantes


class Conversacion(Particion):
    """Historial del diálogo, registro capturado y observaciones del revisor.

    El primer turno es la necesidad con que el cliente abrió la sesión. `turnos_procesados`
    cuenta los turnos que el elicitador ya tuvo en cuenta, de modo que una respuesta nueva del
    cliente se distingue de una ya procesada.
    """

    turnos: tuple[Turno, ...] = ()
    turnos_procesados: NonNegativeInt = 0
    registro: RegistroCaptura = Field(default_factory=RegistroCaptura)
    pregunta_pendiente: TextoObligatorio | None = None
    observaciones_revisor: tuple[TextoObligatorio, ...] = ()

    @property
    def turnos_cliente(self) -> int:
        """Número de intervenciones del cliente, incluida la necesidad inicial."""
        return sum(1 for turno in self.turnos if turno.emisor is Emisor.CLIENTE)

    @property
    def necesidad(self) -> str | None:
        """Necesidad con que el cliente abrió la sesión, o None si aún no hay turnos."""
        return next((turno.texto for turno in self.turnos if turno.emisor is Emisor.CLIENTE), None)

    @property
    def respuesta_nueva(self) -> str | None:
        """Última intervención del cliente que el elicitador aún no ha procesado, si la hay."""
        nuevos = self.turnos[self.turnos_procesados :]
        clientes = [turno.texto for turno in nuevos if turno.emisor is Emisor.CLIENTE]
        return clientes[-1] if clientes else None


class Requerimientos(Particion):
    """Historias y requerimientos formales producidos por el elicitador.

    Attributes:
        referencias: Fragmentos de contexto que sustentan cada requerimiento (RF-04).
        defectos: Defectos de calidad que N5 debe corregir (RF-07).
        sintesis: Síntesis producidas en la sesión; da la versión de los requerimientos.
        correcciones: Retornos automáticos de N6 a N5 desde la última decisión humana.
        defectos_escalados: Defectos que seguían sin corregir cuando la persona decidió.
    """

    historias: tuple[HistoriaUsuario, ...] = ()
    requerimientos: tuple[RequerimientoFormal, ...] = ()
    referencias: dict[IdRequerimiento, tuple[TextoObligatorio, ...]] = Field(default_factory=dict)
    defectos: tuple[TextoObligatorio, ...] = ()
    sintesis: NonNegativeInt = 0
    correcciones: NonNegativeInt = 0
    defectos_escalados: tuple[TextoObligatorio, ...] = ()


class Arquitectura(Particion):
    """Registro de decisión y especificación de diseño del arquitecto.

    Attributes:
        disenos: Diseños producidos en la sesión; da la versión de la especificación.
        correcciones: Retornos automáticos de N9 a N8 desde la última decisión humana.
    """

    registro_decision: TextoObligatorio | None = None
    especificacion: EspecificacionDiseno | None = None
    errores_validacion: tuple[TextoObligatorio, ...] = ()
    observaciones_revisor: tuple[TextoObligatorio, ...] = ()
    disenos: NonNegativeInt = 0
    correcciones: NonNegativeInt = 0


class VersionCodigo(ModeloEstricto):
    """Versión del módulo generada por el desarrollador (RF-19)."""

    numero: PositiveInt
    archivos: dict[str, str] = Field(min_length=1)
    defectos_atendidos: tuple[TextoObligatorio, ...] = ()


class Codigo(Particion):
    """Historial de versiones del módulo."""

    versiones: tuple[VersionCodigo, ...] = ()

    @property
    def vigente(self) -> VersionCodigo | None:
        """Última versión generada, o None si aún no hay código."""
        return self.versiones[-1] if self.versiones else None


class CasoPrueba(ModeloEstricto):
    """Caso de prueba de aceptación derivado de un escenario aprobado (N16)."""

    id: TextoObligatorio
    id_requerimiento: IdRequerimiento
    id_escenario: IdEscenario
    dado_que: TextoObligatorio
    cuando: TextoObligatorio
    entonces: TextoObligatorio


class VeredictoCaso(ModeloEstricto):
    """Dictamen del tester sobre un caso del plan de pruebas, con su evidencia (RF-21)."""

    id_caso: TextoObligatorio
    cumple: bool
    evidencia: TextoObligatorio


class Validacion(Particion):
    """Plan de pruebas, resultados de la validación y retroalimentación al desarrollador."""

    plan_pruebas: tuple[CasoPrueba, ...] = ()
    ejecucion: TextoObligatorio | None = None
    hallazgos: tuple[TextoObligatorio, ...] = ()
    veredictos: tuple[VeredictoCaso, ...] = ()
    retroalimentacion: tuple[TextoObligatorio, ...] = ()

    @property
    def aprobado(self) -> bool:
        """Indica si todos los casos del plan tienen veredicto y todos cumplen."""
        cumplidos = {veredicto.id_caso for veredicto in self.veredictos if veredicto.cumple}
        return bool(self.plan_pruebas) and all(caso.id in cumplidos for caso in self.plan_pruebas)


class FragmentoContexto(ModeloEstricto):
    """Fragmento recuperado de una base de conocimiento, con su fuente (RF-04, RF-30)."""

    model_config = ConfigDict(frozen=True)

    documento_id: TextoObligatorio
    version_documento: Version
    titulo: TextoObligatorio
    contenido: TextoObligatorio
    similitud: float

    @property
    def referencia(self) -> str:
        """Referencia estable al fragmento: documento, versión y título de la sección."""
        return f"{self.documento_id} v{self.version_documento} · {self.titulo}"


class Contexto(Particion):
    """Fragmentos recuperados por colección y contexto descartado."""

    fragmentos: dict[str, tuple[FragmentoContexto, ...]] = Field(default_factory=dict)
    descartados: tuple[str, ...] = ()

    def combinar(self, otro: "Contexto") -> "Contexto":
        """Agrega la recuperación de otro nodo sin perder la de los anteriores.

        Args:
            otro: Contexto recuperado por el nodo actual.

        Returns:
            Contexto nuevo; las colecciones del otro reemplazan a las del mismo nombre.
        """
        return Contexto(
            fragmentos={**self.fragmentos, **otro.fragmentos},
            descartados=(*self.descartados, *otro.descartados),
        )


class Control(Particion):
    """Iteración del ciclo de corrección, límites configurados y costo acumulado."""

    iteracion: NonNegativeInt = 0
    limite_iteraciones: PositiveInt
    limite_turnos: PositiveInt
    limite_correcciones: PositiveInt
    limite_correcciones_diseno: PositiveInt
    costo_acumulado_usd: Decimal = Decimal(0)


PARTICIONES: tuple[type[Particion], ...] = (
    Sesion,
    Conversacion,
    Requerimientos,
    Arquitectura,
    Codigo,
    Validacion,
    Contexto,
    Control,
)
"""Clases que se guardan en la raíz del estado y que el serializador debe reconocer."""


class EntradaSesion(TypedDict):
    """Datos con los que se abre una sesión; los consume N1.

    La necesidad es la primera intervención del cliente: con ella N2 recupera el contexto de
    dominio antes de la primera pregunta (RF-04).
    """

    cliente: str
    proyecto: str
    necesidad: str


class EstadoGrafo(TypedDict, total=False):
    """Estado compartido del grafo: entrada de la sesión y ocho particiones."""

    cliente: str
    proyecto: str
    necesidad: str
    sesion: Sesion
    conversacion: Conversacion
    requerimientos: Requerimientos
    arquitectura: Arquitectura
    codigo: Codigo
    validacion: Validacion
    contexto: Contexto
    control: Control
