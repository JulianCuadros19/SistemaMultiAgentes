"""Capa de operación con PostgreSQL y con el entorno aislado real, sin modelos de lenguaje.

- `pytest -m integracion`: la lista de sesiones se lee de los puntos de control en PostgreSQL;
  una sesión cerrada queda cerrada para otro proceso, y una que otro proceso avanza se ve en
  curso hasta que ese proceso termina o muere.
- `pytest -m sandbox`: las pruebas propias de la persona corren en el entorno aislado contra el
  módulo base del corpus de defectos (RF-38).
"""

import time
import uuid
from datetime import date

import psycopg
import pytest
from langgraph.checkpoint.memory import InMemorySaver

from multiagente.core.configuracion import ConfiguracionBaseDatos, ConfiguracionOrquestador
from multiagente.interfaces.defectos import cargar_corpus_de_defectos
from multiagente.interfaces.operacion import Operador, SesionEnCurso, observaciones_de_pruebas
from multiagente.orquestador.estado import Decision, Fase, ResultadoPrueba
from multiagente.orquestador.grafo import construir_grafo
from multiagente.orquestador.servicios import Servicios
from multiagente.orquestador.simulacion import (
    ArquitectoFijo,
    DesarrolladorFijo,
    ElicitadorFijo,
    ErrorSimulado,
    ServiciosSimulados,
    guion_completo,
)
from multiagente.persistencia.bloqueos import ESPACIO, BloqueosPostgres, clave
from multiagente.persistencia.conexiones import abrir_pool
from multiagente.persistencia.puntos_control import abrir_checkpointer, serializador

CONFIGURACION = ConfiguracionOrquestador(_env_file=None)


@pytest.mark.integracion
def test_lista_las_sesiones_guardadas_en_postgresql():
    with abrir_checkpointer() as checkpointer:
        simulacion = ServiciosSimulados()
        app = construir_grafo(simulacion.como_servicios(), CONFIGURACION).compile(
            checkpointer=checkpointer
        )
        operador = Operador(app)
        primera = operador.iniciar("Cliente A", "Proyecto", "Registrar mutaciones")
        segunda = operador.iniciar("Cliente B", "Proyecto", "Liquidar el impuesto")
        try:
            sesiones = [vista.id_sesion for vista in operador.sesiones()]
            assert sesiones.index(segunda) < sesiones.index(primera)
            assert operador.vista(segunda).cliente == "Cliente B"
        finally:
            for id_sesion in (primera, segunda):
                checkpointer.delete_thread(id_sesion)


@pytest.mark.integracion
def test_una_sesion_cerrada_queda_cerrada_para_otro_proceso():
    guion = guion_completo()
    simulacion = ServiciosSimulados(fallos_veredicto=0, fallos_ejecucion=1)
    with abrir_checkpointer() as checkpointer:
        app = construir_grafo(simulacion.como_servicios(), CONFIGURACION).compile(
            checkpointer=checkpointer
        )
        operador = Operador(app)
        en_pausa = operador.iniciar("Cliente A", guion.proyecto, guion.necesidad)
        detenida = operador.iniciar("Cliente B", guion.proyecto, guion.necesidad)
        try:
            for respuesta in guion.respuestas_cliente[:7]:
                operador.responder(detenida, respuesta)
            operador.decidir(detenida, Decision.APROBADO, "Analista")
            with pytest.raises(ErrorSimulado):
                operador.decidir(detenida, Decision.APROBADO, "Arquitecto")
            assert operador.vista(detenida).detenida

            operador.cerrar(en_pausa, "Laura", "El cliente desistió")
            operador.cerrar(detenida, "Julián", "Docker no está disponible")

            # Otro proceso, con su propia conexión, las encuentra cerradas y sin nada pendiente.
            with abrir_checkpointer() as otra_conexion:
                lector = Operador(
                    construir_grafo(ServiciosSimulados().como_servicios(), CONFIGURACION).compile(
                        checkpointer=otra_conexion
                    )
                )
                for id_sesion in (en_pausa, detenida):
                    vista = lector.vista(id_sesion)
                    assert vista.fase is Fase.CERRADA and vista.terminada
                cierre = lector.estado(detenida)["sesion"].cierre
                assert (cierre.revisor, cierre.motivo) == ("Julián", "Docker no está disponible")
                assert "N11" in cierre.desde
        finally:
            for id_sesion in (en_pausa, detenida):
                checkpointer.delete_thread(id_sesion)


