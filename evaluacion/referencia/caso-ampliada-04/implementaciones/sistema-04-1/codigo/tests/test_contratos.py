"""Pruebas de aceptación y límites del ciclo de vida de contratos."""

from dataclasses import FrozenInstanceError
from datetime import date
from decimal import Decimal

import pytest

from adaptadores.salida.repositorios_memoria import RepositorioContratosMemoria
from aplicacion.contratos import activar_contrato, cambiar_estado, terminar_contrato
from dominio.contratos import (
    CanonInvalido,
    Contrato,
    CruceDeVigencias,
    DocumentoArrendatarioObligatorio,
    EstadoNoModificable,
    FechaTerminacionFueraDePeriodo,
    FechasInvalidas,
    MotivoObligatorio,
    TransicionNoPermitida,
)


def _preparar(codigo, estado="borrador", inmueble="INM-100", documento="DOC-1"):
    repo = RepositorioContratosMemoria()
    contrato = Contrato(
        codigo, inmueble, date(2026, 1, 1), date(2026, 12, 31), documento,
        Decimal("1200000"), estado,
    )
    repo.registrar(contrato)
    return repo


def _activar(repo, codigo, **cambios):
    datos = {
        "codigo": codigo,
        "inmueble": "INM-100",
        "fecha_inicio": date(2026, 1, 1),
        "fecha_fin": date(2026, 12, 31),
        "documento_arrendatario": "DOC-1",
        "canon_mensual": Decimal("1200000"),
        "usuario": "operador",
        "repo": repo,
    }
    datos.update(cambios)
    return activar_contrato(**datos)


def _verificar_resultado(resultado, repo, codigo, estado):
    assert resultado.contrato == repo.consultar_por_codigo(codigo)
    assert resultado.contrato.estado == estado
    assert resultado.usuario == "operador"
    assert resultado.fecha_cambio == date.today()


def test_rf_01_esc_01_activacion_exitosa():
    repo = _preparar("C-100")
    resultado = _activar(repo, "C-100")
    _verificar_resultado(resultado, repo, "C-100", "vigente")
    assert resultado.contrato.canon_mensual == Decimal("1200000")


def test_rf_01_esc_02_documento_obligatorio():
    repo = _preparar("C-101", inmueble="INM-101", documento=None)
    anterior = repo.consultar_por_codigo("C-101")
    with pytest.raises(DocumentoArrendatarioObligatorio, match="documento.*obligatorio"):
        _activar(
            repo, "C-101", inmueble="INM-101", documento_arrendatario=None,
            canon_mensual=Decimal("900000"),
        )
    assert repo.consultar_por_codigo("C-101") == anterior


def test_rf_01_esc_03_fecha_incorrecta():
    repo = _preparar("C-102")
    anterior = repo.consultar_por_codigo("C-102")
    with pytest.raises(FechasInvalidas, match="posterior"):
        _activar(
            repo, "C-102", fecha_inicio=date(2026, 12, 31), fecha_fin=date(2026, 1, 1),
            canon_mensual=Decimal("800000"),
        )
    assert repo.consultar_por_codigo("C-102") == anterior


def test_rf_01_esc_04_cruce_de_contratos():
    repo = _preparar("C-100", "vigente")
    borrador = Contrato(
        "C-103", "INM-100", date(2026, 1, 1), date(2026, 12, 31), "DOC-2",
        Decimal("1200000"), "borrador",
    )
    repo.registrar(borrador)
    with pytest.raises(CruceDeVigencias, match="El inmueble ya tiene un contrato vigente"):
        _activar(repo, "C-103")
    assert repo.consultar_por_codigo("C-103") == borrador
    assert repo.consultar_por_codigo("C-100").estado == "vigente"


def test_rf_02_esc_01_terminacion_exitosa():
    repo = _preparar("C-200", "vigente")
    resultado = terminar_contrato("C-200", "vencimiento", date(2026, 8, 15), "operador", repo)
    _verificar_resultado(resultado, repo, "C-200", "terminado")


def test_rf_02_esc_02_motivo_obligatorio():
    repo = _preparar("C-201", "vigente")
    anterior = repo.consultar_por_codigo("C-201")
    with pytest.raises(MotivoObligatorio, match="motivo es obligatorio"):
        terminar_contrato("C-201", None, date(2026, 8, 15), "operador", repo)
    assert repo.consultar_por_codigo("C-201") == anterior


