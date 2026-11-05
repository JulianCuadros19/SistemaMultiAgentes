"""Pruebas de aceptación de referencia del caso 17, trámites catastrales (ADR-0019).

Verifican solo lo que la ficha del caso dice sin ambigüedad, a través de la interfaz de
`interfaz.md`. Las mismas pruebas evalúan al sistema y a las líneas base de un solo modelo.
"""

from datetime import datetime

from adaptador_referencia import procesar

LUNES = datetime(2026, 11, 2, 9, 0)
MIERCOLES = datetime(2026, 11, 4, 9, 0)
VIERNES = datetime(2026, 11, 6, 9, 0)
LUNES_SIGUIENTE = datetime(2026, 11, 9, 9, 0)


def _aviso(numero, anterior, nuevo, fecha, tipo="mutación"):
    return {
        "numero": numero,
        "tipo": tipo,
        "estado_anterior": anterior,
        "estado_nuevo": nuevo,
        "fecha": fecha,
        "funcionario": "ana",
    }


def _flujo(numero, final, radicado, cierre, tipo="mutación"):
    return [
        _aviso(numero, "radicado", "en revisión", radicado, tipo),
        _aviso(numero, "en revisión", final, cierre, tipo),
    ]


def test_la_bitacora_registra_cada_aviso():
    bitacora, _, _ = procesar(_flujo("T-0001", "aprobado", LUNES, VIERNES))
    assert bitacora.count(("T-0001", True)) == 2


def test_mensaje_de_aprobado():
    _, mensajes, _ = procesar(_flujo("T-0001", "aprobado", LUNES, VIERNES))
    assert "Su trámite T-0001 fue aprobado" in mensajes


def test_mensaje_de_rechazado():
    _, mensajes, _ = procesar(_flujo("T-0002", "rechazado", LUNES, VIERNES))
    assert "Su trámite T-0002 fue rechazado; puede consultar el motivo en la oficina" in mensajes


def test_mensaje_en_revision():
    _, mensajes, _ = procesar(_flujo("T-0003", "aprobado", LUNES, VIERNES))
    assert "Su trámite T-0003 está en revisión" in mensajes


def test_dias_habiles_del_ejemplo():
    _, _, promedios = procesar(_flujo("T-0001", "aprobado", LUNES, VIERNES))
    assert promedios["mutación"] == 4


def test_el_fin_de_semana_no_cuenta():
    _, _, promedios = procesar(_flujo("T-0004", "aprobado", VIERNES, LUNES_SIGUIENTE))
    assert promedios["mutación"] == 1


def test_promedio_por_tipo_de_tramite():
    avisos = [
        *_flujo("T-0005", "aprobado", LUNES, VIERNES),
        *_flujo("T-0006", "rechazado", LUNES, MIERCOLES),
        *_flujo("T-0007", "aprobado", LUNES, MIERCOLES, "certificado"),
    ]
    _, _, promedios = procesar(avisos)
    assert promedios["mutación"] == 3
    assert promedios["certificado"] == 2


def test_una_transicion_invalida_queda_marcada():
    bitacora, _, _ = procesar([_aviso("T-0008", "aprobado", "en revisión", LUNES)])
    assert ("T-0008", False) in bitacora


def test_una_transicion_invalida_no_se_procesa():
    avisos = [_aviso("T-0009", "radicado", "aprobado", LUNES, "rectificación")]
    _, mensajes, promedios = procesar(avisos)
    assert not any("T-0009" in mensaje for mensaje in mensajes)
    assert not promedios.get("rectificación")
