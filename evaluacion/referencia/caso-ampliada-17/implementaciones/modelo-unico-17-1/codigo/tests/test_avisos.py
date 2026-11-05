"""Pruebas de reglas acordadas y decisiones mínimas documentadas."""

from dataclasses import replace
from datetime import date, datetime
from itertools import product
from threading import Event

import pytest

from avisos_catastrales import Aviso, Canal, Sistema, dias_habiles


@pytest.fixture
def sistema():
    instancia = Sistema()
    try:
        yield instancia
    finally:
        instancia.cerrar()


@pytest.fixture
def aviso():
    return Aviso(
        numero="T-0456",
        tipo="mutación",
        estado_anterior="en revisión",
        estado_nuevo="aprobado",
        fecha_hora=datetime(2026, 11, 5, 10, 30),
        funcionario="Marta Pérez",
    )


def test_bitacora_conserva_todos_los_datos_del_ejemplo(sistema, aviso):
    sistema.publicar(aviso)
    sistema.esperar()
    registro, = sistema.bitacora.registros
    assert registro.aviso == aviso
    assert registro.valida


@pytest.mark.parametrize(
    ("anterior", "nuevo", "texto"),
    [
        ("radicado", "en revisión", "Su trámite T-0456 está en revisión"),
        ("en revisión", "aprobado", "Su trámite T-0456 fue aprobado"),
        (
            "en revisión", "rechazado",
            "Su trámite T-0456 fue rechazado; puede consultar el motivo en la oficina",
        ),
    ],
)
def test_transiciones_validas_y_textos(sistema, aviso, anterior, nuevo, texto):
    sistema.indicador.guardar_fecha_radicacion(aviso.numero, date(2026, 11, 2))
    sistema.publicar(replace(aviso, estado_anterior=anterior, estado_nuevo=nuevo))
    sistema.esperar()
    assert sistema.bitacora.registros[0].valida
    assert sistema.mensajes.mensajes[0].numero == "T-0456"
    assert sistema.mensajes.mensajes[0].texto == texto
    assert len(sistema.indicador.mediciones) == (nuevo != "en revisión")
    assert not sistema.canal.fallos


_ESTADOS = ["radicado", "en revisión", "aprobado", "rechazado"]
_INVALIDAS = [
    (anterior, nuevo)
    for anterior, nuevo in product(_ESTADOS, repeat=2)
    if (anterior, nuevo) not in {
        ("radicado", "en revisión"),
        ("en revisión", "aprobado"),
        ("en revisión", "rechazado"),
    }
] + [(None, "radicado"), ("desconocido", "aprobado"), ("radicado", "desconocido")]


@pytest.mark.parametrize(("anterior", "nuevo"), _INVALIDAS)
def test_invalidas_solo_se_registran(sistema, aviso, anterior, nuevo):
    cambiado = replace(aviso, estado_anterior=anterior, estado_nuevo=nuevo)
    sistema.publicar(cambiado)
    sistema.esperar()
    assert sistema.bitacora.registros[0].aviso == cambiado
    assert not sistema.bitacora.registros[0].valida
    assert not sistema.indicador.mediciones
    assert not sistema.mensajes.mensajes
    assert not sistema.canal.fallos


def test_ejemplo_control_cuatro_dias(sistema, aviso):
    sistema.indicador.guardar_fecha_radicacion("T-0001", date(2026, 11, 2))
    sistema.publicar(replace(aviso, numero="T-0001", fecha_hora=datetime(2026, 11, 6)))
    sistema.esperar()
    medicion, = sistema.indicador.mediciones
    assert medicion.fecha_radicacion == date(2026, 11, 2)
    assert medicion.dias == 4
    assert sistema.indicador.promedios == {"mutación": 4.0}