def test_rf_02_esc_03_fecha_fuera_del_periodo():
    repo = _preparar("C-202", "vigente")
    anterior = repo.consultar_por_codigo("C-202")
    with pytest.raises(FechaTerminacionFueraDePeriodo, match="dentro del periodo"):
        terminar_contrato("C-202", "vencimiento", date(2027, 1, 1), "operador", repo)
    assert repo.consultar_por_codigo("C-202") == anterior


def test_rf_02_esc_04_estado_anulado():
    repo = _preparar("C-203", "anulado")
    anterior = repo.consultar_por_codigo("C-203")
    with pytest.raises(EstadoNoModificable, match="estado actual del contrato es anulado"):
        terminar_contrato("C-203", "vencimiento", date(2026, 8, 15), "operador", repo)
    assert repo.consultar_por_codigo("C-203") == anterior


def test_rf_03_esc_01_borrador_a_anulado():
    repo = _preparar("C-300")
    resultado = cambiar_estado("C-300", "anulado", "operador", repo)
    _verificar_resultado(resultado, repo, "C-300", "anulado")


def test_rf_03_esc_02_vigente_a_terminado():
    repo = _preparar("C-301", "vigente")
    resultado = cambiar_estado("C-301", "terminado", "operador", repo)
    _verificar_resultado(resultado, repo, "C-301", "terminado")


def test_rf_03_esc_03_transicion_no_permitida():
    repo = _preparar("C-302")
    anterior = repo.consultar_por_codigo("C-302")
    with pytest.raises(TransicionNoPermitida, match="estado actual del contrato es borrador"):
        cambiar_estado("C-302", "terminado", "operador", repo)
    assert repo.consultar_por_codigo("C-302") == anterior


def test_rf_03_esc_04_estado_final():
    repo = _preparar("C-303", "terminado")
    anterior = repo.consultar_por_codigo("C-303")
    with pytest.raises(EstadoNoModificable, match="estado actual del contrato es terminado"):
        cambiar_estado("C-303", "vigente", "operador", repo)
    assert repo.consultar_por_codigo("C-303") == anterior


@pytest.mark.parametrize("canon", ["0", "-1", "0.01", "1200000.50", "NaN", "Infinity"])
def test_canon_invalido_no_modifica(canon):
    repo = _preparar("C-1")
    anterior = repo.consultar_por_codigo("C-1")
    with pytest.raises(CanonInvalido):
        _activar(repo, "C-1", canon_mensual=Decimal(canon))
    assert repo.consultar_por_codigo("C-1") == anterior


@pytest.mark.parametrize("canon", ["1", "1.00", "1200000"])
def test_canon_entero_positivo(canon):
    repo = _preparar("C-1")
    resultado = _activar(repo, "C-1", canon_mensual=Decimal(canon))
    assert resultado.contrato.canon_mensual == Decimal(canon)
    assert repo.consultar_por_codigo("C-1").estado == "vigente"


@pytest.mark.parametrize(
    ("inicio", "fin", "valido"),
    [
        (date(2026, 1, 1), date(2026, 7, 1), True),
        (date(2026, 1, 1), date(2026, 6, 30), False),
        (date(2026, 1, 1), date(2026, 1, 1), False),
        (date(2026, 8, 31), date(2027, 2, 28), True),
        (date(2027, 8, 31), date(2028, 2, 29), True),
        (date(9999, 1, 1), date(9999, 7, 1), True),
        (date(9999, 8, 1), date(9999, 12, 31), False),
    ],
)
def test_duracion_seis_meses_calendario(inicio, fin, valido):
    repo = _preparar("C-1")
    if valido:
        resultado = _activar(repo, "C-1", fecha_inicio=inicio, fecha_fin=fin)
        assert resultado.contrato.fecha_inicio == inicio
        assert repo.consultar_por_codigo("C-1").fecha_fin == fin
    else:
        with pytest.raises(FechasInvalidas):
            _activar(repo, "C-1", fecha_inicio=inicio, fecha_fin=fin)
        assert repo.consultar_por_codigo("C-1").estado == "borrador"


