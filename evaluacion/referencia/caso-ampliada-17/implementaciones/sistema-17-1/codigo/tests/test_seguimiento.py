from datetime import date, datetime
from decimal import Decimal

import pytest

from consumidores.bitacora import BitacoraConsumidor
from consumidores.falla import ConsumidorFalla
from consumidores.indicador import IndicadorConsumidor
from consumidores.mensajes import MensajesConsumidor
from eventos.aviso import AvisoCambioEstado
from infraestructura.bitacora_memoria import RegistroBitacoraMemoria
from infraestructura.calendario_tramite_memoria import RegistroFechasTramiteMemoria
from infraestructura.canal_memoria import CanalEventosMemoria
from infraestructura.indicadores_memoria import RegistroIndicadoresMemoria
from infraestructura.mensajes_memoria import RegistroMensajesMemoria
from productores.cambios_estado import publicar_cambio_estado


def _publicar(canal, anterior="en revisión", nuevo="aprobado", numero="T-0001", dia=6):
    return publicar_cambio_estado(
        canal, numero, "mutación", anterior, nuevo, datetime(2026, 11, dia, 10, 30), "F-01"
    )


def _bitacora():
    canal = CanalEventosMemoria()
    registro = RegistroBitacoraMemoria()
    consumidor = BitacoraConsumidor(registro)
    canal.suscribir(consumidor.manejar)
    return canal, registro


def _indicador():
    canal = CanalEventosMemoria()
    registro = RegistroIndicadoresMemoria()
    fechas = RegistroFechasTramiteMemoria()
    consumidor = IndicadorConsumidor(registro, fechas)
    canal.suscribir(consumidor.manejar)
    return canal, registro, fechas


def _mensaje(numero, anterior, nuevo):
    canal = CanalEventosMemoria()
    registro = RegistroMensajesMemoria()
    consumidor = MensajesConsumidor(registro)
    canal.suscribir(consumidor.manejar)
    _publicar(canal, anterior, nuevo, numero)
    assert registro.consultar_por_tramite(numero) == []
    canal.despachar_pendientes()
    return registro.consultar_por_tramite(numero)


def test_rf_01_esc_01_publicacion_completa():
    canal = CanalEventosMemoria()
    aviso = _publicar(canal, "radicado", "en revisión")
    assert aviso.numero_tramite == "T-0001"
    assert aviso.tipo_tramite == "mutación"
    assert aviso.estado_anterior == "radicado"
    assert aviso.estado_nuevo == "en revisión"
    assert aviso.fecha_hora == datetime(2026, 11, 6, 10, 30)
    assert aviso.funcionario == "F-01"
    assert aviso.es_valida is True
    assert canal.obtener_pendientes() == [aviso]


def test_rf_01_esc_02_reaccion_separada():
    canal = CanalEventosMemoria()
    registro = RegistroBitacoraMemoria()
    canal.suscribir(BitacoraConsumidor(registro).manejar)
    aviso = _publicar(canal)
    assert canal.obtener_pendientes() == [aviso]
    assert registro.consultar_por_tramite("T-0001") == []
    canal.despachar_pendientes()
    assert len(registro.consultar_por_tramite("T-0001")) == 1


def test_rf_01_esc_03_transicion_invalida():
    canal, registro = _bitacora()
    mensajes = RegistroMensajesMemoria()
    indicadores = RegistroIndicadoresMemoria()
    fechas = RegistroFechasTramiteMemoria()
    fechas.registrar_radicado("T-0001", date(2026, 11, 2))
    canal.suscribir(MensajesConsumidor(mensajes).manejar)
    canal.suscribir(IndicadorConsumidor(indicadores, fechas).manejar)
    aviso = _publicar(canal, "aprobado", "en revisión")
    canal.despachar_pendientes()
    assert aviso.es_valida is False
    assert registro.consultar_por_tramite("T-0001")[0].transicion_valida is False
    assert mensajes.consultar_por_tramite("T-0001") == []
    assert indicadores.consultar_dias_calculados("T-0001") is None
    assert indicadores.promedio_por_tipo("mutación") == Decimal(0)


def test_rf_02_esc_01_asiento_completo():
    canal, registro = _bitacora()
    aviso = _publicar(canal)
    canal.despachar_pendientes()
    asientos = registro.consultar_por_tramite("T-0001")
    assert len(asientos) == 1
    asiento = asientos[0]
    assert asiento.numero_tramite == aviso.numero_tramite
    assert asiento.tipo_tramite == aviso.tipo_tramite
    assert asiento.estado_anterior == aviso.estado_anterior
    assert asiento.estado_nuevo == aviso.estado_nuevo
    assert asiento.fecha_hora == aviso.fecha_hora
    assert asiento.funcionario == aviso.funcionario
    assert asiento.transicion_valida is True


