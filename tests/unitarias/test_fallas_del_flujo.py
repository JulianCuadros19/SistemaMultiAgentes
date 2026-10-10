"""Matriz de fallas: ninguna falla del sistema deja una sesión atascada.

Cada falla debe terminar en un reintento que pueda funcionar (reanudar) o en una decisión humana
con salida. Los servicios simulados fallan en un nodo, una vez o siempre, con un error de salida
del modelo (determinístico) o de infraestructura (transitorio).
"""

from collections import Counter

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from multiagente.core.configuracion import ConfiguracionOrquestador
from multiagente.interfaces.operacion import Operador
from multiagente.llm.invocador import ErrorValidacionSalida
from multiagente.orquestador.estado import Decision
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
            persistente.
        error: Excepción con que fallan.
        vistas: Respuestas nuevas del cliente que recibió el diálogo, en orden.
    """

    def __init__(self, fallas: dict[str, int], error: type[Exception] = ErrorValidacionSalida):
        super().__init__(fallos_veredicto=0)
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
