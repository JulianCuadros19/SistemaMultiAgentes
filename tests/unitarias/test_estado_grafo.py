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
from multiagente.core.esquemas.requerimiento import RequerimientoFormal
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


def test_registro_declara_pendientes_en_orden():
    assert RegistroCaptura().pendientes == ["rol", "funcionalidad", "beneficio", "reglas_negocio"]
    parcial = RegistroCaptura(rol="analista", beneficio="ahorrar tiempo")
    assert parcial.pendientes == ["funcionalidad", "reglas_negocio"]
    completo = parcial.model_copy(update={"funcionalidad": "registrar", "reglas_negocio": ("r",)})
    assert completo.pendientes == []


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
        fase="diseno",
        creada=AHORA,
        aprobaciones=(
            aprobacion(PuntoControl.REQUERIMIENTOS, Decision.RECHAZADO),
            aprobacion(PuntoControl.REQUERIMIENTOS, Decision.APROBADO),
        ),
    )
    assert sesion.ultima_aprobacion(PuntoControl.REQUERIMIENTOS).decision is Decision.APROBADO
    assert sesion.ultima_aprobacion(PuntoControl.FINAL) is None


def test_contexto_combina_colecciones():
    elicitacion = Contexto(fragmentos={"elicitacion": ("a",)}, descartados=("x",))
    combinado = elicitacion.combinar(Contexto(fragmentos={"criterios_calidad": ("b",)}))
    assert combinado.fragmentos == {"elicitacion": ("a",), "criterios_calidad": ("b",)}
    assert combinado.descartados == ("x",)


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
            registro=RegistroCaptura(rol="liquidador", reglas_negocio=("regla",)),
            pregunta_pendiente="¿Para qué lo necesita?",
        ),
        Requerimientos(requerimientos=(RequerimientoFormal.model_validate(datos),)),
        Arquitectura(
            registro_decision="# ADR",
            especificacion=EspecificacionDiseno.model_validate(especificacion),
        ),
        Codigo(versiones=(VersionCodigo(numero=1, archivos={"src/a.py": "x = 1\n"}),)),
        Validacion(plan_pruebas=(caso(1),), veredictos=(veredicto(1, True),)),
        Contexto(fragmentos={"criterios_calidad": ("CAL-MT-001",)}),
        Control(limite_iteraciones=3, limite_turnos=15, costo_acumulado_usd=Decimal("0.000825")),
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