@pytest.mark.parametrize("fecha", [date(2026, 1, 1), date(2026, 12, 31)])
def test_terminacion_extremos_incluidos(fecha):
    repo = _preparar("C-1", "vigente")
    resultado = terminar_contrato("C-1", "vencimiento", fecha, "operador", repo)
    _verificar_resultado(resultado, repo, "C-1", "terminado")
    assert resultado.contrato.fecha_fin == date(2026, 12, 31)


@pytest.mark.parametrize("motivo", ["", "   "])
def test_motivo_vacio(motivo):
    repo = _preparar("C-1", "vigente")
    with pytest.raises(MotivoObligatorio):
        terminar_contrato("C-1", motivo, date(2026, 8, 15), "operador", repo)
    assert repo.consultar_por_codigo("C-1").estado == "vigente"


@pytest.mark.parametrize("documento", ["", "   "])
def test_documento_vacio(documento):
    repo = _preparar("C-1")
    with pytest.raises(DocumentoArrendatarioObligatorio):
        _activar(repo, "C-1", documento_arrendatario=documento)
    assert repo.consultar_por_codigo("C-1").estado == "borrador"


@pytest.mark.parametrize("campo", ["codigo", "usuario", "inmueble"])
@pytest.mark.parametrize("valor", ["", "   "])
def test_identificadores_obligatorios(campo, valor):
    repo = _preparar("C-1")
    datos = {
        "codigo": "C-1", "inmueble": "INM-100", "fecha_inicio": date(2026, 1, 1),
        "fecha_fin": date(2026, 12, 31), "documento_arrendatario": "DOC-1",
        "canon_mensual": Decimal("1"), "usuario": "operador", "repo": repo,
    }
    datos[campo] = valor
    with pytest.raises(TransicionNoPermitida, match="obligatorio"):
        activar_contrato(**datos)
    assert repo.consultar_por_codigo("C-1").estado == "borrador"


@pytest.mark.parametrize("estado", ["terminado", "anulado"])
def test_activar_estado_final(estado):
    repo = _preparar("C-1", estado)
    with pytest.raises(EstadoNoModificable, match=estado):
        _activar(repo, "C-1")
    assert repo.consultar_por_codigo("C-1").estado == estado


def test_cambiar_estado_borrador_a_vigente():
    repo = _preparar("C-1")
    resultado = cambiar_estado("C-1", "vigente", "operador", repo)
    _verificar_resultado(resultado, repo, "C-1", "vigente")


@pytest.mark.parametrize("nuevo", ["borrador", "desconocido", ""])
def test_transiciones_invalidas(nuevo):
    repo = _preparar("C-1")
    with pytest.raises(TransicionNoPermitida, match="borrador"):
        cambiar_estado("C-1", nuevo, "operador", repo)
    assert repo.consultar_por_codigo("C-1").estado == "borrador"


@pytest.mark.parametrize(
    ("inmueble", "desde", "hasta", "esperado"),
    [
        ("INM-100", date(2026, 12, 31), date(2027, 7, 1), True),
        ("INM-100", date(2027, 1, 1), date(2027, 7, 1), False),
        ("INM-100", date(2025, 1, 1), date(2026, 1, 1), True),
        ("INM-200", date(2026, 1, 1), date(2026, 12, 31), False),
    ],
)
def test_consulta_cruces_extremos_e_inmueble(inmueble, desde, hasta, esperado):
    repo = _preparar("C-1", "vigente")
    assert repo.existe_vigencia_en_inmueble(inmueble, desde, hasta) is esperado


@pytest.mark.parametrize("estado", ["borrador", "terminado", "anulado"])
def test_estados_no_vigentes_no_cruzan(estado):
    repo = _preparar("C-1", estado)
    assert not repo.existe_vigencia_en_inmueble("INM-100", date(2026, 1, 1), date(2026, 12, 31))


def test_repositorios_independientes_y_contratos_inmutables():
    primero = _preparar("C-1")
    segundo = RepositorioContratosMemoria()
    with pytest.raises(KeyError):
        segundo.consultar_por_codigo("C-1")
    contrato = primero.consultar_por_codigo("C-1")
    with pytest.raises(FrozenInstanceError):
        contrato.estado = "vigente"
    assert primero.consultar_por_codigo("C-1").estado == "borrador"
    with pytest.raises(KeyError):
        segundo.actualizar(contrato)
