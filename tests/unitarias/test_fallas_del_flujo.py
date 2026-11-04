"""Matriz de fallas: ninguna falla del sistema deja una sesión atascada.

Cada falla debe terminar en un reintento que pueda funcionar (reanudar) o en una decisión humana
con salida. Los servicios simulados fallan en un nodo, una vez o siempre, con un error de salida
del modelo (determinístico) o de infraestructura (transitorio).
"""

from collections import Counter

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from multiagente.core.configuracion import ConfiguracionOrquestador
from multiagente.interfaces.operacion import ErrorOperacion, Operador
from multiagente.llm.invocador import ErrorValidacionSalida
from multiagente.orquestador.estado import Decision, Destino, Fase, Veredicto
from multiagente.orquestador.grafo import PREGUNTA_REINTENTO, construir_grafo
from multiagente.orquestador.simulacion import ServiciosSimulados, guion_completo
from multiagente.persistencia.puntos_control import serializador

SIEMPRE = 10**6


class ErrorDeRed(ConnectionError):
    """Falla transitoria de infraestructura: un servicio no responde."""


class SimulacionConFallas(ServiciosSimulados):
    """Servicios simulados que fallan en los métodos indicados, una cantidad de veces.

    Attributes:
        fallas: Veces que falla cada método antes de funcionar; `SIEMPRE` para una falla
            persistente. La clave `corregir` solo cuenta las generaciones con versión previa.
        error: Excepción con que fallan.
        vistas: Respuestas nuevas del cliente que recibió el diálogo, en orden.
    """

    def __init__(
        self,
        fallas: dict[str, int],
        error: type[Exception] = ErrorValidacionSalida,
        fallos_veredicto: int = 0,
    ):
        super().__init__(fallos_veredicto=fallos_veredicto)
        self.fallas = Counter(fallas)
        self.error = error
        self.vistas: list[str | None] = []

    def _quizas_fallar(self, metodo: str) -> None:
        if self.fallas[metodo] > 0:
            self.fallas[metodo] -= 1
            if self.error is ErrorValidacionSalida:
                raise ErrorValidacionSalida([f"Falla simulada de {metodo}"])
            raise self.error(f"Falla simulada de {metodo}")

    def dialogar(self, conversacion, contexto):
        if conversacion.respuesta_nueva is not None and conversacion.turnos_cliente >= 2:
            self.vistas.append(conversacion.respuesta_nueva)
            self._quizas_fallar("dialogar")
        return super().dialogar(conversacion, contexto)

    def sintetizar(self, conversacion, contexto, previos, proyecto):
        self._quizas_fallar("sintetizar")
        return super().sintetizar(conversacion, contexto, previos, proyecto)

    def disenar(self, requerimientos, contexto, previa):
        self._quizas_fallar("disenar")
        return super().disenar(requerimientos, contexto, previa)

    def generar(self, requerimientos, especificacion, validacion, previa, rediseno=None):
        self._quizas_fallar("generar")
        if previa is not None:
            self._quizas_fallar("corregir")
        return super().generar(requerimientos, especificacion, validacion, previa, rediseno)

    def ejecutar(self, version, especificacion):
        self._quizas_fallar("ejecutar")
        return super().ejecutar(version, especificacion)


def operador(simulacion: ServiciosSimulados) -> Operador:
    app = construir_grafo(
        simulacion.como_servicios(), ConfiguracionOrquestador(_env_file=None)
    ).compile(checkpointer=InMemorySaver(serde=serializador()))
    return Operador(app)


def abrir(op: Operador) -> str:
    guion = guion_completo()
    return op.iniciar("Oficina", guion.proyecto, guion.necesidad)


def hasta(op: Operador, id_sesion: str, punto: str) -> None:
    """Responde el diálogo y aprueba los puntos de control hasta la pausa indicada."""
    respuestas = guion_completo().respuestas_cliente
    while (pausa := op.vista(id_sesion).pausa).punto != punto:
        if pausa.punto == "dialogo":
            op.responder(id_sesion, respuestas.pop(0))
        else:
            op.decidir(id_sesion, Decision.APROBADO, "Equipo")


# N3: falla al procesar la respuesta del cliente --------------------------------------------


