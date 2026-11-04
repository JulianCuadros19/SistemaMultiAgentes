"""Pruebas del estado tipado del grafo y de su serialización en los puntos de control."""

import json
import logging
import re
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from multiagente.core.esquemas.especificacion_diseno import EspecificacionDiseno, TipoInterfaz
from multiagente.core.esquemas.requerimiento import DatoEntrada, DatoSalida, RequerimientoFormal
from multiagente.orquestador.estado import (
    INTENTOS_SIN_RESPUESTA,
    MAX_PREGUNTAS_CASOS_LIMITE,
    PARTICIONES,
    RESERVA_TURNOS_CONFIRMACION,
    AprobacionHumana,
    Arquitectura,
    CasoPrueba,
    CategoriaCasoLimite,
    Codigo,
    ConformidadModulo,
    Contexto,
    Control,
    Conversacion,
    Decision,
    Destino,
    EjecucionPruebas,
    Emisor,
    Enmienda,
    Fase,
    FragmentoContexto,
    Hallazgo,
    PruebaEjecutada,
    PruebasPropias,
    PuntoControl,
    RegistroCaptura,
    Requerimientos,
    RespuestaHumana,
    ResultadoPrueba,
    Sesion,
    Severidad,
    Turno,
    Validacion,
    Veredicto,
    VeredictoCaso,
    VersionCodigo,
)
from multiagente.orquestador.grafo import Nodo, ruta_tras_suficiencia
from multiagente.orquestador.servicios import Dialogo
from multiagente.persistencia.puntos_control import serializador, tipos_permitidos

RAIZ = Path(__file__).resolve().parents[2]
AHORA = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)


def caso(numero: int) -> CasoPrueba:
    return CasoPrueba(
        id=f"CP-RF-01-ESC-0{numero}",
        id_requerimiento="RF-01",
        id_escenario=f"ESC-0{numero}",
        dado_que="un contexto",
        cuando="ocurre una acción",
        entonces="se observa un resultado",
    )


def veredicto(numero: int, cumple: bool) -> VeredictoCaso:
    return VeredictoCaso(id_caso=f"CP-RF-01-ESC-0{numero}", cumple=cumple, evidencia="prueba")


PRUEBA_PROPIA = "def test_limite():\n    assert True\n"


def pruebas_propias() -> PruebasPropias:
    return PruebasPropias(
        archivos={"tests/test_propia.py": PRUEBA_PROPIA},
        ejecucion=EjecucionPruebas(
            pruebas=(
                PruebaEjecutada(
                    archivo="tests/test_propia.py",
                    nombre="test_limite",
                    resultado=ResultadoPrueba.PASO,
                ),
            )
        ),
    )


def test_pruebas_propias_conservan_el_contenido_y_exigen_su_ruta():
    assert pruebas_propias().archivos["tests/test_propia.py"] == PRUEBA_PROPIA
    with pytest.raises(ValidationError, match="tests/test_"):
        PruebasPropias(archivos={"src/otro.py": "x = 1\n"}, ejecucion=EjecucionPruebas())


def test_la_decision_final_registra_las_pruebas_propias():
    respuesta = RespuestaHumana.model_validate(
        {
            "decision": "aprobado",
            "revisor": "Laura",
            "pruebas_propias": pruebas_propias().model_dump(mode="json"),
        }
    )
    aprobacion = AprobacionHumana(**respuesta.model_dump(), punto=PuntoControl.FINAL, fecha=AHORA)
    assert aprobacion.pruebas_propias == pruebas_propias()


def test_rechazo_exige_observaciones():
    with pytest.raises(ValidationError, match="observaciones"):
        RespuestaHumana(decision=Decision.RECHAZADO, revisor="Analista")
    RespuestaHumana(decision=Decision.APROBADO, revisor="Analista")


