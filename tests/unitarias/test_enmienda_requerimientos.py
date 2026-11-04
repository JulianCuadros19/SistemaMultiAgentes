"""Enmienda de los requerimientos desde N17: validación en código y agente con modelo falso."""

import json
from datetime import UTC, datetime

import pytest

from multiagente.agentes.elicitador.enmienda import (
    EscenarioPrecisadoModelo,
    RequerimientoEnmendadoModelo,
    SalidaEnmienda,
    mensajes_enmienda,
    validar_enmienda,
)
from multiagente.agentes.elicitador.servicio import AgenteElicitador
from multiagente.agentes.elicitador.sintesis import EscenarioModelo
from multiagente.core.esquemas.comunes import Enunciado, Impacto, Prioridad
from multiagente.core.esquemas.requerimiento import (
    DatoEntrada,
    DatoSalida,
    Descripcion,
    EscenarioAceptacion,
    HistoriaUsuario,
    RequerimientoFormal,
    TipoSolicitud,
)
from multiagente.llm.costos import cargar_tarifas
from multiagente.llm.invocador import ErrorValidacionSalida, InvocadorNodo, ParametrosNodo
from multiagente.llm.prompts import cargar_prompt
from multiagente.llm.traza import RegistroEnMemoria
from multiagente.orquestador.estado import (
    Conversacion,
    Emisor,
    Enmienda,
    Requerimientos,
    Turno,
)

AHORA = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)
NECESIDAD = "Necesito registrar los préstamos de los libros de la biblioteca"
REGLA = "Un socio puede tener hasta 3 libros prestados a la vez. El préstamo dura 15 días."
ENMIENDA = (
    "Los libros de la colección de referencia no se prestan: el préstamo se rechaza con el "
    "mensaje «Los libros de referencia solo se consultan en sala»."
)
REGLA_ENMENDADA = (
    f"{REGLA} Los libros de la colección de referencia no se prestan: el préstamo se rechaza "
    "con el mensaje «Los libros de referencia solo se consultan en sala»."
)
TITULO = Enunciado(
    como="bibliotecario", quiero="registrar el préstamo de un libro", para="saber quién lo tiene"
)


def escenario(numero: int, entonces: str) -> EscenarioAceptacion:
    return EscenarioAceptacion(
        id=f"ESC-{numero:02d}",
        nombre=f"Escenario {numero}",
        dado_que=f"un socio con {numero - 1} libros prestados",
        cuando="se registra el préstamo de un libro",
        entonces=entonces,
    )


def requerimiento(numero: int, regla: str = REGLA) -> RequerimientoFormal:
    return RequerimientoFormal(
        id_requerimiento=f"RF-{numero:02d}",
        version="0.1",
        proyecto="Biblioteca",
        tipo_solicitud=TipoSolicitud.NUEVO,
        impacto=Impacto.MEDIO,
        modulo="prestamos",
        autor="Agente elicitador",
        area_funcional="Circulación",
        titulo=TITULO,
        descripcion=Descripcion(
            precondicion="El socio está registrado en la biblioteca",
            regla_negocio=regla,
            datos_entrada=[DatoEntrada(nombre="codigo_libro", tipo="texto", obligatorio=True)],
            datos_salida=[DatoSalida(nombre="fecha_devolucion", tipo="fecha")],
        ),
        criterios_aceptacion=[
            escenario(1, "el préstamo queda registrado con devolución en 15 días"),
            escenario(2, "el préstamo queda registrado"),
            escenario(4, "el préstamo se rechaza porque el socio ya tiene 3 libros"),
        ],
        prioridad=Prioridad.ALTA,
    )


def vigentes(observaciones: tuple[str, ...] = (), sintesis: int = 1) -> Requerimientos:
    return Requerimientos(
        historias=(HistoriaUsuario(id="HU-01", enunciado=TITULO),),
        requerimientos=(
            requerimiento(1),
            requerimiento(2, "La devolución tardía genera una multa de 1.000 pesos por día."),
        ),
        referencias={"RF-01": ("eli-003 v1.1 · Plantilla",), "RF-02": ("eli-003 v1.1 · P",)},
        sintesis=sintesis,
        defectos=("RF-01 · C3 No ambiguo · ESC-05.entonces: cuantificador vago «adecuado»",),
        enmienda=Enmienda(
            texto=ENMIENDA,
            revisor="Revisora",
            fecha=AHORA,
            observaciones_analista=observaciones,
        ),
    )