def test_rf_02_esc_02_fallo_aislado(caplog):
    canal = CanalEventosMemoria()
    registro = RegistroBitacoraMemoria()
    mensajes = RegistroMensajesMemoria()
    indicadores = RegistroIndicadoresMemoria()
    fechas = RegistroFechasTramiteMemoria()
    fechas.registrar_radicado("T-0001", date(2026, 11, 2))
    canal.suscribir(ConsumidorFalla().manejar)
    canal.suscribir(BitacoraConsumidor(registro).manejar)
    canal.suscribir(IndicadorConsumidor(indicadores, fechas).manejar)
    canal.suscribir(MensajesConsumidor(mensajes).manejar)
    _publicar(canal)
    canal.despachar_pendientes()
    assert len(registro.consultar_por_tramite("T-0001")) == 1
    assert indicadores.consultar_dias_calculados("T-0001") == 4
    assert mensajes.consultar_por_tramite("T-0001")[0].texto == "Su trámite T-0001 fue aprobado"
    assert "Un receptor falló" in caplog.text
    assert "T-0001" not in caplog.text
    assert "F-01" not in caplog.text
    assert canal.obtener_pendientes() == []


def test_rf_02_esc_03_marca_invalida():
    canal, registro = _bitacora()
    _publicar(canal, "aprobado", "en revisión")
    canal.despachar_pendientes()
    asientos = registro.consultar_por_tramite("T-0001")
    assert len(asientos) == 1
    assert asientos[0].transicion_valida is False


def test_rf_03_esc_01_cuatro_dias_habiles():
    canal, registro, fechas = _indicador()
    fechas.registrar_radicado("T-0001", date(2026, 11, 2))
    _publicar(canal)
    canal.despachar_pendientes()
    assert registro.consultar_dias_calculados("T-0001") == 4


def test_rf_03_esc_02_promedio_aprobados():
    canal, registro, fechas = _indicador()
    fechas.registrar_radicado("T-0001", date(2026, 11, 2))
    fechas.registrar_radicado("T-0002", date(2026, 11, 4))
    _publicar(canal)
    canal.despachar_pendientes()
    assert registro.promedio_por_tipo("mutación") == Decimal(4)
    _publicar(canal, numero="T-0002")
    canal.despachar_pendientes()
    assert registro.promedio_por_tipo("mutación") == Decimal(3)
    assert registro.promedio_por_tipo("otro tipo") == Decimal(0)


def test_rf_03_esc_03_promedio_rechazados():
    canal, registro, fechas = _indicador()
    fechas.registrar_radicado("T-0001", date(2026, 11, 2))
    _publicar(canal, nuevo="rechazado")
    canal.despachar_pendientes()
    assert registro.promedio_por_tipo("mutación") == Decimal(4)


def test_rf_03_esc_04_estado_no_final():
    canal, registro, fechas = _indicador()
    fechas.registrar_radicado("T-0001", date(2026, 11, 2))
    _publicar(canal, "radicado", "en revisión")
    canal.despachar_pendientes()
    assert registro.consultar_dias_calculados("T-0001") is None
    assert registro.promedio_por_tipo("mutación") == Decimal(0)


def test_rf_04_esc_01_mensaje_aprobado():
    mensajes = _mensaje("T-0001", "en revisión", "aprobado")
    assert len(mensajes) == 1
    assert mensajes[0].numero_tramite == "T-0001"
    assert mensajes[0].texto == "Su trámite T-0001 fue aprobado"


def test_rf_04_esc_02_mensaje_rechazado():
    mensajes = _mensaje("T-0002", "en revisión", "rechazado")
    assert len(mensajes) == 1
    assert mensajes[0].texto == (
        "Su trámite T-0002 fue rechazado; puede consultar el motivo en la oficina"
    )


def test_rf_04_esc_03_mensaje_revision():
    mensajes = _mensaje("T-0003", "radicado", "en revisión")
    assert len(mensajes) == 1
    assert mensajes[0].texto == "Su trámite T-0003 está en revisión"


@pytest.mark.parametrize("campo", ["numero_tramite", "tipo_tramite", "funcionario"])
@pytest.mark.parametrize("valor", ["", "   ", None, 1])
def test_identificadores_invalidos_no_publican(campo, valor):
    canal = CanalEventosMemoria()
    datos = {
        "numero_tramite": "T",
        "tipo_tramite": "M",
        "estado_anterior": "radicado",
        "estado_nuevo": "en revisión",
        "fecha_hora": datetime(2026, 11, 2),
        "funcionario": "F",
    }
    datos[campo] = valor
    with pytest.raises(ValueError):
        publicar_cambio_estado(canal, **datos)
    assert canal.obtener_pendientes() == []


@pytest.mark.parametrize("campo", ["estado_anterior", "estado_nuevo"])
@pytest.mark.parametrize("valor", ["", "desconocido", None, []])
def test_estados_fuera_del_catalogo(campo, valor):
    canal = CanalEventosMemoria()
    datos = {
        "numero_tramite": "T",
        "tipo_tramite": "M",
        "estado_anterior": "radicado",
        "estado_nuevo": "en revisión",
        "fecha_hora": datetime(2026, 11, 2),
        "funcionario": "F",
    }
    datos[campo] = valor
    with pytest.raises(ValueError):
        publicar_cambio_estado(canal, **datos)
    assert canal.obtener_pendientes() == []


