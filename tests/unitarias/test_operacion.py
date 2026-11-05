"""Capa de operación compartida por la consola y la web, con servicios simulados y sin Docker."""

import json
from decimal import Decimal

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from multiagente.core.configuracion import ConfiguracionOrquestador
from multiagente.interfaces.documentos import ErrorExportacion
from multiagente.interfaces.operacion import (
    ErrorOperacion,
    Operador,
    detalle_de_recoleccion,
    observaciones_de_pruebas,
)
from multiagente.llm.costos import ConsumoTokens
from multiagente.llm.traza import SESION_ACTUAL, RegistroLlamada, RegistroPorSesion
from multiagente.orquestador.estado import Decision, Destino, Fase, PuntoControl
from multiagente.orquestador.grafo import construir_grafo
from multiagente.orquestador.servicios import Servicios
from multiagente.orquestador.simulacion import (
    DesarrolladorFijo,
    ErrorSimulado,
    ServiciosSimulados,
    guion_completo,
)
from multiagente.orquestador.traza import TrazaEnMemoria
from multiagente.persistencia.puntos_control import serializador

PRUEBA_QUE_PASA = "def test_radicado_con_anio():\n    assert True\n"
PRUEBA_QUE_FALLA = "def test_radicado_falla():\n    assert False, 'falta el año'\n"


def operador(simulacion: ServiciosSimulados | Servicios, tmp_path, entorno) -> Operador:
    servicios = simulacion if isinstance(simulacion, Servicios) else simulacion.como_servicios()
    app = construir_grafo(servicios, ConfiguracionOrquestador(_env_file=None)).compile(
        checkpointer=InMemorySaver(serde=serializador())
    )
    registro = RegistroPorSesion(tmp_path / "traza.jsonl")
    return Operador(app, entorno, registro)


def hasta(operador: Operador, id_sesion: str, punto: str, respuestas: list[str]) -> None:
    """Responde el diálogo y aprueba los puntos de control hasta la pausa indicada."""
    while (pausa := operador.vista(id_sesion).pausa).punto != punto:
        if pausa.punto == "dialogo":
            operador.responder(id_sesion, respuestas.pop(0))
        else:
            operador.decidir(id_sesion, Decision.APROBADO, "Equipo")


def test_flujo_completo_con_pruebas_propias_en_la_aprobacion_final(tmp_path, entorno_falso):
    entorno = entorno_falso
    op = operador(ServiciosSimulados(fallos_veredicto=0), tmp_path, entorno)
    guion = guion_completo()
    id_sesion = op.iniciar("Oficina de catastro", guion.proyecto, guion.necesidad)
    hasta(op, id_sesion, "final", guion.respuestas_cliente)

    vista = op.vista(id_sesion)
    assert (vista.iteracion, vista.limite_iteraciones) == (1, 3)
    assert vista.pausa.datos["iteracion"] == 1

    # La persona prueba la versión: una prueba suya falla y rechaza con ella en las observaciones.
    fallidas = op.probar_propias(id_sesion, {"tests/test_mio.py": PRUEBA_QUE_FALLA})
    assert set(entorno.corridas[0]) > {"tests/test_mio.py"}
    assert [p.nombre for p in fallidas.ejecucion.pruebas] == ["test_radicado_falla"]
    observaciones = observaciones_de_pruebas(fallidas)
    assert (
        "tests/test_mio.py::test_radicado_falla no pasa (fallo): "
        "AssertionError: falta el año assert 2025 == 2026"
    ) in observaciones
    assert "test_radicado.py:3" not in observaciones
    op.decidir(id_sesion, Decision.RECHAZADO, "Laura", observaciones, fallidas)

    # El desarrollador corrige, el tester aprueba y la persona aprueba con su prueba pasando.
    assert op.vista(id_sesion).pausa.datos["version"] == 2
    pasan = op.probar_propias(id_sesion, {"tests/test_mio.py": PRUEBA_QUE_PASA})
    assert observaciones_de_pruebas(pasan) == ""
    op.decidir(id_sesion, Decision.APROBADO, "Laura", pruebas_propias=pasan)

    estado = op.estado(id_sesion)
    assert estado["sesion"].fase is Fase.VALIDADO
    finales = [a for a in estado["sesion"].aprobaciones if a.punto is PuntoControl.FINAL]
    assert [a.decision for a in finales] == [Decision.RECHAZADO, Decision.APROBADO]
    assert finales[1].pruebas_propias == pasan
    assert "| final | aprobado | Laura |" in op.trazabilidad(id_sesion)
    assert "1 de 1 pasan" in op.trazabilidad(id_sesion)
    assert set(op.exportar(id_sesion)) >= {"LEEME.md", "requerimientos.json", "validacion.md"}