def conversacion() -> Conversacion:
    return Conversacion(turnos=(Turno(emisor=Emisor.CLIENTE, texto=NECESIDAD, fecha=AHORA),))


NUEVO = EscenarioModelo(
    nombre="Libro de referencia",
    dado_que="Dado que un socio sin libros prestados y un libro de la colección de referencia",
    cuando="Cuando se registra el préstamo del libro",
    entonces="Entonces el préstamo se rechaza con el mensaje «Los libros de referencia solo se "
    "consultan en sala».",
)


def salida(
    regla: str = REGLA_ENMENDADA,
    precisados: tuple[EscenarioPrecisadoModelo, ...] = (),
    nuevos: tuple[EscenarioModelo, ...] = (NUEVO,),
    id_requerimiento: str = "RF-01",
) -> SalidaEnmienda:
    return SalidaEnmienda(
        requerimientos=[
            RequerimientoEnmendadoModelo(
                id_requerimiento=id_requerimiento,
                regla_negocio=regla,
                escenarios_precisados=list(precisados),
                escenarios_nuevos=list(nuevos),
            )
        ]
    )


def test_la_enmienda_agrega_la_regla_y_un_escenario_con_el_id_siguiente():
    previos = vigentes(sintesis=3)
    sintesis = validar_enmienda(salida(), conversacion(), previos)

    rf_01, rf_02 = sintesis.requerimientos
    # El enmendado sube a la versión siguiente; los demás no cambian.
    assert rf_01.version == "0.4"
    assert rf_02 == previos.requerimientos[1]
    assert rf_01.descripcion.regla_negocio == REGLA_ENMENDADA
    # Los identificadores vigentes se conservan y el nuevo toma el siguiente al mayor.
    assert [e.id for e in rf_01.criterios_aceptacion] == ["ESC-01", "ESC-02", "ESC-04", "ESC-05"]
    nuevo = rf_01.criterios_aceptacion[-1]
    assert nuevo.dado_que.startswith("un socio sin libros prestados")
    assert nuevo.cuando == "se registra el préstamo del libro"
    assert nuevo.entonces.endswith("solo se consultan en sala»")
    # El título, la historia, las referencias y lo demás de la ficha no cambian.
    sin_cambio = {"version", "descripcion", "criterios_aceptacion"}
    assert rf_01.model_dump(exclude=sin_cambio) == previos.requerimientos[0].model_dump(
        exclude=sin_cambio
    )
    assert rf_01.descripcion.precondicion == previos.requerimientos[0].descripcion.precondicion
    assert sintesis.historias == previos.historias
    assert sintesis.referencias == previos.referencias


def test_los_escenarios_precisados_conservan_su_id_y_los_omitidos_no_se_eliminan():
    previos = vigentes()
    precisado = EscenarioPrecisadoModelo(
        id="esc-02",
        nombre="Escenario 2",
        dado_que="un socio con 1 libro prestado",
        cuando="se registra el préstamo de un libro que no es de referencia",
        entonces="el préstamo queda registrado",
    )
    sintesis = validar_enmienda(salida(precisados=(precisado,)), conversacion(), previos)
    rf_01 = sintesis.requerimientos[0]
    antes = previos.requerimientos[0].criterios_aceptacion
    assert [e.id for e in rf_01.criterios_aceptacion] == ["ESC-01", "ESC-02", "ESC-04", "ESC-05"]
    assert rf_01.criterios_aceptacion[0] == antes[0]
    assert rf_01.criterios_aceptacion[1].cuando.endswith("que no es de referencia")
    assert rf_01.criterios_aceptacion[2] == antes[2]


def test_una_enmienda_que_solo_precisa_un_escenario_es_valida():
    precisado = EscenarioPrecisadoModelo(
        id="ESC-01",
        nombre="Escenario 1",
        dado_que="un socio sin libros prestados",
        cuando="se registra el préstamo de un libro",
        entonces="el préstamo queda registrado con devolución en 15 días y sin multa",
    )
    sintesis = validar_enmienda(
        salida(regla=REGLA, precisados=(precisado,), nuevos=()), conversacion(), vigentes()
    )
    assert sintesis.requerimientos[0].version == "0.2"
    assert [e.id for e in sintesis.requerimientos[0].criterios_aceptacion] == [
        "ESC-01",
        "ESC-02",
        "ESC-04",
    ]


def test_un_escenario_precisado_que_no_existe_se_rechaza():
    inexistente = EscenarioPrecisadoModelo(
        id="ESC-03", nombre="Otro", dado_que="un socio", cuando="se presta", entonces="se rechaza"
    )
    with pytest.raises(ErrorValidacionSalida, match="ESC-03 no es un escenario vigente"):
        validar_enmienda(salida(precisados=(inexistente,)), conversacion(), vigentes())


