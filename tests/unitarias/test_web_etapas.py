"""Etapas de la línea del flujo, grupos del panel y pasos del cliente, con servicios simulados."""

from decimal import Decimal

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from multiagente.core.configuracion import ConfiguracionOrquestador
from multiagente.interfaces.operacion import Operador
from multiagente.interfaces.web.etapas import (
    ETAPA_DE_NODO,
    Etapa,
    etapas_de,
    fila_del_panel,
    grupo_de,
    pasos_del_cliente,
    tono_de,
)
from multiagente.orquestador.estado import Decision, Destino
from multiagente.orquestador.grafo import Nodo, construir_grafo
from multiagente.orquestador.simulacion import ErrorSimulado, ServiciosSimulados, guion_completo
from multiagente.persistencia.puntos_control import serializador

GUION = guion_completo()


def operador_con(
    simulacion: ServiciosSimulados | None = None, presupuesto: Decimal | None = None
) -> Operador:
    extra = {"presupuesto_maximo_por_modulo_usd": presupuesto} if presupuesto else {}
    configuracion = ConfiguracionOrquestador(_env_file=None, **extra)
    servicios = (simulacion or ServiciosSimulados(fallos_veredicto=0)).como_servicios()
    app = construir_grafo(servicios, configuracion).compile(
        checkpointer=InMemorySaver(serde=serializador())
    )
    return Operador(app)


def hasta_n6(operador: Operador) -> str:
    id_sesion = operador.iniciar("Oficina de catastro", "Gestión catastral", GUION.necesidad)
    for respuesta in GUION.respuestas_cliente[:7]:
        operador.responder(id_sesion, respuesta)
    return id_sesion


def hasta_n17(operador: Operador) -> str:
    id_sesion = hasta_n6(operador)
    operador.decidir(id_sesion, Decision.APROBADO, "Laura")
    operador.decidir(id_sesion, Decision.APROBADO, "Julián")
    return id_sesion


def etapas(operador: Operador, id_sesion: str, procesando: bool = False):
    lista, abierta = etapas_de(operador.vista(id_sesion), operador.estado(id_sesion), procesando)
    return lista, {etapa.clave: etapa for etapa in lista}, abierta


def resumen(etapa: Etapa) -> tuple[str, str | None, str]:
    return etapa.estado, etapa.tono, etapa.detalle


def test_cada_nodo_pertenece_a_una_etapa():
    assert set(ETAPA_DE_NODO) == {nodo.value for nodo in Nodo}


def test_en_el_dialogo_la_conversacion_espera_al_cliente():
    operador = operador_con()
    id_sesion = operador.iniciar("Oficina de catastro", "Gestión catastral", GUION.necesidad)
    lista, por_clave, abierta = etapas(operador, id_sesion)

    assert abierta == "conversacion"
    assert [etapa.punto for etapa in lista] == [None, "N6", "N9", None, "N17"]
    assert resumen(por_clave["conversacion"]) == ("actual", "espera", "Espera al cliente")
    assert {etapa.estado for etapa in lista[1:]} == {"pendiente"}
    assert grupo_de(operador.vista(id_sesion)) == "curso"
    assert [paso.estado for paso in pasos_del_cliente(lista)] == [
        "actual",
        "pendiente",
        "pendiente",
        "pendiente",
    ]


def test_en_n6_la_conversacion_queda_hecha_y_los_requerimientos_esperan():
    operador = operador_con()
    id_sesion = hasta_n6(operador)
    lista, por_clave, abierta = etapas(operador, id_sesion)

    turnos = len(operador.estado(id_sesion)["conversacion"].turnos)
    assert abierta == "requerimientos"
    assert resumen(por_clave["conversacion"]) == ("hecha", None, f"{turnos} turnos")
    assert resumen(por_clave["requerimientos"]) == ("actual", "espera", "Espera su decisión")
    assert grupo_de(operador.vista(id_sesion)) == "equipo"
    assert [paso.estado for paso in pasos_del_cliente(lista)] == [
        "hecha",
        "actual",
        "pendiente",
        "pendiente",
    ]


def test_en_n17_cada_etapa_anterior_dice_quien_la_aprobo():
    operador = operador_con()
    id_sesion = hasta_n17(operador)
    _, por_clave, abierta = etapas(operador, id_sesion)

    assert abierta == "final"
    assert por_clave["requerimientos"].detalle == "Aprobados por Laura"
    assert por_clave["diseno"].detalle == "Aprobado por Julián"
    assert resumen(por_clave["desarrollo"]) == ("hecha", None, "1 versión")
    assert resumen(por_clave["final"]) == ("actual", "espera", "Espera su decisión")


