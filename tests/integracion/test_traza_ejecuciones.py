"""Traza por nodo en PostgreSQL: migración 0002, escritura y consulta (RF-34, ADR-0016).

Cada prueba crea un esquema temporal, migra en él y lo borra al terminar, sin tocar las tablas
reales. Requiere el contenedor levantado con `docker compose up -d --wait` y el archivo .env.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import psycopg
import pytest
from langgraph.checkpoint.memory import InMemorySaver

from multiagente.core.configuracion import ConfiguracionBaseDatos, ConfiguracionOrquestador
from multiagente.interfaces.operacion import Operador
from multiagente.llm.costos import ConsumoTokens
from multiagente.llm.traza import RegistroLlamada
from multiagente.orquestador.grafo import Nodo, construir_grafo
from multiagente.orquestador.simulacion import (
    Guion,
    ServiciosSimulados,
    aprobar,
    recorrer,
)
from multiagente.orquestador.traza import EjecucionNodo
from multiagente.persistencia.conexiones import abrir_pool
from multiagente.persistencia.ejecuciones import TrazaEjecuciones
from multiagente.persistencia.migraciones import migrar
from multiagente.persistencia.puntos_control import abrir_checkpointer, serializador

pytestmark = pytest.mark.integracion

AHORA = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)


@pytest.fixture
def pool():
    """Pool cuyas conexiones usan un esquema temporal, ya migrado, que se borra al terminar."""
    cadena = ConfiguracionBaseDatos().cadena_conexion()
    esquema = f"prueba_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(cadena, autocommit=True) as administracion:
        administracion.execute(f'CREATE SCHEMA "{esquema}"')
    try:
        with abrir_pool(
            aplicacion="multiagente-pruebas", options=f"-c search_path={esquema},public"
        ) as abierto:
            assert migrar(abierto) == ["0001_bases_conocimiento", "0002_ejecuciones"]
            assert migrar(abierto) == []
            yield abierto
    finally:
        with psycopg.connect(cadena, autocommit=True) as administracion:
            administracion.execute(f'DROP SCHEMA "{esquema}" CASCADE')


def llamada(prompt: str, costo: str, error: str | None = None) -> RegistroLlamada:
    return RegistroLlamada(
        fecha=AHORA,
        nodo="N10",
        prompt=prompt,
        huella_prompt="a" * 64,
        despliegue="gpt-6.1-sol",
        modelo="gpt-6.1-sol-2026-09-29",
        region_procesamiento="South Central US",
        esfuerzo="medium",
        max_tokens_salida=32000,
        motivo_fin="stop",
        consumo=ConsumoTokens(
            entrada=14079,
            entrada_cacheada=2048,
            entrada_escrita_cache=1024,
            salida=7554,
            razonamiento=512,
        ),
        costo_usd=Decimal(costo),
        latencia_ms=99_300,
        error=error,
    )


def test_la_traza_guarda_cada_nodo_con_sus_llamadas_y_el_costo_exacto(pool):
    traza = TrazaEjecuciones(pool)
    generacion = EjecucionNodo(
        sesion="s-1",
        nodo=Nodo.N10.value,
        inicio=AHORA,
        duracion_ms=99_500,
        llamadas=(
            llamada("desarrollador.generacion@1.9", "0.103826400"),
            llamada("desarrollador.generacion@1.9", "0.000000125", error="ErrorSalidaInvalida"),
        ),
    )
    caida = EjecucionNodo(
        sesion="s-1",
        nodo=Nodo.N11.value,
        inicio=AHORA.replace(minute=2),
        duracion_ms=1_200,
        error="ErrorEntornoAislado('Docker no responde')",
    )
    otra = EjecucionNodo(sesion="s-2", nodo=Nodo.N1.value, inicio=AHORA, duracion_ms=3)
    for ejecucion in (generacion, caida, otra):
        traza.registrar_nodo(ejecucion)

    assert traza.consultar("s-1") == [generacion, caida]
    assert traza.consultar("s-2") == [otra]
    assert traza.consultar("no-existe") == []
    with pool.connection() as conexion:
        costo = conexion.execute(
            "SELECT costo_usd FROM ejecuciones WHERE nodo = %s", (Nodo.N10.value,)
        ).fetchone()[0]
    assert costo == Decimal("0.103826525")


def test_el_grafo_deja_su_traza_en_postgresql(pool):
    traza = TrazaEjecuciones(pool)
    simulacion = ServiciosSimulados(fallos_veredicto=0, costo_por_llamada=Decimal("0.01"))
    app = construir_grafo(
        simulacion.como_servicios(), ConfiguracionOrquestador(_env_file=None), traza
    ).compile(checkpointer=InMemorySaver(serde=serializador()))
    guion = Guion(
        necesidad="Registrar mutaciones",
        respuestas_cliente=[
            "Analista",
            "Ahorrar tiempo",
            "El predio debe existir",
            "Número predial",
            "Radicado",
            "Si el predio no existe, se rechaza",
            "Sí, es correcto",
        ],
        decisiones={punto: [aprobar()] for punto in ("requerimientos", "especificacion", "final")},
    )
    recorrido = recorrer(app, guion)

    ejecuciones = traza.consultar(recorrido.id_sesion)
    assert {ejecucion.nodo for ejecucion in ejecuciones} == {nodo.value for nodo in Nodo}
    estado = app.get_state({"configurable": {"thread_id": recorrido.id_sesion}}).values
    assert sum(e.costo_usd for e in ejecuciones) == estado["control"].costo_acumulado_usd


def test_el_operador_con_postgresql_pausa_por_presupuesto_y_lo_amplia(pool):
    simulacion = ServiciosSimulados(fallos_veredicto=0, costo_por_llamada=Decimal("0.01"))
    configuracion = ConfiguracionOrquestador(
        _env_file=None, presupuesto_maximo_por_modulo_usd=Decimal("0.03")
    )
    traza = TrazaEjecuciones(pool)
    with abrir_checkpointer() as checkpointer:
        app = construir_grafo(simulacion.como_servicios(), configuracion, traza).compile(
            checkpointer=checkpointer
        )
        operador = Operador(app, traza=traza)
        id_sesion = operador.iniciar("Oficina", "Catastro", "Registrar mutaciones")
        try:
            operador.responder(id_sesion, "Analista")
            operador.responder(id_sesion, "Ahorrar tiempo")
            vista = operador.vista(id_sesion)
            assert vista.pausa.punto == "presupuesto"
            assert vista.costo_usd == Decimal("0.03")

            # Otro proceso, con su propia conexión, la ve igual y puede ampliarla.
            with abrir_checkpointer() as otro:
                otra_app = construir_grafo(
                    simulacion.como_servicios(), configuracion, traza
                ).compile(checkpointer=otro)
                avance = Operador(otra_app, traza=traza).ampliar_presupuesto(
                    id_sesion, "Laura", Decimal("0.50")
                )
                assert avance.pausa.punto == "dialogo"
            operador.responder(id_sesion, "El predio debe existir")
            control = operador.estado(id_sesion)["control"]
            assert control.presupuesto_usd == Decimal("0.50")
            assert control.ampliaciones[0].gastado == Decimal("0.03")
            ejecuciones = operador.ejecuciones(id_sesion)
            assert sum(e.costo_usd for e in ejecuciones) == control.costo_acumulado_usd
            assert "## Llamadas al modelo" in operador.traza(id_sesion)
        finally:
            checkpointer.delete_thread(id_sesion)
