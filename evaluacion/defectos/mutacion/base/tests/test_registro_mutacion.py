from datetime import date, datetime, timedelta

import pytest

from aplicacion.registro_mutacion import registrar_solicitud_mutacion as registrar_aplicacion
from dominio.solicitud import (
    FechaDocumentoInvalida,
    PredioInexistente,
    SolicitudMutacion,
    TipoDocumentoInvalido,
    validar_fecha_documento_no_posterior,
    validar_tipo_documento,
)
from presentacion.registro_mutacion import registrar_solicitud_mutacion


@pytest.fixture
def contexto():
    guardadas = []
    fechas = []
    consultas = []

    def generar(fecha):
        fechas.append(fecha)
        return f"RAD-{fecha.year:04d}-000123"

    def existe(numero):
        consultas.append(numero)
        return numero == "1" * 30

    datos = {
        "numero_predial": "1" * 30,
        "tipo_documento_soporte": "escritura pública",
        "fecha_documento_soporte": date(2026, 1, 1),
        "identificacion_nuevo_propietario": "123456",
        "nombre_completo_nuevo_propietario": "Persona de prueba",
        "generar_radicado": generar,
        "predio_existe": existe,
        "guardar_solicitud": guardadas.append,
        "fecha_radicacion": date(2026, 1, 2),
    }
    return datos, guardadas, fechas, consultas


def test_rf_01_esc_01_solicitud_aceptada(contexto):
    datos, guardadas, fechas, consultas = contexto
    solicitud = registrar_solicitud_mutacion(**datos)
    assert solicitud.radicado == "RAD-2026-000123"
    assert solicitud.estado == "en trámite"
    assert solicitud.fecha_radicacion == date(2026, 1, 2)
    assert solicitud.numero_predial == datos["numero_predial"]
    assert solicitud.identificacion_nuevo_propietario == "123456"
    assert solicitud.nombre_completo_nuevo_propietario == "Persona de prueba"
    assert guardadas == [solicitud]
    assert guardadas[0] is solicitud
    assert fechas == [date(2026, 1, 2)]
    assert consultas == ["1" * 30]


def test_rf_01_esc_02_sentencia_mismo_dia(contexto):
    datos, guardadas, _, _ = contexto
    datos["tipo_documento_soporte"] = "sentencia judicial"
    datos["fecha_documento_soporte"] = datos["fecha_radicacion"]
    solicitud = registrar_solicitud_mutacion(**datos)
    assert solicitud.radicado == "RAD-2026-000123"
    assert guardadas == [solicitud]


def test_rf_01_esc_03_predio_inexistente(contexto):
    datos, guardadas, fechas, consultas = contexto
    datos["numero_predial"] = "2" * 30
    with pytest.raises(PredioInexistente, match="no existe"):
        registrar_solicitud_mutacion(**datos)
    assert consultas == ["2" * 30]
    assert not guardadas
    assert not fechas


@pytest.mark.parametrize("numero", ["1" * 29, "1" * 31, "a" * 30, "١" * 30, "", None])
def test_numero_predial_invalido_sin_colaboradores(contexto, numero):
    datos, guardadas, fechas, consultas = contexto
    datos["numero_predial"] = numero
    with pytest.raises(PredioInexistente):
        registrar_solicitud_mutacion(**datos)
    assert not guardadas
    assert not fechas
    assert not consultas


@pytest.mark.parametrize("tipo", ["", None, "otro", "Escritura pública"])
def test_tipo_documento_invalido(contexto, tipo):
    datos, guardadas, fechas, consultas = contexto
    datos["tipo_documento_soporte"] = tipo
    with pytest.raises(TipoDocumentoInvalido):
        registrar_solicitud_mutacion(**datos)
    assert not guardadas
    assert not fechas
    assert not consultas


@pytest.mark.parametrize("fecha", [date(2026, 1, 3), None, "2026-01-01", datetime(2026, 1, 1)])
def test_fecha_documento_invalida(contexto, fecha):
    datos, guardadas, fechas, consultas = contexto
    datos["fecha_documento_soporte"] = fecha
    with pytest.raises(FechaDocumentoInvalida):
        registrar_solicitud_mutacion(**datos)
    assert not guardadas
    assert not fechas
    assert not consultas


@pytest.mark.parametrize("campo", [
    "identificacion_nuevo_propietario", "nombre_completo_nuevo_propietario"
])
@pytest.mark.parametrize("valor", ["", "   ", None, 123])
def test_textos_obligatorios(contexto, campo, valor):
    datos, guardadas, _, _ = contexto
    datos[campo] = valor
    with pytest.raises(TipoDocumentoInvalido):
        registrar_solicitud_mutacion(**datos)
    assert not guardadas