def test_una_sesion_validada_queda_toda_hecha():
    operador = operador_con()
    id_sesion = hasta_n17(operador)
    operador.decidir(id_sesion, Decision.APROBADO, "Julián")
    lista, por_clave, abierta = etapas(operador, id_sesion)

    vista = operador.vista(id_sesion)
    assert abierta == "final"
    assert {etapa.estado for etapa in lista} == {"hecha"}
    assert por_clave["final"].detalle == "Validado por Julián"
    assert grupo_de(vista) == "terminadas"
    assert tono_de(vista) == ("ok", "Validado")
    assert {paso.estado for paso in pasos_del_cliente(lista)} == {"hecha"}


def test_una_sesion_escalada_se_marca_en_alerta():
    operador = operador_con(ServiciosSimulados(fallos_veredicto=3))
    id_sesion = hasta_n17(operador)
    _, por_clave, _ = etapas(operador, id_sesion)

    assert resumen(por_clave["final"]) == ("actual", "alerta", "Escalada")
    assert por_clave["desarrollo"].detalle == "3 versiones"
    assert grupo_de(operador.vista(id_sesion)) == "equipo"


def test_una_falla_marca_la_etapa_donde_se_detuvo():
    operador = operador_con(ServiciosSimulados(fallos_veredicto=0, fallos_ejecucion=1))
    id_sesion = hasta_n6(operador)
    operador.decidir(id_sesion, Decision.APROBADO, "Laura")
    with pytest.raises(ErrorSimulado):
        operador.decidir(id_sesion, Decision.APROBADO, "Julián")
    _, por_clave, abierta = etapas(operador, id_sesion)

    assert abierta == "desarrollo"
    assert resumen(por_clave["desarrollo"]) == ("actual", "alerta", "Detenida por una falla")
    assert grupo_de(operador.vista(id_sesion)) == "equipo"


def test_la_pausa_por_presupuesto_marca_la_etapa_del_nodo_que_espera():
    simulacion = ServiciosSimulados(fallos_veredicto=0, costo_por_llamada=Decimal("0.01"))
    operador = operador_con(simulacion, presupuesto=Decimal("0.05"))
    id_sesion = operador.iniciar("Oficina de catastro", "Gestión catastral", GUION.necesidad)
    for respuesta in GUION.respuestas_cliente:
        if operador.vista(id_sesion).pausa.punto != "dialogo":
            break
        operador.responder(id_sesion, respuesta)
    _, por_clave, abierta = etapas(operador, id_sesion)

    assert abierta == "conversacion"
    assert resumen(por_clave["conversacion"]) == ("actual", "alerta", "Sin presupuesto")
    assert grupo_de(operador.vista(id_sesion)) == "equipo"


def test_una_sesion_cerrada_queda_en_la_etapa_que_alcanzo():
    operador = operador_con()
    id_sesion = operador.iniciar("Oficina de catastro", "Gestión catastral", GUION.necesidad)
    operador.cerrar(id_sesion, "Laura", "El cliente desistió")
    _, por_clave, abierta = etapas(operador, id_sesion)

    assert abierta == "conversacion"
    assert resumen(por_clave["conversacion"]) == ("actual", "neutro", "Cerrada aquí")
    assert grupo_de(operador.vista(id_sesion)) == "terminadas"


def test_tras_una_enmienda_las_etapas_siguientes_siguen_hechas():
    operador = operador_con()
    id_sesion = hasta_n17(operador)
    operador.decidir(
        id_sesion,
        Decision.RECHAZADO,
        "Laura",
        observaciones="El radicado debe incluir el año",
        destino=Destino.REQUERIMIENTOS,
    )
    lista, por_clave, abierta = etapas(operador, id_sesion)

    assert abierta == "requerimientos"
    assert [etapa.estado for etapa in lista] == ["hecha", "actual", "hecha", "hecha", "pendiente"]
    assert [paso.estado for paso in pasos_del_cliente(lista)] == [
        "hecha",
        "actual",
        "hecha",
        "pendiente",
    ]


def test_mientras_la_web_procesa_la_etapa_actual_lo_indica():
    operador = operador_con()
    id_sesion = hasta_n6(operador)
    _, por_clave, _ = etapas(operador, id_sesion, procesando=True)
    fila = fila_del_panel(
        operador.vista(id_sesion), operador.estado(id_sesion), "Sintetizando los requerimientos"
    )

    assert resumen(por_clave["requerimientos"]) == ("actual", "procesa", "Procesando")
    assert (fila.grupo, fila.tono, fila.tarea) == (
        "curso",
        "procesa",
        "Sintetizando los requerimientos",
    )
    assert len(fila.etapas) == 5
