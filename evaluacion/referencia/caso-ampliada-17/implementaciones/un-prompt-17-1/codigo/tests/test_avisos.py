"""Pruebas del dominio y del aislamiento asíncrono."""

from collections.abc import Iterator
from datetime import date, datetime
from threading import Event, Thread

import pytest

from avisos_catastrales import (
    Aviso,
    Bitacora,
    CanalAvisos,
    Estado,
    IndicadorTiempos,
    MensajesCiudadano,
    SistemaAvisos,
    TipoTramite,
    dias_habiles,
)


@pytest.fixture
def sistema() -> Iterator[SistemaAvisos]:
    instancia = SistemaAvisos()
    try:
        yield instancia
    finally:
        instancia.cerrar()


def crear_aviso(
    anterior: Estado = Estado.EN_REVISION,
    nuevo: Estado = Estado.APROBADO,
    numero: str = "T-0001",
    tipo: TipoTramite = TipoTramite.MUTACION,
    dia: int = 6,
) -> Aviso:
    return Aviso(numero, tipo, anterior, nuevo, datetime(2026, 11, dia, 15, 30), "Ana")


@pytest.mark.parametrize("anterior", list(Estado))
@pytest.mark.parametrize("nuevo", list(Estado))
def test_cada_transicion(sistema, anterior, nuevo):
    permitidas = {
        (Estado.RADICADO, Estado.EN_REVISION),
        (Estado.EN_REVISION, Estado.APROBADO),
        (Estado.EN_REVISION, Estado.RECHAZADO),
    }
    valido = (anterior, nuevo) in permitidas
    aviso = crear_aviso(anterior, nuevo)
    sistema.indicador.registrar_radicacion(aviso.numero, date(2026, 11, 2))
    sistema.canal.publicar(aviso)
    sistema.canal.esperar()
    assert aviso.valido is valido
    assert len(sistema.bitacora.registros) == 1
    assert sistema.bitacora.registros[0].aviso == aviso
    assert sistema.bitacora.registros[0].valido is valido
    assert len(sistema.mensajes.mensajes) == int(valido)
    terminal = nuevo in {Estado.APROBADO, Estado.RECHAZADO}
    assert len(sistema.indicador.mediciones) == int(valido and terminal)
    assert sistema.canal.fallos == ()


def test_ejemplo_cliente(sistema):
    sistema.indicador.registrar_radicacion("T-0001", date(2026, 11, 2))
    sistema.canal.publicar(crear_aviso(Estado.RADICADO, Estado.EN_REVISION, dia=3))
    sistema.canal.publicar(crear_aviso())
    sistema.canal.esperar()
    assert sistema.indicador.mediciones[0].dias == 4
    assert sistema.indicador.promedios == {TipoTramite.MUTACION: 4.0}
    assert sistema.mensajes.mensajes[-1].texto == "Su trámite T-0001 fue aprobado"
    assert len(sistema.bitacora.registros) == 2


@pytest.mark.parametrize(
    ("anterior", "nuevo", "texto"),
    [
        (Estado.EN_REVISION, Estado.APROBADO, "Su trámite T-0001 fue aprobado"),
        (
            Estado.EN_REVISION,
            Estado.RECHAZADO,
            "Su trámite T-0001 fue rechazado; puede consultar el motivo en la oficina",
        ),
        (Estado.RADICADO, Estado.EN_REVISION, "Su trámite T-0001 está en revisión"),
    ],
)
def test_textos_exactos(sistema, anterior, nuevo, texto):
    sistema.indicador.registrar_radicacion("T-0001", date(2026, 11, 2))
    sistema.canal.publicar(crear_aviso(anterior, nuevo))
    sistema.canal.esperar()
    assert sistema.mensajes.mensajes[0].numero == "T-0001"
    assert sistema.mensajes.mensajes[0].texto == texto


