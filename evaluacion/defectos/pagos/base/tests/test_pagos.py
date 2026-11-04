from datetime import date
from decimal import Decimal
from importlib import reload

import pytest

from consumidores.cartera import manejar_pago_confirmado_cartera, manejar_pago_reversado_cartera
from consumidores.factura import manejar_pago_confirmado_factura, manejar_pago_reversado_factura
from consumidores.recibo import manejar_pago_reversado_recibo
from consumidores.recibo_emision import manejar_pago_confirmado_emitir_recibo
from eventos.aviso_pago import AvisoPagoConfirmado, AvisoPagoReversado, ValidacionEventoInvalido
from eventos.aviso_pago_enriquecido import (
    AvisoPagoConfirmadoEnriquecido,
    AvisoPagoReversadoEnriquecido,
)
from eventos.aviso_pago_enriquecido import (
    ValidacionEventoInvalido as ValidacionEnriquecidoInvalido,
)
from eventos.resultados import AnulacionReciboResultado, EmisionReciboResultado
from infraestructura import repos_facturacion_memoria as repos
from infraestructura.bus_eventos_memoria import BusEventosMemoria, EventoDuplicadoIgnorado
from productores.publicador_avisos import (
    AvisoIncompleto,
    construir_aviso_confirmado,
    construir_aviso_reversado,
)


@pytest.fixture(autouse=True)
def almacen_limpio():
    reload(repos)


@pytest.fixture
def bus():
    canal = BusEventosMemoria()
    canal.suscribir_pago_confirmado(manejar_pago_confirmado_factura)
    canal.suscribir_pago_confirmado(manejar_pago_confirmado_emitir_recibo)
    canal.suscribir_pago_confirmado(manejar_pago_confirmado_cartera)
    canal.suscribir_pago_reversado(manejar_pago_reversado_factura)
    canal.suscribir_pago_reversado(manejar_pago_reversado_recibo)
    canal.suscribir_pago_reversado(manejar_pago_reversado_cartera)
    return canal


def _registrar(numero="2024-000123", saldo="250000"):
    repos.registrar_factura_inicial(numero, "FAMILIA-1", Decimal(saldo), "pendiente")
    repos.registrar_cartera_familia("FAMILIA-1", "en mora")


def _confirmado(referencia="PAGO-7788", numero="2024-000123", valor="250000"):
    return construir_aviso_confirmado(referencia, numero, Decimal(valor), date(2026, 10, 31))


def _emitir_recibo(referencia="PAGO-7788", numero="2024-000123", valor="250000"):
    return repos.aplicar_emision_recibo(
        EmisionReciboResultado(
            numero, referencia, Decimal(valor), date(2026, 10, 31), f"confirmado:{referencia}"
        )
    )


def test_rf_01_esc_01_pago_cubre_saldo(bus):
    _registrar()
    decisiones = []

    def observar(aviso):
        resultado = manejar_pago_confirmado_factura(aviso)
        decisiones.append(resultado)
        return resultado

    bus.suscribir_pago_confirmado(observar)
    bus.publicar_pago_confirmado(_confirmado())
    factura = repos.obtener_factura_por_numero("2024-000123")
    assert factura.estado == "pagada"
    assert factura.saldo == Decimal(0)
    assert decisiones[0].valor_aplicado == Decimal(250000)
    assert decisiones[0].valor_aplicado.as_tuple().exponent == 0


def test_rf_01_esc_02_pago_parcial(bus):
    _registrar("2024-000124")
    decisiones = []

    def observar(aviso):
        resultado = manejar_pago_confirmado_factura(aviso)
        decisiones.append(resultado)
        return resultado

    bus.suscribir_pago_confirmado(observar)
    bus.publicar_pago_confirmado(_confirmado("PAGO-7789", "2024-000124", "120000"))
    factura = repos.obtener_factura_por_numero("2024-000124")
    assert factura.estado == "abonada"
    assert factura.saldo == Decimal(130000)
    assert decisiones[0].valor_aplicado == Decimal(120000)
    assert decisiones[0].valor_aplicado.as_tuple().exponent == 0


def test_rf_01_esc_03_aviso_sin_factura():
    _registrar()
    anterior = repos.obtener_factura_por_numero("2024-000123")
    with pytest.raises(AvisoIncompleto):
        construir_aviso_confirmado("PAGO-7788", "", Decimal(250000), date(2026, 10, 31))
    assert repos.obtener_factura_por_numero("2024-000123") == anterior