@pytest.mark.parametrize("error", [ErrorValidacionSalida, ErrorDeRed])
def test_n3_vuelve_a_preguntar_y_procesa_la_respuesta_nueva(error):
    simulacion = SimulacionConFallas({"dialogar": 1}, error)
    op = operador(simulacion)
    id_sesion = abrir(op)

    avance = op.responder(id_sesion, "RESPUESTA ORIGINAL")
    assert avance.pausa.punto == "dialogo"
    assert avance.pausa.datos["pregunta"] == PREGUNTA_REINTENTO
    assert op.vista(id_sesion).error is None

    op.responder(id_sesion, "RESPUESTA NUEVA")
    # LangGraph no repite la respuesta que falló: el diálogo recibe la nueva.
    assert simulacion.vistas == ["RESPUESTA ORIGINAL", "RESPUESTA NUEVA"]
    textos = [turno.texto for turno in op.estado(id_sesion)["conversacion"].turnos]
    assert textos[-4:-1] == ["RESPUESTA ORIGINAL", PREGUNTA_REINTENTO, "RESPUESTA NUEVA"]


def test_n3_con_falla_persistente_sigue_preguntando_sin_atascarse():
    op = operador(SimulacionConFallas({"dialogar": SIEMPRE}))
    id_sesion = abrir(op)
    for intento in range(3):
        avance = op.responder(id_sesion, f"Respuesta {intento}")
        assert avance.pausa.punto == "dialogo"
        assert avance.pausa.datos["pregunta"] == PREGUNTA_REINTENTO


# Infraestructura: la sesión queda detenida y se reanuda -------------------------------------


def test_una_falla_de_infraestructura_se_reanuda():
    simulacion = SimulacionConFallas({"ejecutar": 1}, ErrorDeRed)
    op = operador(simulacion)
    id_sesion = abrir(op)
    guion = guion_completo()
    for respuesta in guion.respuestas_cliente[:7]:
        op.responder(id_sesion, respuesta)
    op.decidir(id_sesion, Decision.APROBADO, "Analista")
    with pytest.raises(ErrorDeRed):
        op.decidir(id_sesion, Decision.APROBADO, "Arquitecto")

    vista = op.vista(id_sesion)
    assert vista.detenida and "Falla simulada de ejecutar" in vista.error
    assert op.reanudar(id_sesion).pausa.punto == "final"


# Fallas del modelo que se repiten: terminan en una decisión humana ----------------------


def test_n5_sin_sintesis_escala_al_analista_con_la_aprobacion_bloqueada():
    op = operador(SimulacionConFallas({"sintetizar": SIEMPRE}))
    id_sesion = abrir(op)
    hasta(op, id_sesion, "requerimientos")

    datos = op.vista(id_sesion).pausa.datos
    assert datos["requerimientos"] == []
    assert datos["defectos"][0].startswith("La síntesis falló: Falla simulada de sintetizar")
    avance = op.decidir(id_sesion, Decision.APROBADO, "Analista")
    assert avance.pausa.punto == "requerimientos"
    assert "No hay requerimientos que aprobar" in avance.pausa.datos["aviso"]
    # El rechazo devuelve el flujo al diálogo: hay salida.
    avance = op.decidir(id_sesion, Decision.RECHAZADO, "Analista", "Falta precisar la regla")
    assert avance.pausa.punto == "dialogo"


def test_n5_que_falla_una_vez_se_corrige_sola():
    op = operador(SimulacionConFallas({"sintetizar": 1}))
    id_sesion = abrir(op)
    hasta(op, id_sesion, "requerimientos")
    datos = op.vista(id_sesion).pausa.datos
    assert datos["requerimientos"] and datos["defectos"] == []


def test_n8_sin_diseno_escala_al_arquitecto_humano():
    op = operador(SimulacionConFallas({"disenar": SIEMPRE}))
    id_sesion = abrir(op)
    hasta(op, id_sesion, "especificacion")

    datos = op.vista(id_sesion).pausa.datos
    assert datos["especificacion"] is None
    assert datos["errores"][0].startswith("El diseño falló: Falla simulada de disenar")
    avance = op.decidir(id_sesion, Decision.APROBADO, "Arquitecto")
    assert "no puede aprobarse" in avance.pausa.datos["aviso"]


def test_n8_que_falla_una_vez_se_corrige_sola():
    op = operador(SimulacionConFallas({"disenar": 1}))
    id_sesion = abrir(op)
    hasta(op, id_sesion, "especificacion")
    datos = op.vista(id_sesion).pausa.datos
    assert datos["especificacion"] is not None and datos["errores"] == []


def test_n10_que_falla_una_vez_cuenta_la_iteracion_y_sigue():
    op = operador(SimulacionConFallas({"generar": 1}))
    id_sesion = abrir(op)
    hasta(op, id_sesion, "final")
    vista = op.vista(id_sesion)
    assert vista.iteracion == 2
    assert vista.pausa.datos["version"] == 1
    # La generación fallida cuenta como iteración, pero no es una versión del historial.
    assert [version.numero for version, _ in op.historial(id_sesion)] == [1]
    assert "- Versión 1 ·" in op.trazabilidad(id_sesion)