def test_un_requerimiento_inexistente_se_rechaza_sin_agregarlo():
    with pytest.raises(ErrorValidacionSalida, match="RF-03 no es un requerimiento vigente"):
        validar_enmienda(salida(id_requerimiento="RF-03"), conversacion(), vigentes())


def test_un_requerimiento_repetido_se_rechaza():
    doble = salida()
    doble.requerimientos.append(doble.requerimientos[0])
    with pytest.raises(ErrorValidacionSalida, match="aparece dos veces"):
        validar_enmienda(doble, conversacion(), vigentes())


def test_la_regla_solo_admite_lo_que_respaldan_la_enmienda_y_el_requerimiento():
    inventada = f"{REGLA_ENMENDADA} Los investigadores visitantes pagan una cuota anual."
    with pytest.raises(ErrorValidacionSalida, match="no se apoyan en la enmienda") as error:
        validar_enmienda(salida(regla=inventada), conversacion(), vigentes())
    assert "investigadores visitantes" in str(error.value.problemas)


def test_la_regla_admite_lo_que_dijeron_el_analista_y_el_cliente():
    observacion = "Los socios infantiles solo llevan libros de la sala juvenil."
    regla = f"{REGLA_ENMENDADA} {observacion}"
    sintesis = validar_enmienda(salida(regla=regla), conversacion(), vigentes((observacion,)))
    assert sintesis.requerimientos[0].descripcion.regla_negocio == regla


def test_una_enmienda_sin_cambios_se_rechaza():
    with pytest.raises(ErrorValidacionSalida, match="no cambió ningún requerimiento"):
        validar_enmienda(salida(regla=REGLA, nuevos=()), conversacion(), vigentes())


def test_la_regla_vacia_se_rechaza():
    with pytest.raises(ErrorValidacionSalida, match="regla_negocio está vacía"):
        validar_enmienda(salida(regla="  "), conversacion(), vigentes())


def test_sin_enmienda_en_curso_no_hay_nada_que_incorporar():
    sin_enmienda = vigentes().model_copy(update={"enmienda": None})
    with pytest.raises(ValueError, match="No hay una enmienda en curso"):
        validar_enmienda(salida(), conversacion(), sin_enmienda)
    with pytest.raises(ValueError, match="No hay una enmienda en curso"):
        mensajes_enmienda(sin_enmienda, "Biblioteca")


def test_los_mensajes_llevan_la_enmienda_sin_contexto_recuperado():
    observacion = "Falta el escenario del libro de referencia"
    (mensaje,) = mensajes_enmienda(vigentes((observacion,)), "Biblioteca")
    datos = json.loads(mensaje["content"])
    assert set(datos) == {
        "proyecto",
        "requerimientos",
        "enmienda",
        "observaciones_analista",
        "defectos",
    }
    assert datos["enmienda"] == ENMIENDA
    assert datos["observaciones_analista"] == [observacion]
    assert datos["defectos"][0].startswith("RF-01 · C3")
    rf_01 = datos["requerimientos"][0]
    assert rf_01["id_requerimiento"] == "RF-01"
    assert "autor" not in rf_01 and "proyecto" not in rf_01


def test_n5_enmienda_con_su_prompt_y_sin_contexto(cliente_falso, completar_respuesta):
    cliente = cliente_falso(completar_respuesta(salida()))
    registro = RegistroEnMemoria()
    parametros = ParametrosNodo(
        nodo="N5", despliegue="gpt-5-nano", esfuerzo="low", max_tokens_salida=4000
    )

    def invocador(nombre: str) -> InvocadorNodo:
        return InvocadorNodo(
            cliente, parametros, cargar_prompt("elicitador", nombre), registro, cargar_tarifas()
        )

    agente = AgenteElicitador(
        None,
        invocador("extraccion"),
        invocador("dialogo"),
        invocador("sintesis"),
        invocador("enmienda"),
    )
    sintesis = agente.enmendar(conversacion(), vigentes(), "Biblioteca")
    assert sintesis.requerimientos[0].version == "0.2"
    (llamada,) = cliente.llamadas
    sistema, datos = llamada["messages"]
    assert sistema["content"] == cargar_prompt("elicitador", "enmienda").texto
    assert "contexto" not in json.loads(datos["content"])
    assert registro.llamadas[0].prompt == cargar_prompt("elicitador", "enmienda").identificador