def test_promedios_por_tipo_con_aprobados_y_rechazados(sistema, aviso):
    sistema.indicador.guardar_fecha_radicacion("A", date(2026, 11, 2))
    sistema.indicador.guardar_fecha_radicacion("B", date(2026, 11, 2))
    sistema.indicador.guardar_fecha_radicacion("C", date(2026, 11, 2))
    sistema.publicar(replace(aviso, numero="A", fecha_hora=datetime(2026, 11, 6)))
    sistema.publicar(replace(
        aviso, numero="B", estado_nuevo="rechazado", fecha_hora=datetime(2026, 11, 4)
    ))
    sistema.publicar(replace(
        aviso, numero="C", tipo="desenglobe", fecha_hora=datetime(2026, 11, 3)
    ))
    sistema.esperar()
    assert sistema.indicador.promedios == {"mutación": 3.0, "desenglobe": 1.0}


def test_fecha_faltante_no_impide_bitacora_ni_mensaje(sistema, aviso):
    sistema.publicar(aviso)
    sistema.esperar()
    assert len(sistema.bitacora.registros) == 1
    assert len(sistema.mensajes.mensajes) == 1
    assert not sistema.indicador.mediciones
    fallo, = sistema.canal.fallos
    assert fallo.consumidor == "indicador"
    assert fallo.registro.aviso == aviso
    assert fallo.tipo == "ValueError"
    assert fallo.mensaje == "No hay fecha de radicación para T-0456"
    sistema.indicador.guardar_fecha_radicacion("T-0456", date(2026, 11, 2))
    sistema.esperar()
    assert not sistema.indicador.mediciones  # No hay reintento automático.
    sistema.publicar(aviso)
    sistema.esperar()
    assert len(sistema.indicador.mediciones) == 1  # El trabajador continúa vivo.


def test_duplicados_se_conservan_y_se_cuentan(sistema, aviso):
    sistema.indicador.guardar_fecha_radicacion(aviso.numero, date(2026, 11, 2))
    sistema.publicar(aviso)
    sistema.publicar(aviso)
    sistema.esperar()
    assert len(sistema.bitacora.registros) == 2
    assert len(sistema.mensajes.mensajes) == 2
    assert len(sistema.indicador.mediciones) == 2
    assert sistema.indicador.promedios == {"mutación": 3.0}


def test_publicacion_y_consumidores_no_esperan_al_lento(sistema, aviso):
    iniciado = Event()
    liberar = Event()
    independiente = Event()

    def lento(registro):
        iniciado.set()
        liberar.wait()

    def rapido(registro):
        independiente.set()

    sistema.canal.suscribir("lento", lento)
    sistema.canal.suscribir("rapido", rapido)
    try:
        sistema.publicar(aviso)
        assert iniciado.wait(2)
        assert independiente.wait(2)
        assert not liberar.is_set()
    finally:
        liberar.set()
    sistema.esperar()
    assert len(sistema.bitacora.registros) == 1


def test_fallo_de_consumidor_no_impide_otros_ni_avisos_futuros(sistema, aviso):
    def fallar(registro):
        raise RuntimeError("Servicio no disponible")

    sistema.canal.suscribir("externo", fallar)
    sistema.publicar(aviso)
    sistema.publicar(aviso)
    sistema.esperar()
    fallos = [fallo for fallo in sistema.canal.fallos if fallo.consumidor == "externo"]
    assert len(fallos) == 2
    assert all(fallo.mensaje == "Servicio no disponible" for fallo in fallos)
    assert len(sistema.bitacora.registros) == 2
    assert len(sistema.mensajes.mensajes) == 2


@pytest.mark.parametrize(
    ("inicio", "fin", "esperado"),
    [
        (date(2026, 11, 2), date(2026, 11, 6), 4),
        (date(2026, 10, 30), date(2026, 11, 5), 4),
        (date(2026, 11, 6), date(2026, 11, 9), 1),
        (date(2026, 11, 6), date(2026, 11, 8), 0),
        (date(2026, 11, 2), date(2026, 11, 2), 0),
        (date(2026, 11, 2), date(2026, 11, 16), 10),
        (date(2026, 11, 1), date(2026, 11, 2), 1),
    ],
)
def test_convencion_documentada_de_dias(inicio, fin, esperado):
    assert dias_habiles(inicio, fin) == esperado