@pytest.mark.parametrize(
    "identificacion",
    ["12345", "12345678901", "12345a", "123 45", "123456\n", "١" * 6, "", None, 123456],
)
def test_identificacion_invalida_sin_colaboradores(contexto, identificacion):
    datos, guardadas, fechas, consultas = contexto
    datos["identificacion_nuevo_propietario"] = identificacion
    with pytest.raises(TipoDocumentoInvalido, match="solo dígitos, entre 6 y 10"):
        registrar_solicitud_mutacion(**datos)
    assert not guardadas
    assert not fechas
    assert not consultas


@pytest.mark.parametrize("identificacion", ["000000", "1234567890"])
def test_limites_identificacion(contexto, identificacion):
    datos, guardadas, _, _ = contexto
    datos["identificacion_nuevo_propietario"] = identificacion
    solicitud = registrar_solicitud_mutacion(**datos)
    assert solicitud.identificacion_nuevo_propietario == identificacion
    assert guardadas == [solicitud]


def test_entidad_rechaza_identificacion_invalida(contexto):
    datos, _, _, _ = contexto
    campos = {
        clave: valor
        for clave, valor in datos.items()
        if clave not in ("generar_radicado", "predio_existe", "guardar_solicitud")
    }
    campos.update(
        identificacion_nuevo_propietario="12345a",
        radicado="RAD-2026-000123",
        estado="en trámite",
    )
    with pytest.raises(TipoDocumentoInvalido, match="solo dígitos, entre 6 y 10"):
        SolicitudMutacion(**campos)


def test_fecha_radicacion_invalida(contexto):
    datos, guardadas, _, _ = contexto
    datos["fecha_radicacion"] = "2026-01-02"
    with pytest.raises(FechaDocumentoInvalida):
        registrar_aplicacion(**datos)
    assert not guardadas


def test_fecha_actual_por_defecto(contexto):
    datos, guardadas, fechas, _ = contexto
    datos.pop("fecha_radicacion")
    datos["fecha_documento_soporte"] = date.today() - timedelta(days=1)
    antes = date.today()
    solicitud = registrar_aplicacion(**datos)
    despues = date.today()
    assert antes <= solicitud.fecha_radicacion <= despues
    assert fechas == [solicitud.fecha_radicacion]
    assert guardadas == [solicitud]


@pytest.mark.parametrize("radicado", ["RAD-2025-000123", "RAD-2026-123", "", None])
def test_radicado_invalido_no_se_guarda(contexto, radicado):
    datos, guardadas, _, _ = contexto
    datos["generar_radicado"] = lambda fecha: radicado
    with pytest.raises(TipoDocumentoInvalido):
        registrar_solicitud_mutacion(**datos)
    assert not guardadas


@pytest.mark.parametrize("consecutivo", ["000000", "999999"])
def test_limites_formato_radicado(contexto, consecutivo):
    datos, _, _, _ = contexto
    datos["generar_radicado"] = lambda fecha: f"RAD-{fecha.year:04d}-{consecutivo}"
    assert registrar_aplicacion(**datos).radicado == f"RAD-2026-{consecutivo}"


@pytest.mark.parametrize("campo", ["generar_radicado", "predio_existe", "guardar_solicitud"])
def test_colaborador_no_invocable(contexto, campo):
    datos, guardadas, _, _ = contexto
    datos[campo] = None
    with pytest.raises(TipoDocumentoInvalido):
        registrar_aplicacion(**datos)
    assert not guardadas


def test_validadores_publicos_y_limites_fecha():
    assert validar_tipo_documento("escritura pública") is None
    assert validar_tipo_documento("sentencia judicial") is None
    assert validar_fecha_documento_no_posterior(date.min, date.max) is None
    assert validar_fecha_documento_no_posterior(date.max, date.max) is None
    with pytest.raises(FechaDocumentoInvalida):
        validar_fecha_documento_no_posterior(date.max, date.min)
    with pytest.raises(TipoDocumentoInvalido):
        validar_tipo_documento("contrato")


def test_entidad_valida_y_estado_invalido():
    datos = {
        "numero_predial": "0" * 30,
        "tipo_documento_soporte": "escritura pública",
        "fecha_documento_soporte": date(2026, 1, 2),
        "identificacion_nuevo_propietario": "123456",
        "nombre_completo_nuevo_propietario": "A",
        "fecha_radicacion": date(2026, 1, 2),
        "radicado": "RAD-2026-000001",
        "estado": "en trámite",
    }
    assert SolicitudMutacion(**datos).estado == "en trámite"
    datos["estado"] = "finalizado"
    with pytest.raises(TipoDocumentoInvalido):
        SolicitudMutacion(**datos)
