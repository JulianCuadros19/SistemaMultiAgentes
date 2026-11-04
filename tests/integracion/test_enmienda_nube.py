"""Condición de terminado de la fase 6 del paso 12: una regla nueva de N17 llega al módulo.

Con el caso `evaluacion/casos/con-recorridos/desarrollo-avaluo.json`, un elicitador y un
arquitecto fijos entregan los requerimientos y el diseño aprobados. El desarrollador y el tester
son reales, y del elicitador también lo son la enmienda (N5) y la verificación de calidad (N6).

En N17, la persona pide una enmienda con una regla que el cliente no había dicho y que cabe en las
interfaces del diseño: el redondeo de los avalúos al múltiplo de mil. La sesión debe recorrer
N17 → N5 → N6 → N16 → N10 → N17, sin pasar por N7 a N9 (ADR-0015), y:
- el RF-01 sube de versión con la regla y su escenario;
- el plan de pruebas incluye el caso nuevo;
- la prueba nueva pasa en la versión corregida, que el tester aprueba;
- la exportación refleja la enmienda.

Cuesta unos 0,3 USD y requiere el archivo .env, los servicios `db` y `embeddings` y la imagen del
entorno aislado:
`pytest -m "nube and embeddings and sandbox" tests/integracion/test_enmienda_nube.py`.
"""

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from multiagente.agentes.desarrollador.servicio import crear_agente_desarrollador
from multiagente.agentes.elicitador.calidad import normalizar
from multiagente.agentes.elicitador.servicio import AgenteElicitador, crear_agente_elicitador
from multiagente.agentes.tester.reglas import cargar_reglas_calidad, estilo_bloqueante
from multiagente.agentes.tester.servicio import crear_agente_tester
from multiagente.core.configuracion import (
    ConfiguracionAzureOpenAI,
    ConfiguracionOrquestador,
    ConfiguracionTester,
)
from multiagente.interfaces.casos import cargar_caso_desarrollo
from multiagente.interfaces.cliente_simulado import RAIZ_EVALUACION
from multiagente.interfaces.documentos import paquete_del_modulo
from multiagente.llm.cliente import crear_cliente
from multiagente.llm.traza import RegistroEnMemoria
from multiagente.orquestador.ejecucion import (
    avanzar,
    configuracion_hilo,
    iniciar_sesion,
    validaciones,
)
from multiagente.orquestador.estado import (
    Conversacion,
    Fase,
    Requerimientos,
    ResultadoPrueba,
    Veredicto,
)
from multiagente.orquestador.grafo import Nodo, construir_grafo
from multiagente.orquestador.servicios import Servicios, Sintesis, VerificacionCalidad
from multiagente.orquestador.simulacion import ArquitectoFijo, ElicitadorFijo, aprobar, rechazar
from multiagente.persistencia.puntos_control import serializador
from multiagente.sandbox.requisitos import versiones_probadas

pytestmark = [pytest.mark.nube, pytest.mark.embeddings, pytest.mark.sandbox]

CASO = RAIZ_EVALUACION / "casos" / "con-recorridos" / "desarrollo-avaluo.json"
ENMIENDA = (
    "Regla nueva del cliente: el avalúo del terreno y el avalúo de la construcción se redondean, "
    "cada uno, al múltiplo de mil pesos más cercano, y el avalúo total es la suma de los dos ya "
    "redondeados; las fracciones de 500 pesos o más suben al mil siguiente. Por ejemplo, un "
    "predio sin construcción con 120,5 m² de terreno a 415.300 pesos por m² tiene un avalúo del "
    "terreno de 50.044.000 pesos."
)
"""La regla que la persona descubre en N17: cambia el cálculo, pero no las interfaces."""


@dataclass
class ElicitadorFijoQueEnmienda(ElicitadorFijo):
    """Elicitador fijo cuya enmienda (N5) y verificación de calidad (N6) son las reales."""

    real: AgenteElicitador

    def enmendar(
        self, conversacion: Conversacion, requerimientos: Requerimientos, proyecto: str
    ) -> Sintesis:
        """Enmienda con el modelo real (N5)."""
        return self.real.enmendar(conversacion, requerimientos, proyecto)

    def verificar_calidad(self, requerimientos: Requerimientos) -> VerificacionCalidad:
        """Verifica la calidad con el RF-07 real (N6)."""
        return self.real.verificar_calidad(requerimientos)


