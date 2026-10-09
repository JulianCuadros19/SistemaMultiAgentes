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
    PARTICIONES,
    AprobacionHumana,
    Arquitectura,
    CasoPrueba,
    Codigo,
    Contexto,
    Control,
    Conversacion,
    Decision,
    Emisor,
    Fase,
    FragmentoContexto,
    PuntoControl,
    RegistroCaptura,
    Requerimientos,
    RespuestaHumana,
    Sesion,
    Turno,
    Validacion,
    VeredictoCaso,
    VersionCodigo,
)
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
    assert registro_completo().pendientes == ["confirmacion"]
    assert registro_completo(resumen_confirmado=True).pendientes == []


def test_confirmacion_exige_registro_completo():
    with pytest.raises(ValidationError, match="confirmarse"):
        registro_completo(excepciones=(), resumen_confirmado=True)


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
    assert Validacion(plan_pruebas=plan, veredictos=veredictos).aprobado is esperado


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
        ),
        Arquitectura(
            registro_decision="# ADR",
            especificacion=EspecificacionDiseno.model_validate(especificacion),
            disenos=2,
            correcciones=1,
        ),
        Codigo(versiones=(VersionCodigo(numero=1, archivos={"src/a.py": "x = 1\n"}),)),
        Validacion(plan_pruebas=(caso(1),), veredictos=(veredicto(1, True),)),
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
    for clase in (*PARTICIONES, Fase, PuntoControl, Decision, Emisor, TipoInterfaz):
        assert (clase.__module__, clase.__name__) in permitidos
