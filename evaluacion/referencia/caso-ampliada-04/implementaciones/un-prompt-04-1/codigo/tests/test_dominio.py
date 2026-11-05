"""Pruebas de cada regla del dominio sin almacenamiento ni infraestructura."""

from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, timezone

import pytest

from arrendamientos import Contrato, Estado, RechazoContrato, cambiar_estado

MOMENTO = datetime(2026, 1, 1, 12, 30, tzinfo=timezone.utc)


@pytest.fixture
def contrato() -> Contrato:
    return Contrato(
        codigo="CON-1",
        codigo_inmueble="INM-100",
        documento_arrendatario="123456",
        canon_mensual=1_000_000,
        fecha_inicio=date(2026, 1, 1),
        fecha_fin=date(2026, 12, 31),
    )


def test_estados_exactos() -> None:
    assert {estado.value for estado in Estado} == {
        "borrador", "vigente", "terminado", "anulado"
    }


def test_borrador_incompleto_es_valido() -> None:
    nuevo = Contrato("CON-1", "INM-1")
    assert nuevo.estado == Estado.BORRADOR
    assert nuevo.historial == ()


@pytest.mark.parametrize("campo", ["codigo", "codigo_inmueble"])
@pytest.mark.parametrize("valor", ["", "   ", None, 123])
def test_codigos_obligatorios(campo: str, valor: object, contrato: Contrato) -> None:
    with pytest.raises(RechazoContrato, match="código"):
        replace(contrato, **{campo: valor})


@pytest.mark.parametrize("canon", [1.5, 100.0, "100", True])
def test_canon_sin_decimales(canon: object, contrato: Contrato) -> None:
    with pytest.raises(RechazoContrato, match="entero en pesos sin decimales"):
        replace(contrato, canon_mensual=canon)


@pytest.mark.parametrize("campo", ["fecha_inicio", "fecha_fin", "fecha_terminacion"])
@pytest.mark.parametrize("valor", ["2026-01-01", MOMENTO])
def test_fechas_sin_hora(campo: str, valor: object, contrato: Contrato) -> None:
    with pytest.raises(RechazoContrato, match="fecha sin hora"):
        replace(contrato, **{campo: valor})


def test_documento_es_texto(contrato: Contrato) -> None:
    with pytest.raises(RechazoContrato, match="documento.*texto"):
        replace(contrato, documento_arrendatario=123)


def test_estado_debe_ser_enum(contrato: Contrato) -> None:
    with pytest.raises(RechazoContrato, match="valor de Estado"):
        replace(contrato, estado="borrador")


def test_historial_debe_ser_inmutable(contrato: Contrato) -> None:
    with pytest.raises(RechazoContrato, match="tupla"):
        replace(contrato, historial=[])


@pytest.mark.parametrize(
    ("actual", "nuevo"),
    [
        (Estado.BORRADOR, Estado.VIGENTE),
        (Estado.VIGENTE, Estado.TERMINADO),
        (Estado.BORRADOR, Estado.ANULADO),
    ],
)
def test_transiciones_permitidas(
    contrato: Contrato, actual: Estado, nuevo: Estado
) -> None:
    original = replace(contrato, estado=actual)
    resultado = cambiar_estado(
        original,
        nuevo,
        "juridica-1",
        MOMENTO,
        motivo="Mutuo acuerdo",
        fecha_terminacion=date(2026, 6, 15),
    )
    assert resultado.estado == nuevo
    assert original.estado == actual
    cambio = resultado.historial[-1]
    assert cambio.estado_anterior == actual
    assert cambio.estado_nuevo == nuevo
    assert cambio.usuario == "juridica-1"
    assert cambio.momento == MOMENTO