def test_fecha_final_anterior_se_aisla(sistema, aviso):
    sistema.indicador.guardar_fecha_radicacion(aviso.numero, date(2026, 11, 6))
    sistema.publicar(aviso)
    sistema.esperar()
    assert sistema.canal.fallos[0].mensaje == "La fecha final es anterior a la radicación"
    assert not sistema.indicador.mediciones
    assert len(sistema.bitacora.registros) == 1
    assert len(sistema.mensajes.mensajes) == 1


@pytest.mark.parametrize(
    ("campo", "valor", "mensaje"),
    [
        ("numero", "", "numero: se requiere texto no vacío"),
        ("tipo", " ", "tipo: se requiere texto no vacío"),
        ("funcionario", None, "funcionario: se requiere texto no vacío"),
        ("estado_nuevo", "", "estado_nuevo: se requiere texto no vacío"),
        ("estado_anterior", 1, "estado_anterior: se requiere texto o None"),
        ("fecha_hora", "2026-11-05 10:30", "fecha_hora: se requiere datetime"),
    ],
)
def test_datos_mal_formados(aviso, campo, valor, mensaje):
    with pytest.raises(ValueError, match=f"^{mensaje}$"):
        replace(aviso, **{campo: valor})


def test_campos_ausentes():
    with pytest.raises(TypeError):
        Aviso(numero="T-0001")


@pytest.mark.parametrize("fecha", ["2026-11-02", datetime(2026, 11, 2), None])
def test_fecha_radicacion_requiere_date(sistema, fecha):
    with pytest.raises(ValueError, match="fecha: se requiere date, sin hora"):
        sistema.indicador.guardar_fecha_radicacion("T-0001", fecha)


def test_numero_radicacion_vacio(sistema):
    with pytest.raises(ValueError, match="numero: se requiere texto no vacío"):
        sistema.indicador.guardar_fecha_radicacion("", date(2026, 11, 2))


def test_fecha_radicacion_puede_corregirse(sistema, aviso):
    sistema.indicador.guardar_fecha_radicacion(aviso.numero, date(2026, 11, 1))
    sistema.indicador.guardar_fecha_radicacion(aviso.numero, date(2026, 11, 2))
    sistema.publicar(aviso)
    sistema.esperar()
    assert sistema.indicador.mediciones[0].dias == 3


def test_dias_rechaza_datetime():
    with pytest.raises(ValueError, match="Las fechas deben ser date, sin hora"):
        dias_habiles(datetime(2026, 11, 2), date(2026, 11, 6))


def test_canal_validaciones_y_cierre(aviso):
    canal = Canal()

    def atender(registro):
        return None

    try:
        with pytest.raises(ValueError, match="nombre: se requiere texto no vacío"):
            canal.suscribir("", atender)
        with pytest.raises(ValueError, match="atender: se requiere una función"):
            canal.suscribir("mal", None)
        canal.suscribir("uno", atender)
        with pytest.raises(ValueError, match="Consumidor ya suscrito: uno"):
            canal.suscribir("uno", atender)
        with pytest.raises(ValueError, match="aviso: se requiere Aviso"):
            canal.publicar(None)
        canal.publicar(aviso)
    finally:
        canal.cerrar()
    canal.cerrar()
    with pytest.raises(RuntimeError, match="El canal está cerrado"):
        canal.publicar(aviso)
    with pytest.raises(RuntimeError, match="El canal está cerrado"):
        canal.suscribir("otro", atender)


def test_cerrar_procesa_pendientes(aviso):
    sistema = Sistema()
    sistema.publicar(aviso)
    sistema.cerrar()
    assert len(sistema.bitacora.registros) == 1
    assert len(sistema.mensajes.mensajes) == 1


def test_resultados_son_instantaneas(sistema, aviso):
    sistema.indicador.guardar_fecha_radicacion(aviso.numero, date(2026, 11, 2))
    anteriores = sistema.bitacora.registros
    sistema.publicar(aviso)
    sistema.esperar()
    assert anteriores == ()
    promedios = sistema.indicador.promedios
    promedios.clear()
    assert sistema.indicador.promedios == {"mutación": 3.0}
