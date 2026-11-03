"""Operación de las sesiones, compartida por la consola y la web (paso 12).

Las interfaces no tocan el grafo: abren, responden, deciden, reanudan, consultan y exportan por
medio del `Operador`. Así la consola y la web aplican las mismas reglas: qué se puede hacer en
cada pausa, cómo se reanuda tras una falla y qué se exporta.
"""

import uuid
from collections.abc import Iterator, Mapping
from contextlib import AbstractContextManager, contextmanager, nullcontext
from datetime import UTC, datetime
from typing import Any

from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, ConfigDict

from multiagente.agentes.servicios import crear_servicios
from multiagente.agentes.tester.ejecucion import pruebas_ejecutadas
from multiagente.core.configuracion import (
    ConfiguracionInterfaces,
    ConfiguracionTester,
)
from multiagente.interfaces.documentos import paquete_del_modulo, trazabilidad_md
from multiagente.llm.traza import RegistroPorSesion
from multiagente.orquestador.ejecucion import (
    Avance,
    Pausa,
    avanzar,
    configuracion_hilo,
    iniciar_sesion,
    pausa_pendiente,
    validaciones,
)
from multiagente.orquestador.estado import (
    RUTA_PRUEBA_PROPIA,
    CierreSesion,
    Decision,
    Destino,
    EjecucionPruebas,
    EstadoGrafo,
    Fase,
    PruebasPropias,
    PuntoControl,
    ResultadoPrueba,
    Validacion,
    VersionCodigo,
)
from multiagente.orquestador.grafo import Nodo, construir_grafo
from multiagente.persistencia.conexiones import ConexionDePool, abrir_pool
from multiagente.persistencia.puntos_control import (
    abrir_checkpointer_compartido,
    identificadores_de_sesion,
)
from multiagente.sandbox.ejecutor import EntornoAislado, detalle_de_falla
from multiagente.sandbox.requisitos import requisitos_del_entorno

PUNTOS_DE_CONTROL = tuple(punto.value for punto in PuntoControl)
"""Pausas en que decide una persona del equipo: N6, N9 y N17."""

NOMBRES_DE_NODO = {
    Nodo.N1: "N1 · apertura de la sesión",
    Nodo.N2: "N2 · contexto de elicitación",
    Nodo.N3: "N3 · diálogo con el cliente",
    Nodo.N4: "N4 · control de suficiencia",
    Nodo.N5: "N5 · síntesis de requerimientos",
    Nodo.N6: "N6 · aprobación de requerimientos",
    Nodo.N7: "N7 · catálogo de arquitecturas",
    Nodo.N8: "N8 · diseño de la arquitectura",
    Nodo.N9: "N9 · aprobación de la especificación",
    Nodo.N10: "N10 · generación del módulo",
    Nodo.N11: "N11 · ejecución en el entorno aislado",
    Nodo.N12: "N12 · análisis estático",
    Nodo.N13: "N13 · criterios de calidad",
    Nodo.N14: "N14 · veredicto del tester",
    Nodo.N15: "N15 · decisión del ciclo de corrección",
    Nodo.N16: "N16 · plan de pruebas de aceptación",
    Nodo.N17: "N17 · aprobación final",
}
"""Nombre legible de cada nodo, para mostrar dónde está o dónde se detuvo una sesión."""

ACUSE_CONFIRMACION = (
    "Gracias. Reviso su respuesta al resumen: si lo confirma, redacto los requerimientos con lo "
    "conversado, lo que tarda unos segundos…"
)
"""Acuse de la respuesta al resumen. Vale si el cliente lo confirma, porque la síntesis que sigue
tarda de 6 a 16 s, y si lo corrige, porque el elicitador vuelve a resumir."""

ESPERAS = {
    "dialogo": "Espera la respuesta del cliente",
    "requerimientos": "Espera la aprobación de los requerimientos (N6)",
    "especificacion": "Espera la aprobación de la especificación de diseño (N9)",
    "final": "Espera la aprobación final del módulo (N17)",
}

LONGITUD_DETALLE_PRUEBA = 500
"""Caracteres del motivo de una prueba propia que no pasa, al mostrarla o sugerir observaciones."""


class ErrorOperacion(ValueError):
    """La operación no corresponde al estado de la sesión."""


