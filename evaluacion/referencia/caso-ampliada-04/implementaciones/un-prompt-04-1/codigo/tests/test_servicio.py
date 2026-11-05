"""Pruebas de persistencia, auditoría, rechazos y exclusión entre hilos."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import date, datetime, timezone
from threading import Barrier

import pytest

from arrendamientos import (
    Contrato,
    Estado,
    RechazoContrato,
    RepositorioEnMemoria,
    ServicioContratos,
)

MOMENTO = datetime(2026, 1, 1, 10, 15, tzinfo=timezone.utc)


@pytest.fixture
def servicio() -> ServicioContratos:
    resultado = ServicioContratos(RepositorioEnMemoria(), reloj=lambda: MOMENTO)
    resultado.registrar(
        Contrato(
            "CON-1", "INM-100", "111", 500_000, date(2026, 1, 1), date(2026, 12, 31)
        )
    )
    return resultado


def test_historial_acumula_cada_cambio_con_usuario_y_fecha(
    servicio: ServicioContratos,
) -> None:
    inicial = servicio.obtener("CON-1")
    activado = servicio.cambiar_estado("CON-1", Estado.VIGENTE, "abogada-1")
    terminado = servicio.cambiar_estado(
        "CON-1", Estado.TERMINADO, "abogado-2",
        motivo="Acuerdo", fecha_terminacion=date(2026, 6, 1),
    )
    assert inicial.estado == Estado.BORRADOR
    assert inicial.historial == ()
    assert activado.estado == Estado.VIGENTE
    assert len(activado.historial) == 1
    assert len(terminado.historial) == 2
    assert [c.usuario for c in terminado.historial] == ["abogada-1", "abogado-2"]
    assert all(c.momento == MOMENTO for c in terminado.historial)
    assert servicio.obtener("CON-1") == terminado


def test_rechazo_no_persiste_cambios_ni_historial(servicio: ServicioContratos) -> None:
    anterior = servicio.cambiar_estado("CON-1", Estado.VIGENTE, "juridica")
    with pytest.raises(RechazoContrato, match="motivo"):
        servicio.cambiar_estado("CON-1", Estado.TERMINADO, "juridica")
    assert servicio.obtener("CON-1") == anterior


def test_transicion_rechazada_no_modifica_borrador(servicio: ServicioContratos) -> None:
    anterior = servicio.obtener("CON-1")
    with pytest.raises(RechazoContrato, match="estado actual borrador"):
        servicio.cambiar_estado("CON-1", Estado.TERMINADO, "juridica")
    assert servicio.obtener("CON-1") == anterior


def test_codigo_duplicado_no_sobrescribe(servicio: ServicioContratos) -> None:
    anterior = servicio.obtener("CON-1")
    with pytest.raises(RechazoContrato, match="Ya existe"):
        servicio.registrar(Contrato("CON-1", "OTRO-INMUEBLE"))
    assert servicio.obtener("CON-1") == anterior


@pytest.mark.parametrize("operacion", ["obtener", "cambiar"])
def test_codigo_inexistente(servicio: ServicioContratos, operacion: str) -> None:
    with pytest.raises(RechazoContrato, match="No existe el contrato AUSENTE"):
        if operacion == "obtener":
            servicio.obtener("AUSENTE")
        else:
            servicio.cambiar_estado("AUSENTE", Estado.VIGENTE, "juridica")


@pytest.mark.parametrize("estado", [Estado.VIGENTE, Estado.TERMINADO, Estado.ANULADO])
def test_registro_solo_de_borradores_nuevos(
    servicio: ServicioContratos, estado: Estado
) -> None:
    with pytest.raises(RechazoContrato, match="borradores nuevos"):
        servicio.registrar(Contrato("CON-2", "INM-200", estado=estado))


def test_registro_no_importa_historial(servicio: ServicioContratos) -> None:
    activado = servicio.cambiar_estado("CON-1", Estado.VIGENTE, "juridica")
    with pytest.raises(RechazoContrato, match="sin historial"):
        servicio.registrar(replace(activado, codigo="CON-2", estado=Estado.BORRADOR))


def test_terminar_libera_el_bloqueo_de_activacion(servicio: ServicioContratos) -> None:
    servicio.cambiar_estado("CON-1", Estado.VIGENTE, "juridica")
    servicio.cambiar_estado(
        "CON-1", Estado.TERMINADO, "juridica",
        motivo="Acuerdo", fecha_terminacion=date(2026, 6, 1),
    )
    servicio.registrar(
        Contrato(
            "CON-2", "INM-100", "222", 500_000, date(2026, 6, 1), date(2027, 6, 1)
        )
    )
    assert servicio.cambiar_estado("CON-2", Estado.VIGENTE, "juridica").estado == Estado.VIGENTE


def test_reloj_predeterminado_registra_utc() -> None:
    servicio = ServicioContratos(RepositorioEnMemoria())
    servicio.registrar(Contrato("CON-1", "INM-1"))
    resultado = servicio.cambiar_estado("CON-1", Estado.ANULADO, "juridica")
    assert resultado.historial[-1].momento.tzinfo == timezone.utc


def test_transformacion_no_puede_cambiar_identidad() -> None:
    repositorio = RepositorioEnMemoria()
    anterior = repositorio.agregar(Contrato("CON-1", "INM-1"))

    def transformar(actual: Contrato, contratos: tuple[Contrato, ...]) -> Contrato:
        return replace(actual, codigo_inmueble="INM-2")

    with pytest.raises(RechazoContrato, match="no puede cambiar los códigos"):
        repositorio.actualizar("CON-1", transformar)
    assert repositorio.obtener("CON-1") == anterior


def test_activaciones_competidoras_son_atomicas() -> None:
    repositorio = RepositorioEnMemoria()
    servicio = ServicioContratos(repositorio, reloj=lambda: MOMENTO)
    for codigo in ("CON-1", "CON-2"):
        servicio.registrar(
            Contrato(
                codigo, "INM-100", codigo, 500_000,
                date(2026, 1, 1), date(2026, 12, 31),
            )
        )
    barrera = Barrier(2)

    def activar(codigo: str) -> Contrato | RechazoContrato:
        barrera.wait(timeout=10)
        try:
            return servicio.cambiar_estado(codigo, Estado.VIGENTE, "juridica")
        except RechazoContrato as rechazo:
            return rechazo

    with ThreadPoolExecutor(max_workers=2) as ejecutor:
        resultados = list(ejecutor.map(activar, ("CON-1", "CON-2")))
    assert sum(isinstance(resultado, Contrato) for resultado in resultados) == 1
    rechazos = [resultado for resultado in resultados if isinstance(resultado, RechazoContrato)]
    assert len(rechazos) == 1
    assert str(rechazos[0]) == "El inmueble ya tiene un contrato vigente en ese periodo"
    guardados = [servicio.obtener(codigo) for codigo in ("CON-1", "CON-2")]
    assert sum(contrato.estado == Estado.VIGENTE for contrato in guardados) == 1
    assert sum(len(contrato.historial) for contrato in guardados) == 1