def registro_completo(**cambios) -> RegistroCaptura:
    datos = {
        "rol": "analista de conservación catastral",
        "funcionalidad": "registrar solicitudes de mutación",
        "beneficio": "tramitar el cambio del predio",
        "reglas_negocio": ("La solicitud se acepta solo si el predio existe",),
        "datos_entrada": (DatoEntrada(nombre="numero_predial", tipo="texto", obligatorio=True),),
        "datos_salida": (DatoSalida(nombre="radicado", tipo="texto", formato="RAD-AAAA-NNNN"),),
        "excepciones": ("Si el predio no existe, la solicitud se rechaza",),
    }
    return RegistroCaptura(**(datos | cambios))


def test_registro_declara_pendientes_en_orden():
    assert RegistroCaptura().pendientes == [
        "rol",
        "funcionalidad",
        "beneficio",
        "reglas_negocio",
        "datos_entrada",
        "datos_salida",
        "excepciones",
        "confirmacion",
    ]
    parcial = registro_completo(funcionalidad=None, datos_salida=())
    assert parcial.pendientes == ["funcionalidad", "datos_salida", "confirmacion"]
    # Con los atributos completos, antes del resumen, quedan los casos límite (ADR-0015).
    assert registro_completo().pendientes == ["casos_limite", "confirmacion"]
    # Cerrada la fase, una sola vez, la pregunta por algo más (eli-006).
    cerrada = registro_completo(casos_limite_cerrados=True)
    assert cerrada.pendientes == ["algo_mas", "confirmacion"]
    assert cerrada.model_copy(update={"algo_mas_preguntado": True}).pendientes == ["confirmacion"]
    preguntadas = tuple(CategoriaCasoLimite)[:MAX_PREGUNTAS_CASOS_LIMITE]
    agotados = registro_completo(categorias_casos_limite=preguntadas)
    assert agotados.pendientes == ["algo_mas", "confirmacion"]
    assert registro_completo(resumen_confirmado=True).pendientes == []


def test_confirmacion_exige_registro_completo():
    with pytest.raises(ValidationError, match="confirmarse"):
        registro_completo(excepciones=(), resumen_confirmado=True)
    # Un solo «no sé» no basta para confirmar sin el atributo.
    with pytest.raises(ValidationError, match="confirmarse"):
        registro_completo(excepciones=(), no_sabe=("excepciones",), resumen_confirmado=True)


def test_lo_que_el_cliente_no_sabe_deja_de_preguntarse():
    una_vez = registro_completo(datos_salida=(), no_sabe=("datos_salida",))
    assert una_vez.sin_respuesta == []
    assert una_vez.por_preguntar == ["datos_salida", "confirmacion"]
    sin_salidas = registro_completo(
        datos_salida=(), no_sabe=("datos_salida",) * INTENTOS_SIN_RESPUESTA
    )
    assert sin_salidas.sin_respuesta == ["datos_salida"]
    # Sigue declarado como pendiente (RF-03), pero N3 ya no lo pregunta: siguen los casos límite.
    assert sin_salidas.pendientes == ["datos_salida", "casos_limite", "confirmacion"]
    assert sin_salidas.por_preguntar == ["casos_limite", "confirmacion"]


def test_confirmar_sin_lo_que_el_cliente_no_sabe_cierra_la_elicitacion():
    confirmado = registro_completo(
        datos_salida=(),
        no_sabe=("datos_salida",) * INTENTOS_SIN_RESPUESTA,
        resumen_confirmado=True,
    )
    assert confirmado.pendientes == ["datos_salida"]
    assert confirmado.por_preguntar == []
    control = Control(
        limite_iteraciones=3, limite_turnos=15, limite_correcciones=2, limite_correcciones_diseno=2
    )
    estado = {"conversacion": Conversacion(registro=confirmado), "control": control}
    assert ruta_tras_suficiencia(estado) is Nodo.N5
    assert Dialogo(registro=confirmado, siguiente_pregunta=None).siguiente_pregunta is None
    with pytest.raises(ValidationError, match="por preguntar"):
        Dialogo(registro=confirmado, siguiente_pregunta="¿Algo más?")