@pytest.mark.parametrize(
    ("actual", "nuevo"),
    [
        (actual, nuevo)
        for actual in Estado
        for nuevo in Estado
        if (actual, nuevo)
        not in {
            (Estado.BORRADOR, Estado.VIGENTE),
            (Estado.VIGENTE, Estado.TERMINADO),
            (Estado.BORRADOR, Estado.ANULADO),
        }
    ],
)
def test_toda_transicion_no_permitida_indica_estado_actual(
    contrato: Contrato, actual: Estado, nuevo: Estado
) -> None:
    original = replace(contrato, estado=actual)
    with pytest.raises(RechazoContrato) as rechazo:
        cambiar_estado(original, nuevo, "juridica", MOMENTO)
    assert f"estado actual {actual.value}" in str(rechazo.value)
    assert original.historial == ()


@pytest.mark.parametrize(
    ("actual", "nuevo"),
    [
        (Estado.BORRADOR, Estado.VIGENTE),
        (Estado.BORRADOR, Estado.ANULADO),
        (Estado.VIGENTE, Estado.TERMINADO),
    ],
)
@pytest.mark.parametrize("usuario", ["", "  ", None])
def test_usuario_obligatorio_en_cada_cambio(
    contrato: Contrato, actual: Estado, nuevo: Estado, usuario: str | None
) -> None:
    with pytest.raises(RechazoContrato, match="usuario.*obligatorio"):
        cambiar_estado(replace(contrato, estado=actual), nuevo, usuario, MOMENTO)


@pytest.mark.parametrize("documento", [None, "", "  "])
def test_arrendatario_obligatorio_para_activar(
    contrato: Contrato, documento: str | None
) -> None:
    with pytest.raises(RechazoContrato, match="documento del arrendatario"):
        cambiar_estado(
            replace(contrato, documento_arrendatario=documento),
            Estado.VIGENTE,
            "juridica",
            MOMENTO,
        )


@pytest.mark.parametrize("canon", [None, 0, -1])
def test_canon_positivo_para_activar(contrato: Contrato, canon: int | None) -> None:
    with pytest.raises(RechazoContrato, match="mayor que cero"):
        cambiar_estado(
            replace(contrato, canon_mensual=canon), Estado.VIGENTE, "juridica", MOMENTO
        )


def test_canon_un_peso_se_acepta(contrato: Contrato) -> None:
    resultado = cambiar_estado(
        replace(contrato, canon_mensual=1), Estado.VIGENTE, "juridica", MOMENTO
    )
    assert resultado.canon_mensual == 1


@pytest.mark.parametrize("campo", ["fecha_inicio", "fecha_fin"])
def test_fechas_obligatorias_para_activar(contrato: Contrato, campo: str) -> None:
    with pytest.raises(RechazoContrato, match="fechas de inicio y fin"):
        cambiar_estado(
            replace(contrato, **{campo: None}), Estado.VIGENTE, "juridica", MOMENTO
        )


@pytest.mark.parametrize("fin", [date(2026, 1, 1), date(2025, 12, 31)])
def test_fin_posterior_al_inicio(contrato: Contrato, fin: date) -> None:
    with pytest.raises(RechazoContrato, match="posterior"):
        cambiar_estado(
            replace(contrato, fecha_fin=fin), Estado.VIGENTE, "juridica", MOMENTO
        )


def test_duracion_inferior_a_seis_meses(contrato: Contrato) -> None:
    with pytest.raises(RechazoContrato, match="seis meses"):
        cambiar_estado(
            replace(contrato, fecha_fin=date(2026, 6, 30)),
            Estado.VIGENTE,
            "juridica",
            MOMENTO,
        )


@pytest.mark.parametrize(
    ("inicio", "fin"),
    [
        (date(2026, 1, 1), date(2026, 7, 1)),
        (date(2026, 8, 31), date(2027, 2, 28)),
        (date(2023, 8, 31), date(2024, 2, 29)),
    ],
)
def test_seis_meses_calendario_exactos(
    contrato: Contrato, inicio: date, fin: date
) -> None:
    resultado = cambiar_estado(
        replace(contrato, fecha_inicio=inicio, fecha_fin=fin),
        Estado.VIGENTE,
        "juridica",
        MOMENTO,
    )
    assert resultado.estado == Estado.VIGENTE