@pytest.mark.parametrize("tipo", list(TipoTramite))
def test_bitacora_conserva_todos_los_datos(sistema, tipo):
    aviso = crear_aviso(Estado.RADICADO, Estado.EN_REVISION, tipo=tipo)
    sistema.canal.publicar(aviso)
    sistema.canal.esperar()
    registro = sistema.bitacora.registros[0]
    assert registro.aviso == aviso
    assert registro.aviso.numero == "T-0001"
    assert registro.aviso.tipo == tipo
    assert registro.aviso.estado_anterior == Estado.RADICADO
    assert registro.aviso.estado_nuevo == Estado.EN_REVISION
    assert registro.aviso.fecha_hora == datetime(2026, 11, 6, 15, 30)
    assert registro.aviso.funcionario == "Ana"
    assert registro.valido


def test_promedios_separados_por_tipo_y_ambos_terminales(sistema):
    casos = [
        ("M1", TipoTramite.MUTACION, Estado.APROBADO, 6),
        ("M2", TipoTramite.MUTACION, Estado.RECHAZADO, 4),
        ("R1", TipoTramite.RECTIFICACION, Estado.RECHAZADO, 3),
        ("C1", TipoTramite.CERTIFICADO, Estado.APROBADO, 2),
    ]
    for numero, tipo, estado, dia in casos:
        sistema.indicador.registrar_radicacion(numero, date(2026, 11, 2))
        sistema.canal.publicar(crear_aviso(nuevo=estado, numero=numero, tipo=tipo, dia=dia))
    sistema.canal.esperar()
    assert sistema.indicador.promedios == {
        TipoTramite.MUTACION: 3.0,
        TipoTramite.RECTIFICACION: 1.0,
        TipoTramite.CERTIFICADO: 0.0,
    }


@pytest.mark.parametrize(
    ("inicio", "fin", "esperado"),
    [
        (date(2026, 11, 2), date(2026, 11, 6), 4),
        (date(2026, 11, 6), date(2026, 11, 9), 1),
        (date(2026, 11, 7), date(2026, 11, 8), 0),
        (date(2026, 11, 2), date(2026, 11, 2), 0),
        (date(2026, 11, 2), date(2026, 11, 16), 10),
        (date(2026, 11, 1), date(2026, 11, 2), 1),
    ],
)
def test_calendario_lunes_a_viernes(inicio, fin, esperado):
    assert dias_habiles(inicio, fin) == esperado


def test_fecha_final_anterior():
    with pytest.raises(ValueError, match="anterior"):
        dias_habiles(date(2026, 11, 6), date(2026, 11, 2))


def test_falta_radicacion_no_impide_otros_consumidores(sistema):
    sistema.canal.publicar(crear_aviso())
    sistema.canal.esperar()
    assert len(sistema.bitacora.registros) == 1
    assert len(sistema.mensajes.mensajes) == 1
    assert sistema.indicador.mediciones == ()
    assert sistema.indicador.promedios == {}
    assert len(sistema.canal.fallos) == 1
    assert sistema.canal.fallos[0].consumidor == "indicador"
    assert "Falta la fecha" in sistema.canal.fallos[0].descripcion


def test_fecha_incoherente_se_aisla(sistema):
    sistema.indicador.registrar_radicacion("T-0001", date(2026, 11, 9))
    sistema.canal.publicar(crear_aviso())
    sistema.canal.esperar()
    assert len(sistema.bitacora.registros) == 1
    assert len(sistema.mensajes.mensajes) == 1
    assert sistema.indicador.mediciones == ()
    assert "anterior" in sistema.canal.fallos[0].descripcion