def test_n10_que_falla_al_corregir_no_repite_versiones_en_el_historial():
    # La v1 se rechaza, su corrección falla y la siguiente se aprueba en la iteración 3.
    op = operador(SimulacionConFallas({"corregir": 1}, fallos_veredicto=1))
    id_sesion = abrir(op)
    hasta(op, id_sesion, "final")
    assert op.vista(id_sesion).iteracion == 3
    historial = op.historial(id_sesion)
    assert [(version.numero, validacion.veredicto) for version, validacion in historial] == [
        (1, Veredicto.RECHAZADO),
        (2, Veredicto.APROBADO),
    ]


def test_n10_sin_version_agota_el_ciclo_sin_ejecutar_nada():
    simulacion = SimulacionConFallas({"generar": SIEMPRE})
    op = operador(simulacion)
    id_sesion = abrir(op)
    hasta(op, id_sesion, "especificacion")
    op.decidir(id_sesion, Decision.APROBADO, "Arquitecto")

    estado = op.estado(id_sesion)
    assert estado["codigo"].versiones == ()
    assert estado["control"].iteracion == 3
    assert estado["validacion"].reporte.startswith("# La generación del módulo falló")
    assert simulacion.llamadas["ejecutar"] == 0
    # Escala a una persona en N17, aunque no haya versión: la sesión tiene salida.
    datos = op.vista(id_sesion).pausa.datos
    assert datos["escalado"] is True
    assert datos["version"] is None and datos["archivos"] == []
    assert op.historial(id_sesion) == []
    assert "Aún no hay versiones dictaminadas." in op.trazabilidad(id_sesion)
    avance = op.decidir(
        id_sesion, Decision.RECHAZADO, "Revisor", "Simplifica el diseño", destino=Destino.ARQUITECTO
    )
    assert avance.pausa.punto == "especificacion"


# Cerrar: la salida que siempre existe ----------------------------------------------------


@pytest.mark.parametrize("punto", ["dialogo", "requerimientos", "especificacion"])
def test_se_cierra_desde_cualquier_pausa(punto):
    op = operador(SimulacionConFallas({}))
    id_sesion = abrir(op)
    hasta(op, id_sesion, punto)
    op.cerrar(id_sesion, "Laura", "El cliente desistió")

    vista = op.vista(id_sesion)
    assert vista.fase is Fase.CERRADA and vista.pausa is None and not vista.pendientes
    cierre = op.estado(id_sesion)["sesion"].cierre
    assert (cierre.revisor, cierre.motivo) == ("Laura", "El cliente desistió")
    assert cierre.desde.startswith("Espera")
    assert "Cerrada por Laura" in op.trazabilidad(id_sesion)
    with pytest.raises(ErrorOperacion, match="ya terminó"):
        op.cerrar(id_sesion, "Laura", "Otra vez")


def test_se_cierra_una_sesion_escalada_en_n17():
    op = operador(SimulacionConFallas({"generar": SIEMPRE}))
    id_sesion = abrir(op)
    hasta(op, id_sesion, "especificacion")
    op.decidir(id_sesion, Decision.APROBADO, "Arquitecto")
    assert op.vista(id_sesion).pausa.datos["escalado"]
    op.cerrar(id_sesion, "Revisor", "El catálogo no cubre la capacidad pedida")
    assert op.vista(id_sesion).describir() == "Cerrada sin módulo validado"


def test_se_cierra_una_sesion_detenida_por_infraestructura():
    op = operador(SimulacionConFallas({"ejecutar": SIEMPRE}, ErrorDeRed))
    id_sesion = abrir(op)
    hasta(op, id_sesion, "especificacion")
    with pytest.raises(ErrorDeRed):
        op.decidir(id_sesion, Decision.APROBADO, "Arquitecto")
    assert op.vista(id_sesion).detenida

    op.cerrar(id_sesion, "Julián", "Docker no está disponible")
    vista = op.vista(id_sesion)
    assert vista.fase is Fase.CERRADA and not vista.detenida
    assert "N11" in op.estado(id_sesion)["sesion"].cierre.desde


def test_cerrar_exige_revisor_y_motivo():
    op = operador(SimulacionConFallas({}))
    id_sesion = abrir(op)
    with pytest.raises(ErrorOperacion, match="revisor y el motivo"):
        op.cerrar(id_sesion, "Laura", "  ")