def test_periodo_fuera_del_calendario_rechaza_sin_desbordamiento(contrato: Contrato) -> None:
    with pytest.raises(RechazoContrato, match="seis meses"):
        cambiar_estado(
            replace(contrato, fecha_inicio=date(9999, 8, 1), fecha_fin=date.max),
            Estado.VIGENTE,
            "juridica",
            MOMENTO,
        )


@pytest.mark.parametrize("motivo", [None, "", "  "])
def test_motivo_obligatorio_para_terminar(contrato: Contrato, motivo: str | None) -> None:
    with pytest.raises(RechazoContrato, match="motivo"):
        cambiar_estado(
            replace(contrato, estado=Estado.VIGENTE),
            Estado.TERMINADO,
            "juridica",
            MOMENTO,
            motivo=motivo,
            fecha_terminacion=date(2026, 6, 1),
        )


def test_fecha_terminacion_obligatoria(contrato: Contrato) -> None:
    with pytest.raises(RechazoContrato, match="se requiere una fecha de terminación"):
        cambiar_estado(
            replace(contrato, estado=Estado.VIGENTE),
            Estado.TERMINADO,
            "juridica",
            MOMENTO,
            motivo="Acuerdo",
        )


@pytest.mark.parametrize("fecha", [date(2025, 12, 31), date(2027, 1, 1)])
def test_terminacion_fuera_del_periodo(contrato: Contrato, fecha: date) -> None:
    with pytest.raises(RechazoContrato, match="dentro del periodo"):
        cambiar_estado(
            replace(contrato, estado=Estado.VIGENTE),
            Estado.TERMINADO,
            "juridica",
            MOMENTO,
            motivo="Acuerdo",
            fecha_terminacion=fecha,
        )


@pytest.mark.parametrize(
    "fecha", [date(2026, 1, 1), date(2026, 6, 1), date(2026, 12, 31)]
)
def test_terminacion_dentro_del_periodo_incluye_extremos(
    contrato: Contrato, fecha: date
) -> None:
    resultado = cambiar_estado(
        replace(contrato, estado=Estado.VIGENTE),
        Estado.TERMINADO,
        "juridica",
        MOMENTO,
        motivo="Acuerdo",
        fecha_terminacion=fecha,
    )
    assert resultado.fecha_terminacion == fecha
    assert resultado.motivo_terminacion == "Acuerdo"
    assert resultado.historial[-1].fecha_terminacion == fecha
    assert resultado.historial[-1].motivo == "Acuerdo"
    assert resultado.fecha_fin == contrato.fecha_fin


def test_fecha_terminacion_no_admite_hora(contrato: Contrato) -> None:
    with pytest.raises(RechazoContrato, match="fecha sin hora"):
        cambiar_estado(
            replace(contrato, estado=Estado.VIGENTE),
            Estado.TERMINADO,
            "juridica",
            MOMENTO,
            motivo="Acuerdo",
            fecha_terminacion=MOMENTO,
        )


def test_anular_no_exige_datos_de_activacion() -> None:
    resultado = cambiar_estado(
        Contrato("CON-1", "INM-1"), Estado.ANULADO, "juridica", MOMENTO
    )
    assert resultado.estado == Estado.ANULADO
    assert len(resultado.historial) == 1


def test_modelo_no_se_modifica_desde_fuera(contrato: Contrato) -> None:
    with pytest.raises(FrozenInstanceError):
        contrato.estado = Estado.VIGENTE


def test_momento_debe_incluir_fecha_y_hora(contrato: Contrato) -> None:
    with pytest.raises(RechazoContrato, match="fecha y hora"):
        cambiar_estado(contrato, Estado.ANULADO, "juridica", date(2026, 1, 1))


def test_estado_solicitado_debe_ser_enum(contrato: Contrato) -> None:
    with pytest.raises(RechazoContrato, match="estado solicitado"):
        cambiar_estado(contrato, "vigente", "juridica", MOMENTO)