@pytest.mark.parametrize("nombre_fallido", ["bitácora", "indicador", "mensajes"])
def test_cualquier_consumidor_puede_fallar_y_continuar(nombre_fallido):
    bitacora = Bitacora()
    indicador = IndicadorTiempos()
    mensajes = MensajesCiudadano()
    indicador.registrar_radicacion("T-0001", date(2026, 11, 2))
    indicador.registrar_radicacion("T-0002", date(2026, 11, 2))
    callbacks = {
        "bitácora": bitacora.procesar,
        "indicador": indicador.procesar,
        "mensajes": mensajes.procesar,
    }
    original = callbacks[nombre_fallido]

    def fallar_una_vez(aviso):
        if aviso.numero == "T-0001":
            raise RuntimeError("Fallo simulado")
        original(aviso)

    callbacks[nombre_fallido] = fallar_una_vez
    canal = CanalAvisos()
    try:
        for nombre, callback in callbacks.items():
            canal.suscribir(nombre, callback, incluir_invalidos=nombre == "bitácora")
        canal.publicar(crear_aviso())
        canal.publicar(crear_aviso(numero="T-0002"))
        canal.esperar()
        assert len(bitacora.registros) == (1 if nombre_fallido == "bitácora" else 2)
        assert len(indicador.mediciones) == (1 if nombre_fallido == "indicador" else 2)
        assert len(mensajes.mensajes) == (1 if nombre_fallido == "mensajes" else 2)
        assert len(canal.fallos) == 1
        assert canal.fallos[0].consumidor == nombre_fallido
        assert canal.fallos[0].aviso == crear_aviso()
        assert canal.fallos[0].descripcion == "RuntimeError: Fallo simulado"
    finally:
        canal.cerrar()


def test_publicador_y_otro_consumidor_no_esperan_al_lento():
    canal = CanalAvisos()
    liberar = Event()
    iniciado = Event()
    rapido = Event()
    publicado = Event()

    def lento(aviso):
        iniciado.set()
        if not liberar.wait(5):
            raise TimeoutError("La prueba no liberó el consumidor")

    def otro(aviso):
        rapido.set()

    def publicar():
        canal.publicar(crear_aviso())
        publicado.set()

    canal.suscribir("lento", lento)
    canal.suscribir("otro", otro)
    productor = Thread(target=publicar, daemon=True)
    productor.start()
    try:
        assert iniciado.wait(2)
        assert publicado.wait(2)
        assert rapido.wait(2)
        assert not liberar.is_set()
    finally:
        liberar.set()
        productor.join()
        canal.cerrar()
    assert canal.fallos == ()


def test_invalidos_no_llegan_a_consumidores_normales():
    canal = CanalAvisos()
    recibidos = []
    bitacora = Bitacora()
    try:
        canal.suscribir("externo", recibidos.append)
        canal.suscribir("bitácora", bitacora.procesar, incluir_invalidos=True)
        aviso = crear_aviso(Estado.APROBADO, Estado.EN_REVISION)
        canal.publicar(aviso)
        canal.esperar()
        assert recibidos == []
        assert bitacora.registros[0].aviso == aviso
        assert not bitacora.registros[0].valido
    finally:
        canal.cerrar()


def test_consumidores_directos_ignoran_invalidos():
    aviso = crear_aviso(Estado.APROBADO, Estado.EN_REVISION)
    indicador = IndicadorTiempos()
    mensajes = MensajesCiudadano()
    indicador.procesar(aviso)
    mensajes.procesar(aviso)
    assert indicador.mediciones == ()
    assert mensajes.mensajes == ()


def test_duplicados_se_procesan_como_avisos_individuales(sistema):
    sistema.indicador.registrar_radicacion("T-0001", date(2026, 11, 2))
    for _ in range(2):
        sistema.canal.publicar(crear_aviso())
    sistema.canal.esperar()
    assert len(sistema.bitacora.registros) == 2
    assert len(sistema.indicador.mediciones) == 2
    assert len(sistema.mensajes.mensajes) == 2


def test_suscripcion_duplicada():
    canal = CanalAvisos()
    try:
        canal.suscribir("bitácora", Bitacora().procesar)
        with pytest.raises(ValueError, match="duplicado"):
            canal.suscribir("bitácora", Bitacora().procesar)
    finally:
        canal.cerrar()


def test_cierre_drena_es_idempotente_y_rechaza_nuevas_operaciones():
    canal = CanalAvisos()
    bitacora = Bitacora()
    canal.suscribir("bitácora", bitacora.procesar, incluir_invalidos=True)
    canal.publicar(crear_aviso())
    canal.cerrar()
    canal.cerrar()
    canal.esperar()
    assert len(bitacora.registros) == 1
    with pytest.raises(RuntimeError, match="cerrado"):
        canal.publicar(crear_aviso())
    with pytest.raises(RuntimeError, match="cerrado"):
        canal.suscribir("otro", bitacora.procesar)
