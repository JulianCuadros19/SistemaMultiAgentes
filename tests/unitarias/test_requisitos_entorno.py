"""Versiones del entorno aislado: los tres archivos versionados de la imagen son coherentes."""

import pytest

from multiagente.sandbox.requisitos import nombre_canonico, versiones_probadas


@pytest.mark.parametrize(
    ("declarado", "canonico"),
    [
        ("psycopg[binary]", "psycopg"),
        ("typing_extensions", "typing-extensions"),
        ("Pygments", "pygments"),
        ("zope.interface", "zope-interface"),
    ],
)
def test_el_nombre_canonico_quita_extras_y_normaliza(declarado, canonico):
    assert nombre_canonico(declarado) == canonico


def test_cada_libreria_del_catalogo_tiene_cierre_y_version_fija():
    probadas = versiones_probadas()
    assert set(probadas.cierres) == set(probadas.requisitos)
    for nombre, requisito in probadas.requisitos.items():
        # El requisito del catálogo fija la misma versión que quedó instalada.
        version = requisito.split("==", 1)[1]
        assert probadas.versiones[nombre].endswith(f"=={version}")
        for dependencia in probadas.cierres[nombre]:
            assert dependencia in probadas.versiones, f"{dependencia}, de {nombre}, sin versión"


def test_lo_instalado_es_el_cierre_del_catalogo():
    probadas = versiones_probadas()
    alcanzables = {*probadas.requisitos, *(d for c in probadas.cierres.values() for d in c)}
    assert set(probadas.versiones) == alcanzables
