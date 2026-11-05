"""Ejemplos del cliente y casos de intersección de periodos."""

from dataclasses import replace
from datetime import date, datetime, timezone

import pytest

from arrendamientos import (
    Contrato,
    Estado,
    RechazoContrato,
    RepositorioEnMemoria,
    ServicioContratos,
    cambiar_estado,
)

MOMENTO = datetime(2026, 1, 1, tzinfo=timezone.utc)
MENSAJE = "El inmueble ya tiene un contrato vigente en ese periodo"


@pytest.fixture
def vigente() -> Contrato:
    borrador = Contrato(
        "CON-1", "INM-100", "111", 500_000, date(2026, 1, 1), date(2026, 12, 31)
    )
    return cambiar_estado(borrador, Estado.VIGENTE, "juridica", MOMENTO)


def test_ejemplo_del_cliente_rechaza_y_activa_periodo_siguiente() -> None:
    servicio = ServicioContratos(RepositorioEnMemoria(), reloj=lambda: MOMENTO)
    servicio.registrar(
        Contrato(
            "CON-1", "INM-100", "111", 500_000, date(2026, 1, 1), date(2026, 12, 31)
        )
    )
    servicio.cambiar_estado("CON-1", Estado.VIGENTE, "juridica")
    segundo = servicio.registrar(
        Contrato(
            "CON-2", "INM-100", "222", 600_000, date(2026, 6, 1), date(2027, 5, 31)
        )
    )
    with pytest.raises(RechazoContrato) as rechazo:
        servicio.cambiar_estado("CON-2", Estado.VIGENTE, "juridica")
    assert str(rechazo.value) == MENSAJE
    assert servicio.obtener("CON-2") == segundo
    servicio.registrar(
        Contrato(
            "CON-3", "INM-100", "333", 700_000, date(2027, 1, 1), date(2027, 12, 31)
        )
    )
    assert servicio.cambiar_estado("CON-3", Estado.VIGENTE, "juridica").estado == Estado.VIGENTE


@pytest.mark.parametrize(
    ("inicio", "fin"),
    [
        (date(2026, 1, 1), date(2026, 12, 31)),
        (date(2026, 2, 1), date(2026, 8, 1)),
        (date(2025, 6, 1), date(2027, 6, 1)),
        (date(2025, 6, 1), date(2026, 1, 1)),
        (date(2026, 12, 31), date(2027, 12, 31)),
    ],
)
def test_cruces_incluyen_contencion_e_igualdad_de_extremos(
    vigente: Contrato, inicio: date, fin: date
) -> None:
    otro = replace(vigente, codigo="CON-2", estado=Estado.BORRADOR, historial=(),
                   fecha_inicio=inicio, fecha_fin=fin)
    with pytest.raises(RechazoContrato) as rechazo:
        cambiar_estado(otro, Estado.VIGENTE, "juridica", MOMENTO, contratos=(vigente,))
    assert str(rechazo.value) == MENSAJE


@pytest.mark.parametrize(
    ("inicio", "fin"),
    [
        (date(2025, 1, 1), date(2025, 12, 31)),
        (date(2027, 1, 1), date(2027, 12, 31)),
    ],
)
def test_periodos_separados_se_aceptan(vigente: Contrato, inicio: date, fin: date) -> None:
    otro = replace(vigente, codigo="CON-2", estado=Estado.BORRADOR, historial=(),
                   fecha_inicio=inicio, fecha_fin=fin)
    resultado = cambiar_estado(
        otro, Estado.VIGENTE, "juridica", MOMENTO, contratos=(vigente,)
    )
    assert resultado.estado == Estado.VIGENTE


def test_otro_inmueble_no_impide_activacion(vigente: Contrato) -> None:
    otro = replace(
        vigente, codigo="CON-2", codigo_inmueble="INM-200", estado=Estado.BORRADOR, historial=()
    )
    resultado = cambiar_estado(
        otro, Estado.VIGENTE, "juridica", MOMENTO, contratos=(vigente,)
    )
    assert resultado.estado == Estado.VIGENTE


@pytest.mark.parametrize("estado", [Estado.BORRADOR, Estado.TERMINADO, Estado.ANULADO])
def test_solo_los_vigentes_bloquean(vigente: Contrato, estado: Estado) -> None:
    competidor = replace(vigente, estado=estado)
    otro = replace(vigente, codigo="CON-2", estado=Estado.BORRADOR, historial=())
    resultado = cambiar_estado(
        otro, Estado.VIGENTE, "juridica", MOMENTO, contratos=(competidor,)
    )
    assert resultado.estado == Estado.VIGENTE


def test_se_revisan_todos_los_competidores(vigente: Contrato) -> None:
    distinto = replace(vigente, codigo="CON-X", codigo_inmueble="INM-200")
    otro = replace(vigente, codigo="CON-2", estado=Estado.BORRADOR, historial=())
    with pytest.raises(RechazoContrato, match=MENSAJE):
        cambiar_estado(
            otro, Estado.VIGENTE, "juridica", MOMENTO, contratos=iter((distinto, vigente))
        )


def test_vigente_con_periodo_incompleto_no_se_ignora(vigente: Contrato) -> None:
    corrupto = replace(vigente, fecha_fin=None)
    otro = replace(vigente, codigo="CON-2", estado=Estado.BORRADOR, historial=())
    with pytest.raises(RechazoContrato, match="periodo incompleto"):
        cambiar_estado(otro, Estado.VIGENTE, "juridica", MOMENTO, contratos=(corrupto,))
