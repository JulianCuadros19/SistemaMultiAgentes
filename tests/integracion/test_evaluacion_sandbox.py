"""Oráculo común del paso 15 en el entorno aislado real (ADR-0019).

Requiere Docker y la imagen: `docker compose build sandbox`, y luego
`pytest -m "sandbox and not nube"`.
"""

import pytest

from multiagente.evaluacion.referencia import (
    cargar_caso_referencia,
    casos_de_referencia,
    evaluar_referencia,
    hallazgos_estaticos,
    pruebas_propias,
    validar_oraculo,
)
from multiagente.sandbox.ejecutor import EntornoAislado

pytestmark = pytest.mark.sandbox

NIT = {
    "src/nit/__init__.py": "",
    "src/nit/digito.py": (
        '"""Dígito de verificación."""\n\n'
        "PESOS = (3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71)\n\n\n"
        "def dv(numero: str) -> int:\n"
        '    """Dígito de verificación del número."""\n'
        '    limpio = numero.replace(".", "").replace("-", "")\n'
        "    if not limpio.isdigit():\n"
        '        raise ValueError("El NIT solo admite dígitos")\n'
        "    if len(limpio) > 15:\n"
        '        raise ValueError("El NIT admite como máximo 15 dígitos")\n'
        "    r = sum(int(d) * p for d, p in zip(reversed(limpio), PESOS)) % 11\n"
        "    return r if r < 2 else 11 - r\n"
    ),
    "tests/test_propio.py": (
        "from nit.digito import dv\n\n\n"
        "def test_dv():\n    assert dv('900123456') == 8\n\n\n"
        "def test_dv_que_falla():\n    assert dv('123456789') == 5\n"
    ),
}
ADAPTADOR_SIN_VALIDAR = (
    "from nit.digito import dv\n"
    "from referencia_comun import Ausente\n\n\n"
    "def calcular_digito(numero: str) -> int:\n"
    "    return dv(numero)\n\n\n"
    "def validar_nit(nit: str) -> tuple[bool, int]:\n"
    "    raise Ausente('la implementación no valida un NIT completo')\n"
)


@pytest.mark.parametrize("id_caso", casos_de_referencia())
def test_el_oraculo_pasa_con_el_control_y_detecta_cada_mutante(id_caso):
    validacion = validar_oraculo(EntornoAislado(), cargar_caso_referencia(id_caso))
    assert validacion.control.cuenta("paso") == validacion.control.total
    assert validacion.mutantes_no_detectados == []
    assert validacion.valido


def test_un_comportamiento_ausente_se_cuenta_aparte():
    caso = cargar_caso_referencia("caso-ampliada-12")
    resultado = evaluar_referencia(EntornoAislado(), caso, ADAPTADOR_SIN_VALIDAR, NIT)
    ausentes = {v.nombre for v in resultado.verificaciones if v.resultado == "ausente"}
    assert ausentes == {
        "test_valida_un_nit_correcto_con_puntos_y_guion",
        "test_informa_el_digito_esperado_de_un_nit_incorrecto",
        "test_rechaza_letras",
    }
    assert resultado.cuenta("paso") == 7


def test_las_pruebas_propias_y_los_hallazgos_de_una_implementacion():
    propias = pruebas_propias(EntornoAislado(), NIT)
    assert (propias.total, propias.pasan, propias.errores_recoleccion) == (2, 1, 0)
    assert isinstance(hallazgos_estaticos(NIT), dict)