def test_rf_02_esc_01_reverso_anula_y_restaura(bus):
    _registrar()
    bus.publicar_pago_confirmado(_confirmado())
    emitido = repos.obtener_recibo_por_referencia("PAGO-7788")
    assert emitido.consecutivo == "REC-000001"
    assert emitido.valor == Decimal(250000)
    assert emitido.numero_factura == "2024-000123"
    assert emitido.estado_recibo == "emitido"
    bus.publicar_pago_reversado(
        construir_aviso_reversado("PAGO-7788", date(2026, 10, 31), "reverso")
    )
    assert repos.obtener_recibo_por_referencia("PAGO-7788").estado_recibo == "anulado"
    factura = repos.obtener_factura_por_numero("2024-000123")
    assert factura.estado == "pendiente"
    assert factura.saldo == Decimal(250000)


def test_rf_02_esc_02_motivo_registrado(bus):
    _registrar("2024-000124")
    bus.publicar_pago_confirmado(_confirmado("PAGO-7789", "2024-000124", "120000"))
    bus.publicar_pago_reversado(
        construir_aviso_reversado(
            "PAGO-7789", date(2026, 10, 31), "reverso por contracargo"
        )
    )
    recibo = repos.obtener_recibo_por_referencia("PAGO-7789")
    assert recibo.estado_recibo == "anulado"
    assert recibo.motivo == "reverso por contracargo"


def test_rf_02_esc_03_reverso_sin_motivo(bus):
    _registrar()
    bus.publicar_pago_confirmado(_confirmado())
    anterior = repos.obtener_recibo_por_referencia("PAGO-7788")
    with pytest.raises(AvisoIncompleto):
        construir_aviso_reversado("PAGO-7788", date(2026, 10, 31), "")
    assert repos.obtener_recibo_por_referencia("PAGO-7788") == anterior
    assert repos.obtener_recibo_por_referencia("PAGO-7788").estado_recibo == "emitido"


def test_rf_03_esc_01_cartera_por_confirmacion(bus):
    _registrar()
    bus.publicar_pago_confirmado(_confirmado("PAGO-7790"))
    cartera = repos.obtener_cartera_por_familia("FAMILIA-1")
    assert cartera.estado == "al día"
    assert cartera.ultima_referencia_procesada == "PAGO-7790"


def test_rf_03_esc_02_cartera_por_reverso(bus):
    _registrar()
    bus.publicar_pago_confirmado(_confirmado("PAGO-7791"))
    bus.publicar_pago_reversado(
        construir_aviso_reversado("PAGO-7791", date(2026, 10, 31), "reverso")
    )
    cartera = repos.obtener_cartera_por_familia("FAMILIA-1")
    assert cartera.estado == "en mora"
    assert cartera.ultima_referencia_procesada == "PAGO-7791"


def test_rf_03_esc_03_duplicado_no_modifica_cartera(bus):
    _registrar()
    aviso = _confirmado("PAGO-7792", valor="120000")
    bus.publicar_pago_confirmado(aviso)
    cartera = repos.obtener_cartera_por_familia("FAMILIA-1")
    factura = repos.obtener_factura_por_numero("2024-000123")
    recibo = repos.obtener_recibo_por_referencia("PAGO-7792")
    assert (cartera.estado, cartera.ultima_referencia_procesada) == ("en mora", "PAGO-7792")
    assert (factura.estado, factura.saldo) == ("abonada", Decimal(130000))
    with pytest.raises(EventoDuplicadoIgnorado):
        bus.publicar_pago_confirmado(aviso)
    assert repos.obtener_cartera_por_familia("FAMILIA-1") == cartera
    assert repos.obtener_factura_por_numero("2024-000123") == factura
    assert repos.obtener_recibo_por_referencia("PAGO-7792") == recibo


@pytest.mark.parametrize("valor", [Decimal(-1), Decimal("0.1"), Decimal("NaN"),
                                   Decimal("Infinity"), 1, 1.0])
def test_valores_invalidos(valor):
    with pytest.raises(ValidacionEventoInvalido):
        construir_aviso_confirmado("P", "N", valor, date(2026, 10, 31))


@pytest.mark.parametrize("valor", ["0", "1", "1.00", "250001"])
def test_limites_y_excedente(valor):
    aviso = AvisoPagoConfirmadoEnriquecido(
        "P", "N", Decimal(valor), date(2026, 10, 31), Decimal(250000), "pendiente", "F"
    )
    resultado = manejar_pago_confirmado_factura(aviso)
    assert resultado.valor_aplicado == min(Decimal(valor), Decimal(250000))
    assert resultado.saldo_a_favor == max(Decimal(0), Decimal(valor) - Decimal(250000))
    assert resultado.valor_aplicado.as_tuple().exponent == 0
    assert resultado.saldo_a_favor.as_tuple().exponent == 0