class VistaSesion(BaseModel):
    """Lo que una interfaz muestra de una sesión.

    Attributes:
        pausa: Pausa en la que espera a una persona, si la hay.
        pendientes: Nodos por ejecutar sin pausa humana: la sesión se detuvo por una falla o
            porque el proceso se interrumpió.
        error: Error del último nodo que falló, si lo hay.
        confirma_resumen: La pregunta pendiente es el resumen que confirma el cliente; responderla
            cierra la elicitación y lanza la síntesis, que tarda varios segundos.
    """

    model_config = ConfigDict(frozen=True)

    id_sesion: str
    cliente: str
    proyecto: str
    fase: Fase
    creada: datetime
    pausa: Pausa | None
    pendientes: tuple[str, ...]
    error: str | None
    iteracion: int
    limite_iteraciones: int
    confirma_resumen: bool

    @property
    def detenida(self) -> bool:
        """Indica si la sesión espera que alguien la reanude, sin pausa humana pendiente."""
        return self.pausa is None and bool(self.pendientes)

    @property
    def terminada(self) -> bool:
        """Indica si la sesión llegó al final: validada, cerrada o terminada por el grafo."""
        return self.pausa is None and not self.pendientes

    def describir(self) -> str:
        """Estado de la sesión en lenguaje de negocio, para listas y encabezados."""
        if self.pausa is not None:
            if self.pausa.punto == "final" and self.pausa.datos.get("escalado"):
                return "Escalada: el tester no aprobó el módulo; espera la decisión de una persona"
            return ESPERAS[self.pausa.punto]
        if self.pendientes:
            nodos = ", ".join(NOMBRES_DE_NODO.get(n, n) for n in self.pendientes)
            return f"Detenida antes de {nodos}: hay que reanudarla"
        if self.fase is Fase.VALIDADO:
            return "Módulo validado"
        if self.fase is Fase.CERRADA:
            return "Cerrada sin módulo validado"
        if self.fase is Fase.REQUIERE_INTERVENCION:
            return "Requiere intervención humana: se agotaron las iteraciones de corrección"
        return f"Terminada en la fase {self.fase}"