def test_fecha_hora_y_marca_invalidas():
    with pytest.raises(ValueError):
        AvisoCambioEstado("T", "M", "radicado", "en revisión", date(2026, 11, 2), "F", True)
    with pytest.raises(ValueError):
        AvisoCambioEstado("T", "M", "radicado", "en revisión", datetime(2026, 11, 2), "F", False)
    with pytest.raises(ValueError):
        AvisoCambioEstado("T", "M", "radicado", "en revisión", datetime(2026, 11, 2), "F", 1)


def test_identificadores_minimos_validos():
    canal = CanalEventosMemoria()
    aviso = publicar_cambio_estado(
        canal, "T", "M", "radicado", "en revisión", datetime(2026, 11, 2), "F"
    )
    assert canal.obtener_pendientes() == [aviso]


@pytest.mark.parametrize(
    ("inicio", "dia_final", "esperados"),
    [(date(2026, 11, 6), 6, 0), (date(2026, 11, 6), 9, 1), (date(2026, 11, 7), 8, 0)],
)
def test_limites_dias_habiles(inicio, dia_final, esperados):
    canal, registro, fechas = _indicador()
    fechas.registrar_radicado("T-0001", inicio)
    _publicar(canal, dia=dia_final)
    canal.despachar_pendientes()
    assert registro.consultar_dias_calculados("T-0001") == esperados
    assert registro.promedio_por_tipo("mutación") == Decimal(esperados)


def test_fecha_final_anterior_no_registra():
    registro = RegistroIndicadoresMemoria()
    fechas = RegistroFechasTramiteMemoria()
    fechas.registrar_radicado("T-0001", date(2026, 11, 9))
    canal = CanalEventosMemoria()
    aviso = _publicar(canal)
    consumidor = IndicadorConsumidor(registro, fechas)
    with pytest.raises(ValueError):
        consumidor.manejar(aviso)
    assert registro.consultar_dias_calculados("T-0001") is None


def test_sin_fecha_no_actualiza_indicador():
    canal, registro, fechas = _indicador()
    assert fechas.obtener_fecha_radicado("T-0001") is None
    _publicar(canal)
    canal.despachar_pendientes()
    assert registro.consultar_dias_calculados("T-0001") is None


@pytest.mark.parametrize("dias", [-1, Decimal("1"), True, "1"])
def test_dias_invalidos(dias):
    registro = RegistroIndicadoresMemoria()
    with pytest.raises(ValueError):
        registro.registrar_dias("T", "M", dias)
    assert registro.consultar_dias_calculados("T") is None


def test_actualizacion_no_duplica_promedio():
    registro = RegistroIndicadoresMemoria()
    registro.registrar_dias("T", "M", 0)
    registro.registrar_dias("U", "M", 3)
    assert registro.promedio_por_tipo("M") == Decimal("1.5")
    registro.registrar_dias("T", "M", 1)
    assert registro.promedio_por_tipo("M") == Decimal(2)


@pytest.mark.parametrize("fecha", [None, "2026-11-02", datetime(2026, 11, 2)])
def test_fecha_radicado_invalida(fecha):
    registro = RegistroFechasTramiteMemoria()
    with pytest.raises(ValueError):
        registro.registrar_radicado("T", fecha)
    assert registro.obtener_fecha_radicado("T") is None


def test_consumidor_falla_directamente():
    aviso = _publicar(CanalEventosMemoria())
    with pytest.raises(Exception, match="Fallo deliberado"):
        ConsumidorFalla().manejar(aviso)


def test_canal_rechaza_entradas_invalidas():
    canal = CanalEventosMemoria()
    with pytest.raises(ValueError):
        canal.suscribir(None)
    with pytest.raises(ValueError):
        canal.publicar(None)
    assert canal.obtener_pendientes() == []


def test_aislamiento_copias_y_despacho_unico():
    canal, registro = _bitacora()
    _publicar(canal)
    copia = canal.obtener_pendientes()
    copia.clear()
    assert len(canal.obtener_pendientes()) == 1
    assert CanalEventosMemoria().obtener_pendientes() == []
    canal.despachar_pendientes()
    canal.despachar_pendientes()
    asientos = registro.consultar_por_tramite("T-0001")
    assert len(asientos) == 1
    asientos.clear()
    assert len(registro.consultar_por_tramite("T-0001")) == 1
    assert RegistroBitacoraMemoria().consultar_por_tramite("T-0001") == []
    assert RegistroIndicadoresMemoria().promedio_por_tipo("mutación") == Decimal(0)
    assert RegistroFechasTramiteMemoria().obtener_fecha_radicado("T-0001") is None
    assert RegistroMensajesMemoria().consultar_por_tramite("T-0001") == []