def test_respuesta_nueva_distingue_lo_ya_procesado():
    necesidad = Turno(emisor=Emisor.CLIENTE, texto="Necesito liquidar", fecha=AHORA)
    pregunta = Turno(emisor=Emisor.ELICITADOR, texto="¿Quién lo usa?", fecha=AHORA)
    respuesta = Turno(emisor=Emisor.CLIENTE, texto="El liquidador", fecha=AHORA)

    inicial = Conversacion(turnos=(necesidad,))
    assert inicial.necesidad == inicial.respuesta_nueva == "Necesito liquidar"
    esperando = Conversacion(turnos=(necesidad, pregunta), turnos_procesados=2)
    assert esperando.respuesta_nueva is None
    respondida = esperando.model_copy(update={"turnos": (necesidad, pregunta, respuesta)})
    assert respondida.respuesta_nueva == "El liquidador"
    assert respondida.turnos_cliente == 2


@pytest.mark.parametrize(
    ("plan", "veredictos", "esperado"),
    [
        ((), (), False),
        ((caso(1), caso(2)), (veredicto(1, True),), False),
        ((caso(1), caso(2)), (veredicto(1, True), veredicto(2, False)), False),
        ((caso(1), caso(2)), (veredicto(1, True), veredicto(2, True)), True),
    ],
)
def test_validacion_aprobada_solo_si_todos_los_casos_cumplen(plan, veredictos, esperado):
    validacion = Validacion(plan_pruebas=plan, veredictos=veredictos, veredicto=Veredicto.APROBADO)
    assert validacion.aprobado is esperado


def test_validacion_no_aprobada_sin_veredicto_aprobado():
    # Con un hallazgo Alta el veredicto es rechazado aunque todos los casos cumplan (cal-sv).
    plan, veredictos = (caso(1),), (veredicto(1, True),)
    assert not Validacion(plan_pruebas=plan, veredictos=veredictos).aprobado
    rechazada = Validacion(plan_pruebas=plan, veredictos=veredictos, veredicto=Veredicto.RECHAZADO)
    assert not rechazada.aprobado


def test_particiones_inmutables():
    conversacion = Conversacion()
    with pytest.raises(ValidationError):
        conversacion.pregunta_pendiente = "¿Cambio directo?"


def test_ultima_aprobacion_por_punto():
    def aprobacion(punto: PuntoControl, decision: Decision) -> AprobacionHumana:
        observaciones = "ajustar" if decision is Decision.RECHAZADO else None
        return AprobacionHumana(
            punto=punto, decision=decision, revisor="R", observaciones=observaciones, fecha=AHORA
        )

    sesion = Sesion(
        id_sesion="s1",
        cliente="Realtix",
        proyecto="Gestión catastral",
        fase="diseno",
        creada=AHORA,
        aprobaciones=(
            aprobacion(PuntoControl.REQUERIMIENTOS, Decision.RECHAZADO),
            aprobacion(PuntoControl.REQUERIMIENTOS, Decision.APROBADO),
        ),
    )
    assert sesion.ultima_aprobacion(PuntoControl.REQUERIMIENTOS).decision is Decision.APROBADO
    assert sesion.ultima_aprobacion(PuntoControl.FINAL) is None


def fragmento(documento_id: str, titulo: str = "Sección") -> FragmentoContexto:
    return FragmentoContexto(
        documento_id=documento_id,
        version_documento="1.0",
        titulo=titulo,
        contenido="contenido",
        similitud=0.61,
    )


def test_contexto_combina_colecciones():
    a, b = fragmento("eli-006"), fragmento("cal-001")
    elicitacion = Contexto(fragmentos={"elicitacion": (a,)}, descartados=("x",))
    combinado = elicitacion.combinar(Contexto(fragmentos={"criterios_calidad": (b,)}))
    assert combinado.fragmentos == {"elicitacion": (a,), "criterios_calidad": (b,)}
    assert combinado.descartados == ("x",)