def test_saldo_cero_y_pago_cero():
    aviso = AvisoPagoConfirmadoEnriquecido(
        "P", "N", Decimal(0), date(2026, 10, 31), Decimal(0), "pagada", "F"
    )
    assert manejar_pago_confirmado_factura(aviso).estado_factura == "pagada"
    assert manejar_pago_confirmado_cartera(aviso).estado_cartera == "al día"


@pytest.mark.parametrize("fecha", [None, "2026-10-31", 0])
def test_fechas_invalidas_en_eventos(fecha):
    with pytest.raises(ValidacionEventoInvalido):
        AvisoPagoConfirmado("P", "N", Decimal(0), fecha)
    with pytest.raises(ValidacionEventoInvalido):
        AvisoPagoReversado("P", fecha, "motivo")


@pytest.mark.parametrize("texto", ["", "   ", None, 1])
def test_referencia_y_motivo_invalidos(texto):
    with pytest.raises(ValidacionEventoInvalido):
        AvisoPagoConfirmado(texto, "N", Decimal(0), date(2026, 10, 31))
    with pytest.raises(ValidacionEventoInvalido):
        AvisoPagoReversado("P", date(2026, 10, 31), texto)


@pytest.mark.parametrize("campo, valor", [
    ("saldo_actual", Decimal(-1)), ("saldo_actual", Decimal("1.1")),
    ("estado_actual", "otro"), ("id_familia", ""), ("numero_factura", ""),
    ("fecha", "2026-10-31"), ("valor", Decimal("NaN")),
])
def test_contexto_confirmado_invalido(campo, valor):
    datos = {
        "referencia_pago": "P", "numero_factura": "N", "valor": Decimal(1),
        "fecha": date(2026, 10, 31), "saldo_actual": Decimal(1),
        "estado_actual": "pendiente", "id_familia": "F",
    }
    datos[campo] = valor
    with pytest.raises(ValidacionEnriquecidoInvalido):
        AvisoPagoConfirmadoEnriquecido(**datos)


def test_contexto_reversado_invalido():
    with pytest.raises(ValidacionEnriquecidoInvalido):
        AvisoPagoReversadoEnriquecido("P", date(2026, 10, 31), "motivo", "N", "otro", "F")


@pytest.mark.parametrize("manejador", [
    manejar_pago_confirmado_factura, manejar_pago_reversado_factura,
    manejar_pago_confirmado_emitir_recibo, manejar_pago_reversado_recibo,
    manejar_pago_confirmado_cartera, manejar_pago_reversado_cartera,
])
def test_consumidores_rechazan_evento_incorrecto(manejador):
    with pytest.raises(ValidacionEnriquecidoInvalido):
        manejador(None)


def test_factura_y_referencia_inexistentes(bus):
    with pytest.raises(repos.FacturaNoExiste):
        bus.publicar_pago_confirmado(_confirmado())
    with pytest.raises(repos.ReferenciaNoAsociada):
        bus.publicar_pago_reversado(
            construir_aviso_reversado("P", date(2026, 10, 31), "motivo")
        )
    with pytest.raises(repos.ReciboNoExiste):
        repos.aplicar_anulacion_recibo(AnulacionReciboResultado("P", "motivo", "anulado", "k"))


def test_consecutivos_y_emision_idempotente():
    primero = _emitir_recibo()
    segundo = _emitir_recibo("PAGO-7789")
    assert primero.consecutivo == "REC-000001"
    assert segundo.consecutivo == "REC-000002"
    assert _emitir_recibo() is primero


def test_reverso_duplicado_no_modifica_estado(bus):
    _registrar()
    bus.publicar_pago_confirmado(_confirmado())
    aviso = construir_aviso_reversado("PAGO-7788", date(2026, 10, 31), "motivo")
    bus.publicar_pago_reversado(aviso)
    factura = repos.obtener_factura_por_numero("2024-000123")
    with pytest.raises(EventoDuplicadoIgnorado):
        bus.publicar_pago_reversado(aviso)
    assert repos.obtener_factura_por_numero("2024-000123") is factura


def test_cartera_parcial_y_estado_anterior_pagado():
    confirmado = AvisoPagoConfirmadoEnriquecido(
        "P", "N", Decimal(1), date(2026, 10, 31), Decimal(2), "pendiente", "F"
    )
    assert manejar_pago_confirmado_cartera(confirmado).estado_cartera == "en mora"
    reversado = AvisoPagoReversadoEnriquecido(
        "P", date(2026, 10, 31), "motivo", "N", "pagada", "F"
    )
    assert manejar_pago_reversado_cartera(reversado).estado_cartera == "al día"