class Operador:
    """Opera las sesiones de un grafo compilado con checkpointer."""

    def __init__(
        self,
        app: CompiledStateGraph,
        entorno: EntornoAislado | None = None,
        registro: RegistroPorSesion | None = None,
        tester: ConfiguracionTester | None = None,
    ) -> None:
        """Prepara el operador.

        Args:
            app: Grafo compilado con checkpointer.
            entorno: Entorno aislado de las pruebas propias en N17; si se omite, el configurado.
            registro: Traza de llamadas; si se indica, cada llamada queda con su sesión.
            tester: Tiempo límite de las pruebas; si se omite, el configurado.
        """
        self.app = app
        self.entorno = entorno or EntornoAislado()
        self.registro = registro
        self.tester = tester or ConfiguracionTester()

    def _en_sesion(self, id_sesion: str) -> AbstractContextManager[None]:
        return self.registro.en_sesion(id_sesion) if self.registro else nullcontext()

    def _avanzar(self, id_sesion: str, respuesta: str | dict[str, Any] | None) -> Avance:
        with self._en_sesion(id_sesion):
            return avanzar(self.app, id_sesion, respuesta)

    def _pausa(self, id_sesion: str, puntos: tuple[str, ...]) -> Pausa:
        pausa = pausa_pendiente(self.app, id_sesion)
        if pausa is None or pausa.punto not in puntos:
            actual = pausa.punto if pausa else "ninguna"
            raise ErrorOperacion(
                f"La sesión {id_sesion} no espera {' ni '.join(puntos)}; pausa actual: {actual}."
            )
        return pausa

    # Flujo ----------------------------------------------------------------------------------

    def iniciar(
        self, cliente: str, proyecto: str, necesidad: str, id_sesion: str | None = None
    ) -> str:
        """Abre una sesión con la necesidad del cliente y la lleva hasta la primera pregunta.

        Args:
            cliente: Nombre del cliente.
            proyecto: Proyecto al que pertenecen los requerimientos.
            necesidad: Primera intervención del cliente.
            id_sesion: Identificador a usar; si se omite, se genera. Darlo permite a la interfaz
                conocer la sesión aunque un nodo falle antes de la primera pregunta.

        Returns:
            El identificador de la sesión. Si un nodo falla, la excepción se propaga y la sesión
            queda detenida, para reanudarla con `reanudar`.

        Raises:
            ErrorOperacion: Si falta algún dato.
        """
        if not all(texto.strip() for texto in (cliente, proyecto, necesidad)):
            raise ErrorOperacion("El cliente, el proyecto y la necesidad son obligatorios.")
        id_sesion = id_sesion or str(uuid.uuid4())
        with self._en_sesion(id_sesion):
            iniciar_sesion(self.app, cliente.strip(), proyecto.strip(), necesidad, id_sesion)
        return id_sesion

    def responder(self, id_sesion: str, texto: str) -> Avance:
        """Entrega la respuesta del cliente a la pregunta pendiente (N3).

        Args:
            id_sesion: Identificador de la sesión.
            texto: Respuesta del cliente.

        Returns:
            El avance hasta la siguiente pausa.

        Raises:
            ErrorOperacion: Si la sesión no espera una respuesta del cliente.
        """
        self._pausa(id_sesion, ("dialogo",))
        return self._avanzar(id_sesion, texto)

    def decidir(
        self,
        id_sesion: str,
        decision: Decision,
        revisor: str,
        observaciones: str | None = None,
        pruebas_propias: PruebasPropias | None = None,
        destino: Destino | None = None,
    ) -> Avance:
        """Registra la decisión de la persona en el punto de control pendiente.

        Una decisión que el grafo no admite (un rechazo sin observaciones o una aprobación
        bloqueada) vuelve a pausar con un aviso en `Pausa.datos["aviso"]`.

        Args:
            id_sesion: Identificador de la sesión.
            decision: Aprobar o rechazar.
            revisor: Nombre de quien decide.
            observaciones: Qué debe cambiar el agente anterior; obligatorias al rechazar.
            pruebas_propias: Pruebas que la persona ejecutó en N17 (RF-38).
            destino: Solo al rechazar en N17: el desarrollador (por defecto) o el arquitecto.

        Returns:
            El avance hasta la siguiente pausa o el final.

        Raises:
            ErrorOperacion: Si la sesión no espera una decisión.
        """
        self._pausa(id_sesion, PUNTOS_DE_CONTROL)
        respuesta: dict[str, Any] = {"decision": decision.value, "revisor": revisor.strip()}
        if observaciones and observaciones.strip():
            respuesta["observaciones"] = observaciones.strip()
        if pruebas_propias is not None:
            respuesta["pruebas_propias"] = pruebas_propias.model_dump(mode="json")
        if destino is not None:
            respuesta["destino"] = destino.value
        return self._avanzar(id_sesion, respuesta)

    def cerrar(self, id_sesion: str, revisor: str, motivo: str) -> None:
        """Cierra una sesión sin módulo validado, desde una pausa o detenida por una falla.

        Es la salida que siempre existe: el cierre se aplica como si N17 lo hubiera decidido,
        lo que termina el grafo y descarta la pausa o el nodo pendiente. Queda registrado en
        `Sesion.cierre` (RF-33).

        Args:
            id_sesion: Identificador de la sesión.
            revisor: Quién la cierra.
            motivo: Por qué.

        Raises:
            ErrorOperacion: Si la sesión ya terminó, o si falta el revisor o el motivo.
        """
        vista = self.vista(id_sesion)
        if vista.terminada:
            raise ErrorOperacion(f"La sesión {id_sesion} ya terminó: {vista.describir().lower()}.")
        if not revisor.strip() or not motivo.strip():
            raise ErrorOperacion("Para cerrar la sesión se necesitan el revisor y el motivo.")
        desde = (
            ESPERAS[vista.pausa.punto]
            if vista.pausa
            else "Detenida antes de "
            + ", ".join(NOMBRES_DE_NODO.get(n, n) for n in vista.pendientes)
        )
        sesion = self.estado(id_sesion)["sesion"]
        cierre = CierreSesion(
            revisor=revisor.strip(), motivo=motivo.strip(), desde=desde, fecha=datetime.now(UTC)
        )
        cerrada = sesion.model_copy(update={"fase": Fase.CERRADA, "cierre": cierre})
        with self._en_sesion(id_sesion):
            self.app.update_state(
                configuracion_hilo(id_sesion), {"sesion": cerrada}, as_node=Nodo.N17
            )

    def reanudar(self, id_sesion: str) -> Avance:
        """Reanuda una sesión detenida por una falla o por la interrupción del proceso (RF-28).

        Args:
            id_sesion: Identificador de la sesión.

        Returns:
            El avance hasta la siguiente pausa o el final.

        Raises:
            ErrorOperacion: Si la sesión no está detenida.
        """
        if not self.vista(id_sesion).detenida:
            raise ErrorOperacion(f"La sesión {id_sesion} no está detenida.")
        return self._avanzar(id_sesion, None)

    # Consulta -------------------------------------------------------------------------------

    def estado(self, id_sesion: str) -> EstadoGrafo:
        """Devuelve el estado vigente de una sesión.

        Raises:
            ErrorOperacion: Si la sesión no existe.
        """
        valores = self.app.get_state(configuracion_hilo(id_sesion)).values
        if "sesion" not in valores:
            raise ErrorOperacion(f"No existe la sesión {id_sesion}.")
        return valores

    def vista(self, id_sesion: str) -> VistaSesion:
        """Resume el estado de una sesión para mostrarlo.

        Raises:
            ErrorOperacion: Si la sesión no existe.
        """
        instantanea = self.app.get_state(configuracion_hilo(id_sesion))
        valores = instantanea.values
        if "sesion" not in valores:
            raise ErrorOperacion(f"No existe la sesión {id_sesion}.")
        sesion, control, conversacion = (
            valores["sesion"],
            valores["control"],
            valores["conversacion"],
        )
        pausa = pausa_pendiente(self.app, id_sesion)
        errores = [str(tarea.error) for tarea in instantanea.tasks if tarea.error is not None]
        return VistaSesion(
            id_sesion=id_sesion,
            cliente=sesion.cliente,
            proyecto=sesion.proyecto,
            fase=sesion.fase,
            creada=sesion.creada,
            pausa=pausa,
            pendientes=tuple(instantanea.next) if pausa is None else (),
            error=errores[-1] if errores else None,
            iteracion=control.iteracion,
            limite_iteraciones=control.limite_iteraciones,
            confirma_resumen=(
                pausa is not None
                and pausa.punto == "dialogo"
                and conversacion.registro.por_preguntar == ["confirmacion"]
            ),
        )

    def sesiones(self) -> list[VistaSesion]:
        """Lista las sesiones guardadas, de la más reciente a la más antigua.

        Omite los hilos sin estado de sesión, como uno que se cayó antes de abrirse.
        """
        vistas = []
        for id_sesion in identificadores_de_sesion(self.app.checkpointer):
            try:
                vistas.append(self.vista(id_sesion))
            except ErrorOperacion:
                continue
        return vistas

    def historial(self, id_sesion: str) -> list[tuple[VersionCodigo, Validacion]]:
        """Cada versión dictaminada del módulo con su validación (RF-33)."""
        return validaciones(self.app, id_sesion)

    def trazabilidad(self, id_sesion: str) -> str:
        """Cadena completa de artefactos de la sesión, en Markdown (RF-33)."""
        return trazabilidad_md(self.estado(id_sesion), self.historial(id_sesion))

    def exportar(self, id_sesion: str) -> dict[str, str]:
        """Entregables del módulo validado, por ruta relativa (RF-35).

        Raises:
            ErrorExportacion: Si la sesión no terminó con un módulo validado.
        """
        return paquete_del_modulo(
            self.estado(id_sesion), self.historial(id_sesion), requisitos_del_entorno()
        )

    # Pruebas propias en N17 -----------------------------------------------------------------

    def probar_propias(self, id_sesion: str, archivos: Mapping[str, str]) -> PruebasPropias:
        """Ejecuta las pruebas de la persona contra la versión vigente, en el entorno aislado.

        Se corren junto con las pruebas del módulo, pero el resultado solo incluye las de la
        persona: son su evidencia para decidir en N17 (RF-38).

        Args:
            id_sesion: Identificador de la sesión, pausada en la aprobación final.
            archivos: Contenido de cada archivo de prueba por su ruta, `tests/test_*.py`.

        Returns:
            Los archivos y su resultado, para registrarlos con la decisión.

        Raises:
            ErrorOperacion: Si la sesión no está en N17, o si una ruta no es válida o pisa un
                archivo del módulo.
            ErrorEntornoAislado: Si Docker no responde o la imagen no existe.
        """
        self._pausa(id_sesion, ("final",))
        version = self.estado(id_sesion)["codigo"].vigente
        if version is None:
            raise ErrorOperacion("No hay una versión del módulo contra la cual probar.")
        if invalidas := sorted(r for r in archivos if not RUTA_PRUEBA_PROPIA.fullmatch(r)):
            raise ErrorOperacion(f"Las pruebas propias van en tests/test_*.py: {invalidas}")
        if repetidas := sorted(set(archivos) & set(version.archivos)):
            raise ErrorOperacion(f"Estas rutas ya son del módulo; use otro nombre: {repetidas}")
        corrida = self.entorno.probar(
            {**version.archivos, **archivos}, self.tester.tiempo_limite_pruebas_s
        )
        propias = set(archivos)
        ejecucion = EjecucionPruebas(
            pruebas=tuple(p for p in pruebas_ejecutadas(corrida) if p.archivo in propias),
            errores_recoleccion=tuple(
                error
                for error in corrida.errores_recoleccion
                if error.split(":", 1)[0] in propias or not error.startswith("tests/")
            ),
            vencido=corrida.ejecucion.vencido,
            duracion_ms=corrida.ejecucion.duracion_ms,
            salida=corrida.salida_pytest,
        )
        return PruebasPropias(archivos=dict(archivos), ejecucion=ejecucion)


