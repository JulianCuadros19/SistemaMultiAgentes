"""Pruebas de aceptación de referencia del caso 04, contratos de arrendamiento (ADR-0019).

Verifican solo lo que la ficha del caso dice sin ambigüedad, a través de la interfaz de
`interfaz.md`. Las mismas pruebas evalúan al sistema y a las líneas base de un solo modelo.
"""

from datetime import date

from adaptador_referencia import Contratos
from referencia_comun import rechaza

INICIO = date(2026, 1, 1)
FIN = date(2026, 12, 31)


def _con_borrador(
    codigo="C-1", inmueble="INM-100", arrendatario="10203040", canon=1_500_000, inicio=INICIO, fin=FIN
):
    contratos = Contratos()
    contratos.crear(codigo, inmueble, arrendatario, canon, inicio, fin, "ana")
    return contratos


def test_activa_un_contrato_valido():
    assert _con_borrador().activar("C-1", "ana") == "vigente"


def test_rechaza_periodos_que_se_cruzan():
    contratos = _con_borrador()
    contratos.activar("C-1", "ana")
    contratos.crear("C-2", "INM-100", "50607080", 1_500_000, date(2026, 6, 1), date(2027, 5, 31), "ana")
    rechaza(
        contratos.activar,
        "C-2",
        "ana",
        mensaje="El inmueble ya tiene un contrato vigente en ese periodo",
    )


def test_activa_si_los_periodos_no_se_cruzan():
    contratos = _con_borrador()
    contratos.activar("C-1", "ana")
    contratos.crear("C-3", "INM-100", "50607080", 1_500_000, date(2027, 1, 1), date(2027, 12, 31), "ana")
    assert contratos.activar("C-3", "ana") == "vigente"


def test_rechaza_activar_sin_arrendatario():
    rechaza(_con_borrador(arrendatario=None).activar, "C-1", "ana")


def test_rechaza_activar_con_canon_cero():
    rechaza(_con_borrador(canon=0).activar, "C-1", "ana")


def test_rechaza_activar_con_menos_de_seis_meses():
    rechaza(_con_borrador(fin=date(2026, 3, 31)).activar, "C-1", "ana")


def test_termina_un_contrato_vigente():
    contratos = _con_borrador()
    contratos.activar("C-1", "ana")
    assert contratos.terminar("C-1", "Mutuo acuerdo", date(2026, 6, 15), "ana") == "terminado"


def test_terminar_exige_motivo():
    contratos = _con_borrador()
    contratos.activar("C-1", "ana")
    rechaza(contratos.terminar, "C-1", "", date(2026, 6, 15), "ana")


def test_terminar_exige_fecha_dentro_del_periodo():
    contratos = _con_borrador()
    contratos.activar("C-1", "ana")
    rechaza(contratos.terminar, "C-1", "Mutuo acuerdo", date(2027, 6, 15), "ana")


def test_anula_un_borrador():
    assert _con_borrador().anular("C-1", "ana") == "anulado"


def test_una_transicion_no_permitida_indica_el_estado():
    contratos = _con_borrador()
    rechaza(contratos.terminar, "C-1", "Mutuo acuerdo", date(2026, 6, 15), "ana", mensaje="borrador")


def test_un_contrato_terminado_no_cambia():
    contratos = _con_borrador()
    contratos.activar("C-1", "ana")
    contratos.terminar("C-1", "Mutuo acuerdo", date(2026, 6, 15), "ana")
    rechaza(contratos.activar, "C-1", "ana")
    rechaza(contratos.anular, "C-1", "ana")


def test_registra_el_usuario_de_cada_cambio():
    contratos = _con_borrador()
    contratos.activar("C-1", "beto")
    contratos.terminar("C-1", "Mutuo acuerdo", date(2026, 6, 15), "carla")
    usuarios = contratos.usuarios_de_los_cambios("C-1")
    assert "beto" in usuarios
    assert "carla" in usuarios