def test_una_regla_nueva_de_n17_entra_a_los_requerimientos_y_al_modulo(
    base_real, vectorizador, entorno_aislado, caplog
):
    caplog.set_level(logging.WARNING, logger="multiagente.llm.invocador")
    caso = cargar_caso_desarrollo(CASO)
    registro = RegistroEnMemoria()
    cliente = crear_cliente(ConfiguracionAzureOpenAI())
    servicios = Servicios(
        elicitador=ElicitadorFijoQueEnmienda(
            caso.sintesis, crear_agente_elicitador(base_real, registro, cliente, vectorizador)
        ),
        arquitecto=ArquitectoFijo(caso.diseno),
        desarrollador=crear_agente_desarrollador(
            registro,
            cliente,
            estilo_bloqueante(
                cargar_reglas_calidad(), ConfiguracionTester().umbral_hallazgos_media
            ),
        ),
        tester=crear_agente_tester(base_real, registro, cliente, vectorizador, entorno_aislado),
    )
    app = construir_grafo(servicios, ConfiguracionOrquestador(_env_file=None)).compile(
        checkpointer=InMemorySaver(serde=serializador())
    )
    id_sesion, _ = iniciar_sesion(app, caso.cliente, caso.proyecto, caso.necesidad)
    avanzar(app, id_sesion, aprobar("Analista"))
    avance = avanzar(app, id_sesion, aprobar("Arquitecto"))
    assert avance.pausa is not None and avance.pausa.punto == "final", avance
    antes = len(registro.llamadas)
    version_previa = avance.pausa.datos["version"]
    print(
        f"\nAntes de la enmienda: versión {version_previa} · veredicto "
        f"{avance.pausa.datos['veredicto']} · escalada {avance.pausa.datos['escalado']}"
    )

    # N17 → N5 → N6: el elicitador enmienda y el analista revisa la enmienda.
    avance = avanzar(app, id_sesion, rechazar(ENMIENDA, "Revisora") | {"destino": "requerimientos"})
    nodos = list(avance.nodos)
    assert avance.pausa is not None and avance.pausa.punto == "requerimientos", avance
    enmienda = avance.pausa.datos["enmienda"]
    rf_01 = next(
        r for r in avance.pausa.datos["requerimientos"] if r["id_requerimiento"] == "RF-01"
    )
    print(f"Defectos en N6: {avance.pausa.datos['defectos']}")
    print(f"RF-01 v{rf_01['version']} · regla: {rf_01['descripcion']['regla_negocio']}")
    for escenario in rf_01["criterios_aceptacion"]:
        print(
            f"  {escenario['id']} · {escenario['nombre']}: DADO QUE {escenario['dado_que']}, "
            f"CUANDO {escenario['cuando']}, ENTONCES {escenario['entonces']}"
        )
    assert enmienda["requerimientos"] == {"RF-01": rf_01["version"]}
    assert rf_01["version"] != "0.1"
    regla = normalizar(rf_01["descripcion"]["regla_negocio"])
    assert "redonde" in regla and "mil" in regla
    ids = [escenario["id"] for escenario in rf_01["criterios_aceptacion"]]
    assert ids[:3] == ["ESC-01", "ESC-02", "ESC-03"] and len(ids) > 3
    nuevos = ids[3:]

    # N6 → N16 → N10 … N17: el desarrollador corrige con la enmienda y el mismo diseño.
    avance = avanzar(app, id_sesion, aprobar("Analista"))
    nodos += avance.nodos
    assert avance.pausa is not None and avance.pausa.punto == "final", avance
    assert not {Nodo.N7, Nodo.N8, Nodo.N9} & set(nodos)
    assert nodos[0] == Nodo.N17 and Nodo.N16 in nodos and Nodo.N10 in nodos
    estado = app.get_state(configuracion_hilo(id_sesion)).values
    validacion = estado["validacion"]
    version = estado["codigo"].vigente
    plan = [caso_prueba.id for caso_prueba in validacion.plan_pruebas]
    pruebas = validacion.ejecucion.pruebas
    for linea in validacion.retroalimentacion:
        print(f"Retroalimentación pendiente: {linea[:300]}")
    print(f"Versión {version.numero} · veredicto {validacion.veredicto} · plan {plan}")
    for prueba in pruebas:
        print(f"  {prueba.resultado:7} {prueba.identificador}")
    for rechazo in caplog.messages:
        print(f"Reintento: {rechazo[:600]}")
    gasto: defaultdict[str, Decimal] = defaultdict(Decimal)
    for llamada in registro.llamadas[antes:]:
        gasto[llamada.nodo] += llamada.costo_usd
        print(
            f"{llamada.nodo} {llamada.latencia_ms / 1000:6.1f} s · {llamada.prompt} · entrada "
            f"{llamada.consumo.entrada} · salida {llamada.consumo.salida} · USD "
            f"{llamada.costo_usd:.4f}{' · ' + llamada.error if llamada.error else ''}"
        )
    total = sum((llamada.costo_usd for llamada in registro.llamadas), Decimal(0))
    print(
        f"Llamadas por nodo: {dict(Counter(llamada.nodo for llamada in registro.llamadas))} · "
        f"enmienda en adelante: {dict(gasto)} · total USD {total:.4f}"
    )

    # El plan incluye el caso nuevo, la versión corregida lo prueba y el tester la aprueba.
    assert [f"CP-RF-01-{id_escenario}" in plan for id_escenario in nuevos] == [True] * len(nuevos)
    assert version.numero > version_previa
    assert version.defectos_atendidos[0] == ENMIENDA
    assert avance.pausa.datos["escalado"] is False, validacion.reporte
    assert validacion.veredicto is Veredicto.APROBADO, validacion.reporte
    for id_escenario in nuevos:
        prefijo = f"test_rf_01_{id_escenario.lower().replace('-', '_')}"
        de_escenario = [p for p in pruebas if p.nombre.startswith(prefijo)]
        assert de_escenario, f"Sin prueba de {id_escenario}"
        assert all(p.resultado is ResultadoPrueba.PASO for p in de_escenario), de_escenario
    assert avance.pausa.datos["iteracion"] >= 1

    # La exportación refleja la enmienda.
    final = avanzar(app, id_sesion, aprobar("Revisora"))
    assert final.fase is Fase.VALIDADO
    estado = app.get_state(configuracion_hilo(id_sesion)).values
    paquete = paquete_del_modulo(estado, validaciones(app, id_sesion), versiones_probadas())
    marca = f"- v{rf_01['version']} · enmendado desde N17 por Revisora el "
    assert marca in paquete["requerimientos.md"]
    assert f"aprobada · enmienda RF-01 v{rf_01['version']}" in paquete["trazabilidad.md"]
    (aplicada,) = estado["requerimientos"].enmiendas
    assert aplicada.texto == ENMIENDA