def test_una_regla_descubierta_en_n17_entra_a_los_requerimientos_exportados(
    tmp_path, entorno_falso
):
    # Como en el predial (ADR-0015): la prueba propia de la persona destapa una regla nueva.
    op = operador(ServiciosSimulados(fallos_veredicto=0), tmp_path, entorno_falso)
    guion = guion_completo()
    id_sesion = op.iniciar("Oficina de catastro", guion.proyecto, guion.necesidad)
    hasta(op, id_sesion, "final", guion.respuestas_cliente)
    fallidas = op.probar_propias(id_sesion, {"tests/test_mio.py": PRUEBA_QUE_FALLA})
    regla = "El radicado debe incluir el año de la solicitud"
    op.decidir(id_sesion, Decision.RECHAZADO, "Laura", regla, fallidas, Destino.REQUERIMIENTOS)

    vista = op.vista(id_sesion)
    assert vista.fase is Fase.ELICITACION
    assert vista.describir() == "Espera la aprobación de los requerimientos (N6)"
    assert vista.pausa.datos["enmienda"]["texto"] == regla
    assert f"· Laura · en curso · enmienda RF-01 v0.2: {regla}" in op.trazabilidad(id_sesion)

    op.decidir(id_sesion, Decision.APROBADO, "Analista")
    assert op.vista(id_sesion).pausa.datos["version"] == 2
    pasan = op.probar_propias(id_sesion, {"tests/test_mio.py": PRUEBA_QUE_PASA})
    op.decidir(id_sesion, Decision.APROBADO, "Laura", pruebas_propias=pasan)

    paquete = op.exportar(id_sesion)
    rf_01 = json.loads(paquete["requerimientos.json"])["requerimientos"][0]
    assert rf_01["version"] == "0.2"
    assert regla in rf_01["descripcion"]["regla_negocio"]
    assert rf_01["criterios_aceptacion"][-1]["id"] == "ESC-03"
    assert (
        "## RF-01 · versión 0.2\n\n- v0.2 · enmendado desde N17 por Laura el "
        in (paquete["requerimientos.md"])
    )
    trazabilidad = paquete["trazabilidad.md"]
    assert f"· Laura · aprobada · enmienda RF-01 v0.2: {regla}" in trazabilidad
    assert "| final | rechazado | Laura |" in trazabilidad


def test_una_sesion_que_alcanza_su_presupuesto_se_amplia_o_se_cierra(tmp_path, entorno_falso):
    simulacion = ServiciosSimulados(fallos_veredicto=0, costo_por_llamada=Decimal("0.01"))
    configuracion = ConfiguracionOrquestador(
        _env_file=None, presupuesto_maximo_por_modulo_usd=Decimal("0.05")
    )
    traza = TrazaEnMemoria()
    app = construir_grafo(simulacion.como_servicios(), configuracion, traza).compile(
        checkpointer=InMemorySaver(serde=serializador())
    )
    op = Operador(app, entorno_falso, traza=traza)
    guion = guion_completo()
    ampliada = op.iniciar("Oficina", guion.proyecto, guion.necesidad)
    cerrada = op.iniciar("Oficina", guion.proyecto, guion.necesidad)
    for id_sesion in (ampliada, cerrada):
        for respuesta in guion.respuestas_cliente[:4]:
            op.responder(id_sesion, respuesta)

    vista = op.vista(ampliada)
    assert vista.pausa.punto == "presupuesto"
    assert (vista.costo_usd, vista.presupuesto_usd) == (Decimal("0.05"), Decimal("0.05"))
    assert vista.describir().startswith("Detenida por presupuesto: gastó 0.0500 de 0.0500 USD")
    with pytest.raises(ErrorOperacion, match="no espera dialogo"):
        op.responder(ampliada, "Otra respuesta")
    avance = op.ampliar_presupuesto(ampliada, "Laura", Decimal("0.04"))
    assert "debe superar lo gastado" in avance.pausa.datos["aviso"]
    avance = op.ampliar_presupuesto(ampliada, "Laura", Decimal("1.00"), "Cerrar el diálogo")
    assert avance.pausa.punto == "dialogo"

    # Cerrar es la otra salida, desde la misma pausa.
    op.cerrar(cerrada, "Julián", "El presupuesto no alcanza")
    cierre = op.estado(cerrada)["sesion"].cierre
    assert cierre.desde == "Espera que una persona amplíe el presupuesto"
    assert "- Gastado: 0.0500 USD · presupuesto: 0.0500 USD" in op.trazabilidad(cerrada)
    assert len(op.ejecuciones(cerrada)) > 0