@pytest.mark.integracion
def test_una_sesion_que_otro_proceso_avanza_no_se_reanuda_hasta_que_ese_proceso_muere():
    guion = guion_completo()
    simulacion = ServiciosSimulados(fallos_veredicto=0, fallos_ejecucion=1)
    otro_proceso = f"prueba-otro-proceso-{uuid.uuid4().hex[:8]}"
    with abrir_checkpointer() as checkpointer, abrir_pool(aplicacion="prueba-bloqueos") as pool:
        app = construir_grafo(simulacion.como_servicios(), CONFIGURACION).compile(
            checkpointer=checkpointer
        )
        operador = Operador(app, bloqueos=BloqueosPostgres(pool))
        id_sesion = operador.iniciar("Cliente", guion.proyecto, guion.necesidad)
        conexion = psycopg.connect(
            ConfiguracionBaseDatos().cadena_conexion(),
            autocommit=True,
            application_name=otro_proceso,
        )
        try:
            for respuesta in guion.respuestas_cliente[:7]:
                operador.responder(id_sesion, respuesta)
            operador.decidir(id_sesion, Decision.APROBADO, "Analista")
            with pytest.raises(ErrorSimulado):
                operador.decidir(id_sesion, Decision.APROBADO, "Arquitecto")
            assert operador.vista(id_sesion).detenida

            # Otro proceso la toma para reanudarla: se ve en curso y no se reanuda ni se cierra.
            conexion.execute("SELECT pg_advisory_lock(%s, %s)", (ESPACIO, clave(id_sesion)))
            vista = operador.vista(id_sesion)
            assert vista.en_curso and not vista.detenida
            with pytest.raises(SesionEnCurso):
                operador.reanudar(id_sesion)
            with pytest.raises(SesionEnCurso):
                operador.cerrar(id_sesion, "Analista", "Prueba")

            # Si ese proceso muere, PostgreSQL suelta el bloqueo con su conexión.
            with psycopg.connect(ConfiguracionBaseDatos().cadena_conexion()) as admin:
                admin.execute(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE application_name = %s",
                    (otro_proceso,),
                )
            for _ in range(50):
                if operador.vista(id_sesion).detenida:
                    break
                time.sleep(0.1)
            assert operador.vista(id_sesion).detenida
            assert operador.reanudar(id_sesion).pausa.punto == "final"
        finally:
            conexion.close()
            checkpointer.delete_thread(id_sesion)


PRUEBA_PROPIA = f"""from decimal import Decimal

import pytest

from aplicacion.calculo_avaluo import calcular_avaluo
from dominio.avaluo import ValoresUnitarios
from infraestructura import valores_unitarios_repositorio as repositorio

NUMERO = "2" * 30


@pytest.fixture
def valores(monkeypatch):
    registros = {{(NUMERO, {date.today().year}): ValoresUnitarios(Decimal("1000"), Decimal("0"))}}
    monkeypatch.setattr(repositorio, "_VALORES_UNITARIOS", registros)


def test_lote_sin_construccion(valores):
    resultado = calcular_avaluo(NUMERO, {date.today().year}, Decimal("50"), Decimal("0"))
    assert resultado.avaluo_total == Decimal("50000")


def test_expectativa_equivocada(valores):
    resultado = calcular_avaluo(NUMERO, {date.today().year}, Decimal("50"), Decimal("0"))
    assert resultado.avaluo_total == Decimal("1")
"""


@pytest.mark.sandbox
def test_las_pruebas_propias_corren_en_el_entorno_aislado(entorno_aislado):
    corpus = next(c for c in cargar_corpus_de_defectos() if c.nombre == "avaluo")
    simulacion = ServiciosSimulados(fallos_veredicto=0)
    servicios = Servicios(
        elicitador=ElicitadorFijo(corpus.caso.sintesis),
        arquitecto=ArquitectoFijo(corpus.caso.diseno),
        desarrollador=DesarrolladorFijo(
            versiones=[next(v for v in corpus.variantes() if v.es_control).archivos]
        ),
        tester=simulacion,
    )
    app = construir_grafo(servicios, CONFIGURACION).compile(
        checkpointer=InMemorySaver(serde=serializador())
    )
    operador = Operador(app, entorno_aislado)
    id_sesion = operador.iniciar(corpus.caso.cliente, corpus.caso.proyecto, "Avalúo")
    operador.decidir(id_sesion, Decision.APROBADO, "Analista")
    operador.decidir(id_sesion, Decision.APROBADO, "Arquitecto")
    assert operador.vista(id_sesion).pausa.punto == "final"

    pruebas = operador.probar_propias(id_sesion, {"tests/test_persona.py": PRUEBA_PROPIA})

    resultados = {p.nombre: p.resultado for p in pruebas.ejecucion.pruebas}
    assert resultados == {
        "test_lote_sin_construccion": ResultadoPrueba.PASO,
        "test_expectativa_equivocada": ResultadoPrueba.FALLO,
    }
    assert pruebas.ejecucion.errores_recoleccion == ()
    assert "test_expectativa_equivocada no pasa (fallo)" in observaciones_de_pruebas(pruebas)