@pytest.mark.parametrize("saldo", [Decimal(-1), Decimal("1.5"), Decimal("Infinity")])
def test_registro_factura_invalida_no_persiste(saldo):
    with pytest.raises(ValueError):
        repos.registrar_factura_inicial("N", "F", saldo, "pendiente")
    with pytest.raises(repos.FacturaNoExiste):
        repos.obtener_factura_por_numero("N")


def test_resultados_invalidos():
    with pytest.raises(ValueError):
        EmisionReciboResultado("N", "P", Decimal("1.1"), date(2026, 10, 31), "k")
    with pytest.raises(ValueError):
        AnulacionReciboResultado("P", "motivo", "emitido", "k")


def test_suscripcion_y_enriquecimiento_independientes():
    _registrar()
    bus = BusEventosMemoria()
    observados = []

    def observar(aviso):
        observados.append(aviso)
        return manejar_pago_confirmado_factura(aviso)

    bus.suscribir_pago_confirmado(observar)
    bus.publicar_pago_confirmado(_confirmado())
    assert observados[0].saldo_actual == Decimal(250000)
    assert observados[0].id_familia == "FAMILIA-1"
    assert repos.obtener_numero_factura_por_referencia("PAGO-7788") == "2024-000123"


@pytest.mark.parametrize(
    "primera_referencia, segunda_referencia, saldo_intermedio",
    [
        ("PAGO-8001", "PAGO-8002", Decimal(200000)),
        ("PAGO-8002", "PAGO-8001", Decimal(150000)),
    ],
)
def test_reversos_de_abonos_conservan_los_otros_pagos(
    bus, primera_referencia, segunda_referencia, saldo_intermedio
):
    numero = "2024-000200"
    _registrar(numero)
    bus.publicar_pago_confirmado(_confirmado("PAGO-8001", numero, "100000"))
    bus.publicar_pago_confirmado(_confirmado("PAGO-8002", numero, "50000"))
    assert repos.obtener_factura_por_numero(numero).saldo == Decimal(100000)

    bus.publicar_pago_reversado(
        construir_aviso_reversado(primera_referencia, date(2026, 10, 31), "contracargo")
    )
    intermedia = repos.obtener_factura_por_numero(numero)
    assert intermedia.saldo == saldo_intermedio
    assert intermedia.estado == "abonada"
    assert repos.obtener_recibo_por_referencia(primera_referencia).estado_recibo == "anulado"
    assert repos.obtener_recibo_por_referencia(segunda_referencia).estado_recibo == "emitido"
    with pytest.raises(EventoDuplicadoIgnorado):
        bus.publicar_pago_reversado(
            construir_aviso_reversado(primera_referencia, date(2026, 10, 31), "contracargo")
        )
    assert repos.obtener_factura_por_numero(numero) is intermedia

    bus.publicar_pago_reversado(
        construir_aviso_reversado(segunda_referencia, date(2026, 10, 31), "contracargo")
    )
    final = repos.obtener_factura_por_numero(numero)
    assert final.saldo == Decimal(250000)
    assert final.estado == "pendiente"
    assert repos.obtener_recibo_por_referencia(segunda_referencia).estado_recibo == "anulado"


@pytest.mark.parametrize("valor", ["0", "300000"])
def test_reverso_devuelve_solo_el_valor_aplicado(bus, valor):
    _registrar()
    bus.publicar_pago_confirmado(_confirmado(valor=valor))
    bus.publicar_pago_reversado(
        construir_aviso_reversado("PAGO-7788", date(2026, 10, 31), "contracargo")
    )
    factura = repos.obtener_factura_por_numero("2024-000123")
    assert factura.saldo == Decimal(250000)
    assert factura.estado == "pendiente"


def test_reverso_de_pago_con_saldo_inicial_cero(bus):
    repos.registrar_factura_inicial("N", "FAMILIA-1", Decimal(0), "pagada")
    repos.registrar_cartera_familia("FAMILIA-1", "al día")
    bus.publicar_pago_confirmado(_confirmado("P", "N", "0"))
    bus.publicar_pago_reversado(
        construir_aviso_reversado("P", date(2026, 10, 31), "contracargo")
    )
    factura = repos.obtener_factura_por_numero("N")
    assert factura.saldo == Decimal(0)
    assert factura.estado == "pagada"