def test_el_error_de_recoleccion_indica_el_archivo_y_el_motivo():
    error = (
        "tests/test_mio.py: ImportError while importing test module "
        "'/tmp/codigo/tests/test_mio.py'.\n"
        "E   ModuleNotFoundError: No module named 'radicados'"
    )
    assert detalle_de_recoleccion(error) == (
        "tests/test_mio.py · ModuleNotFoundError: No module named 'radicados'"
    )
    sin_resultado = "Sin resultado de las pruebas: tiempo vencido"
    assert detalle_de_recoleccion(sin_resultado) == sin_resultado


def test_acusa_cuando_la_respuesta_confirma_el_resumen(tmp_path, entorno_falso):
    op = operador(ServiciosSimulados(), tmp_path, entorno_falso)
    guion = guion_completo()
    id_sesion = op.iniciar("Oficina", guion.proyecto, guion.necesidad)
    confirmaciones = []
    while op.vista(id_sesion).pausa.punto == "dialogo":
        vista = op.vista(id_sesion)
        confirmaciones.append(vista.confirma_resumen)
        op.responder(id_sesion, guion.respuestas_cliente.pop(0))
    assert confirmaciones[-1] and not any(confirmaciones[:-1])


def test_reanuda_una_sesion_detenida_por_una_falla(tmp_path, entorno_falso):
    op = operador(
        ServiciosSimulados(fallos_veredicto=0, fallos_ejecucion=1), tmp_path, entorno_falso
    )
    guion = guion_completo()
    id_sesion = op.iniciar("Oficina", guion.proyecto, guion.necesidad)
    hasta(op, id_sesion, "especificacion", guion.respuestas_cliente)
    with pytest.raises(ErrorSimulado):
        op.decidir(id_sesion, Decision.APROBADO, "Arquitecto")

    vista = op.vista(id_sesion)
    assert vista.detenida and vista.pausa is None
    assert vista.pendientes == ("n11_ejecucion",)
    assert "Caída simulada" in vista.error

    avance = op.reanudar(id_sesion)
    assert avance.pausa.punto == "final"
    assert op.vista(id_sesion).error is None
    with pytest.raises(ErrorOperacion, match="no está detenida"):
        op.reanudar(id_sesion)


def test_una_sesion_en_curso_no_se_reanuda_ni_se_cierra(tmp_path, entorno_falso):
    op = operador(
        ServiciosSimulados(fallos_veredicto=0, fallos_ejecucion=1), tmp_path, entorno_falso
    )
    guion = guion_completo()
    id_sesion = op.iniciar("Oficina", guion.proyecto, guion.necesidad)
    hasta(op, id_sesion, "especificacion", guion.respuestas_cliente)
    with pytest.raises(ErrorSimulado):
        op.decidir(id_sesion, Decision.APROBADO, "Arquitecto")

    # Otra corrida la toma, como un proceso que la está reanudando: se ve igual que una caída,
    # pero no se ofrece reanudarla ni cerrarla.
    with op.bloqueos.exclusivo(id_sesion):
        vista = op.vista(id_sesion)
        assert vista.en_curso and not vista.detenida
        assert vista.describir() == "En curso: N11 · ejecución en el entorno aislado"
        assert [v.en_curso for v in op.sesiones()] == [True]
        with pytest.raises(ErrorOperacion, match="en curso"):
            op.reanudar(id_sesion)
        with pytest.raises(ErrorOperacion, match="en curso"):
            op.cerrar(id_sesion, "Analista", "Prueba")

    assert op.vista(id_sesion).detenida
    assert op.reanudar(id_sesion).pausa.punto == "final"