def test_referencia_estable_del_fragmento():
    referencia = fragmento("dom-002", "Mutaciones catastrales › Primera clase").referencia
    assert referencia == "dom-002 v1.0 · Mutaciones catastrales › Primera clase"


def estado_completo() -> list:
    """Una instancia de cada partición, con todas las enumeraciones del estado en uso."""
    datos = json.loads((RAIZ / "tests/datos/anexos/anexo_a_rf27.json").read_text(encoding="utf-8"))
    datos.pop("_fuente")
    plantilla = (
        RAIZ / "knowledge_base/arquitecturas_referencia/02-especificacion-de-diseno.md"
    ).read_text(encoding="utf-8")
    especificacion = json.loads(re.search(r"```json\n(.*?)\n```", plantilla, re.S).group(1))
    return [
        Sesion(
            id_sesion="s1",
            cliente="Realtix",
            proyecto="Gestión catastral",
            fase=Fase.DISENO,
            creada=AHORA,
            aprobaciones=(
                AprobacionHumana(
                    punto=PuntoControl.REQUERIMIENTOS,
                    decision=Decision.RECHAZADO,
                    revisor="Analista",
                    observaciones="Falta la regla de redondeo",
                    fecha=AHORA,
                ),
                AprobacionHumana(
                    punto=PuntoControl.FINAL,
                    decision=Decision.RECHAZADO,
                    revisor="Revisor",
                    observaciones="Los avalúos se redondean al múltiplo de mil",
                    destino=Destino.REQUERIMIENTOS,
                    fecha=AHORA,
                ),
                AprobacionHumana(
                    punto=PuntoControl.FINAL,
                    decision=Decision.APROBADO,
                    revisor="Revisor",
                    pruebas_propias=pruebas_propias(),
                    fecha=AHORA,
                ),
            ),
        ),
        Conversacion(
            turnos=(Turno(emisor=Emisor.CLIENTE, texto="Necesito liquidar", fecha=AHORA),),
            turnos_procesados=1,
            registro=registro_completo(resumen_confirmado=True),
            pregunta_pendiente="¿Para qué lo necesita?",
        ),
        Requerimientos(
            requerimientos=(RequerimientoFormal.model_validate(datos),),
            referencias={"RF-27": ("eli-003 v1.1 · Plantilla",)},
            sintesis=2,
            correcciones=1,
            defectos_escalados=("RF-27 · C9 Conforme",),
            enmienda=Enmienda(
                texto="El abono reversado no vuelve a reversarse",
                revisor="Revisor",
                fecha=AHORA,
                observaciones_analista=("Falta el escenario del abono ya reversado",),
                requerimientos={"RF-27": "0.4"},
            ),
            enmiendas=(
                Enmienda(
                    texto="Los avalúos se redondean al múltiplo de mil",
                    revisor="Revisor",
                    fecha=AHORA,
                    requerimientos={"RF-27": "0.3"},
                ),
            ),
        ),
        Arquitectura(
            registro_decision="# ADR",
            especificacion=EspecificacionDiseno.model_validate(especificacion),
            disenos=2,
            correcciones=1,
        ),
        Codigo(versiones=(VersionCodigo(numero=1, archivos={"src/a.py": "x = 1\n"}),)),
        Validacion(
            plan_pruebas=(caso(1),),
            ejecucion=EjecucionPruebas(
                errores_importacion={"dominio.predio": "SyntaxError"},
                pruebas=(
                    PruebaEjecutada(
                        archivo="tests/test_a.py",
                        nombre="test_rf_01_esc_01",
                        resultado=ResultadoPrueba.FALLO,
                        mensaje="AssertionError",
                    ),
                ),
                duracion_ms=700,
            ),
            hallazgos=(
                Hallazgo(
                    regla="CAL-SG-002",
                    severidad=Severidad.ALTA,
                    ubicacion="src/dominio/predio.py:3",
                    descripcion="Uso de eval",
                    sugerencia="Elimina eval",
                    origen="ruff:S307",
                ),
            ),
            conformidad=(
                ConformidadModulo(
                    modulo="dominio.predio", ruta="src/dominio/predio.py", existe=True
                ),
            ),
            no_evaluadas=("CAL-SG-005",),
            veredictos=(veredicto(1, True),),
            veredicto=Veredicto.RECHAZADO,
            retroalimentacion=("[CAL-SG-002 · alta] src/dominio/predio.py:3 · Uso de eval",),
            reporte="# Reporte",
        ),
        Contexto(fragmentos={"criterios_calidad": (fragmento("cal-002", "CAL-MT-001"),)}),
        Control(
            limite_iteraciones=3,
            limite_turnos=15,
            limite_correcciones=2,
            limite_correcciones_diseno=2,
            costo_acumulado_usd=Decimal("0.000825"),
        ),
    ]


