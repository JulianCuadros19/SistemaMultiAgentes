"""Configuración de estilo del código generado: lectura, huella y análisis con Ruff."""

import hashlib

from multiagente.core.estilo import RUTA_ESTILO_GENERADO, cargar_estilo, hallazgos_de_estilo

CONFORME = '''"""Entidad de predio."""

from decimal import Decimal


def avaluo(area: Decimal, valor_m2: Decimal) -> Decimal:
    """Calcula el avalúo.

    Args:
        area: Área en metros cuadrados.
        valor_m2: Valor del metro cuadrado.

    Returns:
        El avalúo.
    """
    return area * valor_m2
'''

PRUEBA = """from decimal import Decimal

from dominio.predio import avaluo


def test_rf_01_esc_01_calcula():
    assert avaluo(Decimal(2), Decimal(3)) == Decimal(6)
"""


def test_huella_del_archivo_versionado():
    estilo = cargar_estilo()
    assert estilo.archivo == "ruff.toml"
    assert estilo.huella == hashlib.sha256(RUTA_ESTILO_GENERADO.read_bytes()).hexdigest()
    assert 'target-version = "py311"' in estilo.texto


def test_codigo_conforme_sin_hallazgos():
    archivos = {"src/dominio/predio.py": CONFORME, "tests/test_predio.py": PRUEBA, "USO.md": "x"}
    assert hallazgos_de_estilo(archivos) == []


def test_reporta_seguridad_documentacion_y_anotaciones():
    archivos = {"src/dominio/riesgo.py": '"""Riesgo."""\n\n\ndef evaluar(x):\n    return eval(x)\n'}
    codigos = {hallazgo.codigo for hallazgo in hallazgos_de_estilo(archivos)}
    assert {"S307", "D103", "ANN001", "ANN201"} <= codigos
    (primero, *_) = hallazgos_de_estilo(archivos)
    assert primero.archivo == "src/dominio/riesgo.py"