def observaciones_de_pruebas(pruebas: PruebasPropias) -> str:
    """Observaciones con las pruebas propias que fallaron, para precargar un rechazo en N17.

    Args:
        pruebas: Pruebas propias ejecutadas.

    Returns:
        Una línea por prueba que no pasó o archivo que no se recolectó; vacío si todas pasan.
    """
    lineas = [
        f"La prueba propia {prueba.identificador} no pasa ({prueba.resultado}): "
        f"{detalle_de_prueba(prueba.mensaje)}"
        for prueba in pruebas.ejecucion.pruebas
        if prueba.resultado is not ResultadoPrueba.PASO
    ]
    lineas += [
        f"Archivo de pruebas propias sin recolectar: {detalle_de_recoleccion(error)}"
        for error in pruebas.ejecucion.errores_recoleccion
    ]
    return "\n".join(lineas)


def detalle_de_prueba(mensaje: str) -> str:
    """Motivo, en una línea, de que una prueba no pase.

    Args:
        mensaje: Reporte de pytest de la prueba.

    Returns:
        Las líneas con que pytest explica el error, recortadas.
    """
    return detalle_de_falla(mensaje, LONGITUD_DETALLE_PRUEBA)


def detalle_de_recoleccion(error: str) -> str:
    """Archivo y motivo de un error de recolección de pytest, en una línea.

    Args:
        error: Error de recolección, `ruta: reporte`, o el motivo de que no haya resultado.

    Returns:
        `ruta · motivo` si el error es de un archivo de pruebas; si no, solo el motivo.
    """
    ruta, _, reporte = error.partition(": ")
    if not ruta.startswith("tests/"):
        return detalle_de_prueba(error)
    return f"{ruta} · {detalle_de_prueba(reporte)}"


@contextmanager
def abrir_operador(configuracion: ConfiguracionInterfaces | None = None) -> Iterator[Operador]:
    """Abre el operador del sistema completo: base de conocimiento, puntos de control y agentes.

    Requiere `docker compose up -d --wait`, el corpus ingerido, la imagen del entorno aislado y
    el archivo .env. Cada llamada a un modelo queda en la traza con su sesión. Las conexiones a
    PostgreSQL van por pools que se reconectan, para que un reinicio de la base no detenga una
    web abierta durante horas.

    Args:
        configuracion: Traza y carpeta de trabajo; si se omite, se lee del entorno.

    Yields:
        El operador, listo para la consola o la web.
    """
    configuracion = configuracion or ConfiguracionInterfaces()
    registro = RegistroPorSesion(configuracion.traza_llamadas)
    entorno = EntornoAislado()
    with (
        abrir_pool(aplicacion="multiagente-conocimiento") as pool,
        abrir_checkpointer_compartido() as puntos,
    ):
        servicios = crear_servicios(ConexionDePool(pool), registro, entorno=entorno)
        app = construir_grafo(servicios).compile(checkpointer=puntos)
        yield Operador(app, entorno, registro)