def test_particiones_sobreviven_al_serializador(caplog):
    serde = serializador()
    particiones = estado_completo()
    assert {type(particion) for particion in particiones} == set(PARTICIONES)
    with caplog.at_level(logging.WARNING, logger="langgraph"):
        for original in particiones:
            recuperado = serde.loads_typed(serde.dumps_typed(original))
            assert type(recuperado) is type(original)
            assert recuperado == original
    assert not caplog.records, [registro.getMessage() for registro in caplog.records]


def test_lista_blanca_incluye_particiones_y_enumeraciones():
    permitidos = set(tipos_permitidos())
    enumeraciones = (Fase, PuntoControl, Decision, Destino, Emisor, TipoInterfaz)
    for clase in (*PARTICIONES, *enumeraciones, Severidad, Veredicto, ResultadoPrueba):
        assert (clase.__module__, clase.__name__) in permitidos


def test_requerimientos_de_puntos_de_control_anteriores_se_leen_sin_enmiendas():
    # Las sesiones guardadas antes de las enmiendas (ADR-0015) no traen los campos nuevos.
    guardados = Requerimientos(sintesis=1).model_dump(exclude={"enmienda", "enmiendas"})
    leidos = Requerimientos.model_validate(guardados)
    assert leidos.enmienda is None
    assert leidos.enmiendas == ()


def test_version_de_codigo_conserva_el_contenido_tal_cual():
    contenido = '"""Módulo."""\n\n\ndef f() -> None:\n    """Nada."""\n'
    version = VersionCodigo(
        numero=1, archivos={"src/a.py": contenido}, defectos_atendidos=(" D1 ",)
    )
    assert version.archivos["src/a.py"] == contenido
    assert version.defectos_atendidos == ("D1",)


def test_cerca_del_limite_de_turnos_no_se_preguntan_casos_limite():
    from multiagente.orquestador.grafo import _con_reserva_de_turnos

    ahora = datetime.now(UTC)

    def conversacion(turnos_cliente: int) -> Conversacion:
        turnos = tuple(
            Turno(emisor=Emisor.CLIENTE, texto=f"respuesta {n}", fecha=ahora)
            for n in range(turnos_cliente)
        )
        return Conversacion(turnos=turnos, registro=registro_completo())

    limite = 15
    con_margen = _con_reserva_de_turnos(
        conversacion(limite - RESERVA_TURNOS_CONFIRMACION - 1), limite
    )
    assert con_margen.registro.por_preguntar == ["casos_limite", "confirmacion"]
    sin_margen = _con_reserva_de_turnos(conversacion(limite - RESERVA_TURNOS_CONFIRMACION), limite)
    assert sin_margen.registro.casos_limite_cerrados
    assert sin_margen.registro.por_preguntar == ["confirmacion"]
