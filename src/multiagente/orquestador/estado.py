"""Estado tipado del grafo: las ocho particiones de la arquitectura (Tabla 4).

Cada partición es inmutable. Un nodo lee el estado y devuelve particiones nuevas construidas con
`model_copy`; nunca modifica las que recibe. Los agentes se comunican exclusivamente a través de
este estado.
"""

import re
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Self, TypedDict

from pydantic import (
    ConfigDict,
    Field,
    NonNegativeInt,
    PositiveInt,
    field_validator,
    model_validator,
)

from multiagente.core.esquemas.comunes import (
    IdEscenario,
    IdRequerimiento,
    ModeloEstricto,
    Prioridad,
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
    CERRADA = "cerrada"


class PuntoControl(StrEnum):
    """Puntos de control humano del flujo: N6, N9 y N17."""

    REQUERIMIENTOS = "requerimientos"
    ESPECIFICACION = "especificacion"
    FINAL = "final"


class Decision(StrEnum):
    """Decisión de la persona en un punto de control."""

    APROBADO = "aprobado"
    RECHAZADO = "rechazado"


class Destino(StrEnum):
    """A quién devuelve la persona el módulo cuando lo rechaza en la aprobación final (N17)."""

    DESARROLLADOR = "desarrollador"
    ARQUITECTO = "arquitecto"


class RespuestaHumana(ModeloEstricto):
    """Respuesta que entrega la persona al reanudar un punto de control.

    Attributes:
        pruebas_propias: Pruebas que la persona ejecutó antes de decidir en N17 (RF-38); quedan
            con la decisión como evidencia (RF-33).
        destino: Solo en un rechazo en N17: el desarrollador corrige el módulo (por defecto) o
            el arquitecto lo rediseña.
    """

    decision: Decision
    revisor: TextoObligatorio
    observaciones: TextoObligatorio | None = None
    pruebas_propias: "PruebasPropias | None" = None
    destino: Destino | None = None

    @model_validator(mode="after")
    def _rechazo_con_observaciones(self) -> Self:
        if self.decision is Decision.RECHAZADO and self.observaciones is None:
            raise ValueError("Un rechazo debe incluir observaciones para el agente anterior")
        if self.destino is not None and self.decision is not Decision.RECHAZADO:
            raise ValueError("El destino solo se indica al rechazar")
        return self


class AprobacionHumana(RespuestaHumana):
    """Decisión registrada en un punto de control, con su momento (RF-33)."""

    punto: PuntoControl
    fecha: datetime


class CierreSesion(ModeloEstricto):
    """Cierre de una sesión por una persona, sin módulo validado.

    Attributes:
        revisor: Quién la cerró.
        motivo: Por qué.
        desde: Dónde estaba la sesión: la pausa que esperaba o los nodos pendientes.
        fecha: Momento del cierre.
    """

    revisor: TextoObligatorio
    motivo: TextoObligatorio
    desde: TextoObligatorio
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
    cierre: CierreSesion | None = None

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


INTENTOS_SIN_RESPUESTA = 2
"""Veces que el cliente dice no saber un atributo antes de que N3 deje de preguntarlo (RF-02)."""


class RegistroCaptura(ModeloEstricto):
    """Información capturada durante la elicitación (RF-03).

    El criterio de suficiencia sigue la guía de preguntas estratégicas (eli-006): rol,
    funcionalidad, beneficio, reglas de negocio, datos de entrada y de salida, al menos un caso
    de error o excepción y la confirmación explícita del resumen por el cliente (RNF-08).

    `no_sabe` anota el atributo que se preguntaba cada vez que el cliente dijo no saberlo. Tras
    `INTENTOS_SIN_RESPUESTA` veces queda sin respuesta: sigue pendiente, pero N3 no lo vuelve a
    preguntar y el cliente puede confirmar el resumen sin él. La prioridad y las condiciones que el
    cliente ya definió (quién consume lo que pide, cómo se prueba, qué cambiará) son opcionales.
    """

    model_config = ConfigDict(frozen=True)

    rol: TextoObligatorio | None = None
    funcionalidad: TextoObligatorio | None = None
    beneficio: TextoObligatorio | None = None
    reglas_negocio: tuple[TextoObligatorio, ...] = ()
    datos_entrada: tuple[DatoEntrada, ...] = ()
    datos_salida: tuple[DatoSalida, ...] = ()
    excepciones: tuple[TextoObligatorio, ...] = ()
    condiciones: tuple[TextoObligatorio, ...] = ()
    prioridad: Prioridad | None = None
    supuestos: tuple[TextoObligatorio, ...] = ()
    preguntas_abiertas: tuple[TextoObligatorio, ...] = ()
    no_sabe: tuple[str, ...] = ()
    resumen_confirmado: bool = False

    @model_validator(mode="after")
    def _confirmacion_con_registro_completo(self) -> Self:
        if self.resumen_confirmado and set(self._faltantes()) - set(self.sin_respuesta):
            raise ValueError(
                "El resumen solo puede confirmarse cuando no falta ningún atributo, salvo los que "
                "el cliente no supo responder"
            )
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

    @property
    def sin_respuesta(self) -> list[str]:
        """Atributos que faltan y que el cliente no supo responder las veces que se le preguntó."""
        return [
            nombre
            for nombre in self._faltantes()
            if self.no_sabe.count(nombre) >= INTENTOS_SIN_RESPUESTA
        ]

    @property
    def por_preguntar(self) -> list[str]:
        """Pendientes que N3 todavía pregunta: todos menos los que quedaron sin respuesta."""
        sin_respuesta = set(self.sin_respuesta)
        return [nombre for nombre in self.pendientes if nombre not in sin_respuesta]


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
        fallo_sintesis: Por qué falló la última síntesis, si el modelo no dio una válida; los
            requerimientos son entonces los de la síntesis anterior, si la hubo.
    """

    historias: tuple[HistoriaUsuario, ...] = ()
    requerimientos: tuple[RequerimientoFormal, ...] = ()
    referencias: dict[IdRequerimiento, tuple[TextoObligatorio, ...]] = Field(default_factory=dict)
    defectos: tuple[TextoObligatorio, ...] = ()
    sintesis: NonNegativeInt = 0
    correcciones: NonNegativeInt = 0
    defectos_escalados: tuple[TextoObligatorio, ...] = ()
    fallo_sintesis: TextoObligatorio | None = None


class Arquitectura(Particion):
    """Registro de decisión y especificación de diseño del arquitecto.

    Attributes:
        disenos: Diseños producidos en la sesión; da la versión de la especificación.
        correcciones: Retornos automáticos de N9 a N8 desde la última decisión humana.
        observaciones_atendidas: Observaciones del revisor que ya conocía el último diseño; si
            llega una nueva, N8 vuelve a seleccionar la arquitectura.
        fallo_diseno: Por qué falló el último diseño, si el modelo no dio uno válido; la
            especificación es entonces la del diseño anterior, si lo hubo.
        capacidades_no_cubiertas: Lo que piden los requerimientos y el catálogo tecnológico no
            permite, según el último diseño; N9 lo muestra a la persona.
    """

    registro_decision: TextoObligatorio | None = None
    especificacion: EspecificacionDiseno | None = None
    errores_validacion: tuple[TextoObligatorio, ...] = ()
    observaciones_revisor: tuple[TextoObligatorio, ...] = ()
    disenos: NonNegativeInt = 0
    correcciones: NonNegativeInt = 0
    observaciones_atendidas: NonNegativeInt = 0
    fallo_diseno: TextoObligatorio | None = None
    capacidades_no_cubiertas: tuple[TextoObligatorio, ...] = ()


class VersionCodigo(ModeloEstricto):
    """Versión del módulo generada por el desarrollador (RF-19).

    Attributes:
        numero: Número de la versión; la primera es 1.
        archivos: Contenido de cada archivo por su ruta: módulos, pruebas y `USO.md`.
        defectos_atendidos: Retroalimentación que esta versión atiende.
        huella_estilo: SHA-256 de la configuración de estilo que rigió la generación (RF-36).
        especificacion: Especificación con que se generó, como `ED-01 v0.2`: tras un rediseño,
            la versión siguiente se genera de cero.
    """

    # El contenido de los archivos se conserva tal cual: recortarlo quitaría el salto de línea
    # final que exige el estilo y cambiaría el código que se ejecuta y se analiza.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)

    numero: PositiveInt
    archivos: dict[str, str] = Field(min_length=1)
    defectos_atendidos: tuple[TextoObligatorio, ...] = ()
    huella_estilo: TextoObligatorio | None = None
    especificacion: TextoObligatorio | None = None


class Codigo(Particion):
    """Historial de versiones del módulo.

    Attributes:
        fallo_generacion: Por qué falló la última generación, si el modelo no dio una versión
            válida; N15 la cuenta como una iteración fallida.
    """

    versiones: tuple[VersionCodigo, ...] = ()
    fallo_generacion: TextoObligatorio | None = None

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
    """Dictamen del tester sobre un caso del plan de pruebas, con su evidencia (RF-21).

    Attributes:
        id_caso: Caso del plan de pruebas (N16).
        cumple: Si el caso se cumple.
        evidencia: Por qué se cumple o no: resultado de sus pruebas y juicio sobre ellas.
        pruebas: Pruebas que sirven de evidencia, como `tests/test_x.py::test_rf_01_esc_01`.
    """

    id_caso: TextoObligatorio
    cumple: bool
    evidencia: TextoObligatorio
    pruebas: tuple[TextoObligatorio, ...] = ()


class Severidad(StrEnum):
    """Severidad de un hallazgo según la escala del tester (cal-sv)."""

    ALTA = "alta"
    MEDIA = "media"
    BAJA = "baja"


class Veredicto(StrEnum):
    """Veredicto único del tester sobre una versión del módulo (cal-sv)."""

    APROBADO = "aprobado"
    RECHAZADO = "rechazado"


class ResultadoPrueba(StrEnum):
    """Resultado de una prueba ejecutada en el entorno aislado."""

    PASO = "paso"
    FALLO = "fallo"
    ERROR = "error"
    OMITIDA = "omitida"


class PruebaEjecutada(ModeloEstricto):
    """Prueba de la versión ejecutada en el entorno aislado (N11)."""

    archivo: TextoObligatorio
    nombre: TextoObligatorio
    resultado: ResultadoPrueba
    duracion_ms: NonNegativeInt = 0
    mensaje: str = ""

    @property
    def identificador(self) -> str:
        """Archivo y nombre, p. ej. `tests/test_avaluo.py::test_rf_01_esc_01`."""
        return f"{self.archivo}::{self.nombre}"


class EjecucionPruebas(ModeloEstricto):
    """Resultado de ejecutar la versión y sus pruebas en el entorno aislado (N11, RF-20).

    Attributes:
        errores_importacion: Traza de cada módulo declarado que no se pudo importar.
        pruebas: Cada prueba ejecutada con su resultado.
        errores_recoleccion: Archivos de prueba que no se pudieron recolectar, con su error.
        vencido: Si alguna ejecución alcanzó el tiempo límite.
        duracion_ms: Duración total de las ejecuciones en el entorno aislado.
        salida: Final de la salida de pytest.
    """

    errores_importacion: dict[str, str] = Field(default_factory=dict)
    pruebas: tuple[PruebaEjecutada, ...] = ()
    errores_recoleccion: tuple[TextoObligatorio, ...] = ()
    vencido: bool = False
    duracion_ms: NonNegativeInt = 0
    salida: str = ""


RUTA_PRUEBA_PROPIA = re.compile(r"tests/test_\w+\.py")
"""Ruta admitida para un archivo de pruebas propias: el pytest del entorno aislado lo recolecta."""


class PruebasPropias(ModeloEstricto):
    """Pruebas que la persona escribe y ejecuta en N17 contra la versión vigente (RF-38).

    Attributes:
        archivos: Contenido de cada archivo de prueba por su ruta, `tests/test_*.py`.
        ejecucion: Resultado de esas pruebas en el entorno aislado.
    """

    # Como en `VersionCodigo`, el contenido se conserva tal cual.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)

    archivos: dict[str, str] = Field(min_length=1)
    ejecucion: EjecucionPruebas

    @field_validator("archivos")
    @classmethod
    def _rutas_de_prueba(cls, archivos: dict[str, str]) -> dict[str, str]:
        if ajenas := sorted(r for r in archivos if not RUTA_PRUEBA_PROPIA.fullmatch(r)):
            raise ValueError(f"Las pruebas propias van en tests/test_*.py: {ajenas}")
        return archivos


# `RespuestaHumana` se declara antes que la ejecución de pruebas que guarda en `pruebas_propias`.
RespuestaHumana.model_rebuild()
AprobacionHumana.model_rebuild()
Sesion.model_rebuild()


class Hallazgo(ModeloEstricto):
    """Incumplimiento de una regla de calidad, con su evidencia (RF-23, RF-24).

    Attributes:
        regla: Regla de calidad que lo origina, p. ej. `CAL-MT-001`.
        severidad: Severidad de la regla en la base de conocimiento.
        ubicacion: Archivo y línea, módulo o caso afectado.
        descripcion: Qué se encontró.
        sugerencia: Cómo corregirlo, para el desarrollador.
        origen: Comprobación que lo detectó, p. ej. `ruff:S307`, `conformidad` o `ejecucion`.
    """

    regla: TextoObligatorio
    severidad: Severidad
    ubicacion: TextoObligatorio
    descripcion: TextoObligatorio
    sugerencia: TextoObligatorio
    origen: TextoObligatorio

    def como_linea(self) -> str:
        """Defecto para el desarrollador, con campos fijos (RF-24).

        Returns:
            `[regla · severidad] ubicación · defecto · Sugerencia: …`.
        """
        return (
            f"[{self.regla} · {self.severidad.value}] {self.ubicacion} · {self.descripcion} · "
            f"Sugerencia: {self.sugerencia}"
        )


class ConformidadModulo(ModeloEstricto):
    """Conformidad arquitectónica de un módulo declarado (RF-22)."""

    modulo: TextoObligatorio
    ruta: TextoObligatorio
    existe: bool
    interfaces_conformes: tuple[TextoObligatorio, ...] = ()
    interfaces_divergentes: tuple[TextoObligatorio, ...] = ()
    dependencias_no_autorizadas: tuple[TextoObligatorio, ...] = ()


class Validacion(Particion):
    """Plan de pruebas, resultados de la validación y retroalimentación al desarrollador.

    Attributes:
        plan_pruebas: Casos de prueba de aceptación (N16).
        ejecucion: Resultado de la ejecución en el entorno aislado (N11).
        hallazgos: Hallazgos por regla: los del análisis estático (N12) y, tras N14, también
            los de la ejecución y los casos.
        conformidad: Conformidad de cada módulo declarado (N12).
        no_evaluadas: Reglas de calidad que no tienen comprobación automática.
        veredictos: Dictamen por caso del plan (N14).
        veredicto: Veredicto único según la regla de cal-sv (N14).
        retroalimentacion: Defectos que debe atender el desarrollador, uno por línea.
        reporte: Reporte de validación en Markdown, para la persona (RF-24).
    """

    plan_pruebas: tuple[CasoPrueba, ...] = ()
    ejecucion: EjecucionPruebas | None = None
    hallazgos: tuple[Hallazgo, ...] = ()
    conformidad: tuple[ConformidadModulo, ...] = ()
    no_evaluadas: tuple[TextoObligatorio, ...] = ()
    veredictos: tuple[VeredictoCaso, ...] = ()
    veredicto: Veredicto | None = None
    retroalimentacion: tuple[TextoObligatorio, ...] = ()
    reporte: TextoObligatorio | None = None

    @property
    def aprobado(self) -> bool:
        """Indica si el veredicto es aprobado y todos los casos del plan cumplen."""
        cumplidos = {veredicto.id_caso for veredicto in self.veredictos if veredicto.cumple}
        return (
            self.veredicto is Veredicto.APROBADO
            and bool(self.plan_pruebas)
            and all(caso.id in cumplidos for caso in self.plan_pruebas)
        )


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
    """Iteración del ciclo de corrección, límites configurados y costo acumulado.

    Attributes:
        iteracion: Iteración del ciclo de corrección en curso; cada devolución de la persona en
            N17 abre un ciclo nuevo, que empieza en 1.
        retornos_humanos: Devoluciones de N17 ya contadas por N15.
    """

    iteracion: NonNegativeInt = 0
    retornos_humanos: NonNegativeInt = 0
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
