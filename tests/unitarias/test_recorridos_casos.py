"""Los recorridos destapan en N9 los vacíos de diseño de la sesión de pensiones (ADR-0015).

Las versiones 0.2 a 0.5 de la sesión 5f5d2739 pasaron las validaciones de N9; dos llegaron a N17
y volvieron al arquitecto. Con los recorridos que exigen sus escenarios, la validación nombra las
interfaces que les faltaban, las mismas que el revisor pidió en sus observaciones.
"""

import json
import re

import pytest

from multiagente.agentes.arquitecto.recorridos import (
    RecorridoModelo,
    errores_de_recorridos,
    recorridos_desde_salida,
)
from multiagente.core.esquemas.especificacion_diseno import EspecificacionDiseno
from multiagente.interfaces.casos import cargar_caso_desarrollo
from multiagente.interfaces.cliente_simulado import RAIZ_EVALUACION
from multiagente.orquestador.estado import Requerimientos

CASOS = RAIZ_EVALUACION / "casos"
REPRODUCCION = json.loads((CASOS / "recorridos-pagos.json").read_text(encoding="utf-8"))
DESARROLLO = cargar_caso_desarrollo(CASOS / REPRODUCCION["caso_desarrollo"])
REQUERIMIENTOS = Requerimientos(requerimientos=DESARROLLO.sintesis.requerimientos)
RECORRIDOS = recorridos_desde_salida(
    [RecorridoModelo.model_validate(r) for r in REPRODUCCION["recorridos"]]
)
VERSIONES = {v["version"]: v for v in REPRODUCCION["versiones"]}

# Sin dónde vivan las facturas, los recibos y la cartera de cada familia, ni cómo consultarlos.
SIN_ALMACEN = {
    "registrar_factura_inicial",
    "obtener_factura_por_numero",
    "manejar_pago_confirmado_emitir_recibo",
    "obtener_recibo_por_referencia",
    "registrar_cartera_familia",
    "obtener_cartera_por_familia",
}
FALTANTES = {
    "0.2": SIN_ALMACEN,
    "0.3": SIN_ALMACEN,
    # La 0.4 agregó el almacén de facturas (observación 2), pero no el recibo ni la cartera.
    "0.4": {
        "manejar_pago_confirmado_emitir_recibo",
        "obtener_recibo_por_referencia",
        "registrar_cartera_familia",
        "obtener_cartera_por_familia",
    },
    # La 0.5 los agregó (observación 3), pero el recibo anulado no se podía consultar.
    "0.5": {"obtener_recibo_por_referencia"},
}
NO_DECLARADA = re.compile(r"«([^»]+)» no es una interfaz declarada")


@pytest.mark.parametrize("version", sorted(FALTANTES))
def test_cada_version_carece_de_las_interfaces_que_pidio_el_revisor(version):
    especificacion = EspecificacionDiseno.model_validate(VERSIONES[version]["especificacion"])
    errores = errores_de_recorridos(especificacion, REQUERIMIENTOS, RECORRIDOS)
    assert errores
    assert all(NO_DECLARADA.search(error) for error in errores), errores
    assert {NO_DECLARADA.search(error)[1] for error in errores} == FALTANTES[version]


def test_el_diseno_completo_ejecuta_todos_sus_escenarios():
    assert errores_de_recorridos(DESARROLLO.especificacion, REQUERIMIENTOS, RECORRIDOS) == []
    escenarios = {
        (r.id_requerimiento, e.id)
        for r in REQUERIMIENTOS.requerimientos
        for e in r.criterios_aceptacion
    }
    assert {(r.id_requerimiento, r.id_escenario) for r in RECORRIDOS} == escenarios