def test_rechaza_operaciones_que_no_corresponden(tmp_path, entorno_falso):
    simulacion = ServiciosSimulados(fallos_veredicto=0)
    version = {"src/simulado/modulo.py": "x = 1\n", "tests/test_modulo.py": "def test_x(): ...\n"}
    servicios = Servicios(
        elicitador=simulacion,
        arquitecto=simulacion,
        desarrollador=DesarrolladorFijo(versiones=[version]),
        tester=simulacion,
    )
    op = operador(servicios, tmp_path, entorno_falso)
    guion = guion_completo()
    with pytest.raises(ErrorOperacion, match="obligatorios"):
        op.iniciar("Oficina", guion.proyecto, "   ")
    with pytest.raises(ErrorOperacion, match="No existe"):
        op.vista("no-existe")

    id_sesion = op.iniciar("Oficina", guion.proyecto, guion.necesidad)
    with pytest.raises(ErrorOperacion, match="pausa actual: dialogo"):
        op.decidir(id_sesion, Decision.APROBADO, "Analista")
    hasta(op, id_sesion, "requerimientos", guion.respuestas_cliente)
    with pytest.raises(ErrorOperacion, match="no espera dialogo"):
        op.responder(id_sesion, "otra respuesta")
    with pytest.raises(ErrorOperacion, match="no espera final"):
        op.probar_propias(id_sesion, {"tests/test_mio.py": PRUEBA_QUE_PASA})
    with pytest.raises(ErrorExportacion):
        op.exportar(id_sesion)

    hasta(op, id_sesion, "final", guion.respuestas_cliente)
    with pytest.raises(ErrorOperacion, match="tests/test_"):
        op.probar_propias(id_sesion, {"src/mio.py": PRUEBA_QUE_PASA})
    with pytest.raises(ErrorOperacion, match="ya son del módulo"):
        op.probar_propias(id_sesion, {"tests/test_modulo.py": PRUEBA_QUE_PASA})


def test_lista_las_sesiones_de_la_mas_reciente_a_la_mas_antigua(tmp_path, entorno_falso):
    op = operador(ServiciosSimulados(), tmp_path, entorno_falso)
    primera = op.iniciar("Cliente A", "Proyecto", "Registrar mutaciones")
    segunda = op.iniciar("Cliente B", "Proyecto", "Liquidar el impuesto")
    assert [vista.id_sesion for vista in op.sesiones()] == [segunda, primera]
    assert [vista.cliente for vista in op.sesiones()] == ["Cliente B", "Cliente A"]


class SimulacionQueObservaLaSesion(ServiciosSimulados):
    """Simulación que anota la sesión de la traza vista por los agentes en cada nodo."""

    def __init__(self) -> None:
        super().__init__(fallos_veredicto=0)
        self.sesiones_vistas: list[str | None] = []

    def dialogar(self, conversacion, contexto):
        self.sesiones_vistas.append(SESION_ACTUAL.get())
        return super().dialogar(conversacion, contexto)

    def recuperar_catalogo(self, requerimientos):
        # N7 corre en paralelo con N16: LangGraph lo ejecuta en otro hilo.
        self.sesiones_vistas.append(SESION_ACTUAL.get())
        return super().recuperar_catalogo(requerimientos)


def test_cada_llamada_queda_en_la_traza_con_su_sesion(tmp_path, entorno_falso):
    simulacion = SimulacionQueObservaLaSesion()
    op = operador(simulacion, tmp_path, entorno_falso)
    guion = guion_completo()
    id_sesion = op.iniciar("Oficina", guion.proyecto, guion.necesidad)
    hasta(op, id_sesion, "especificacion", guion.respuestas_cliente)

    assert simulacion.sesiones_vistas and set(simulacion.sesiones_vistas) == {id_sesion}
    assert SESION_ACTUAL.get() is None


def test_el_registro_por_sesion_escribe_la_sesion_en_cada_linea(tmp_path):
    registro = RegistroPorSesion(tmp_path / "traza" / "llamadas.jsonl")
    llamada = RegistroLlamada(
        fecha="2026-10-09T12:00:00Z",
        nodo="N3",
        prompt="elicitador.dialogo@1.5",
        huella_prompt="x",
        despliegue="gpt-5.4-mini",
        modelo="gpt-5.4-mini",
        region_procesamiento=None,
        esfuerzo="low",
        max_tokens_salida=100,
        motivo_fin="stop",
        consumo=ConsumoTokens(entrada=10, salida=5),
        costo_usd="0.001",
        latencia_ms=900,
    )
    with registro.en_sesion("s-1"):
        registro.registrar(llamada)
    registro.registrar(llamada)
    lineas = [json.loads(linea) for linea in registro.ruta.read_text().splitlines()]
    assert [linea["sesion"] for linea in lineas] == ["s-1", None]
    assert len(registro.llamadas) == 2
