"""N2 con el modelo real BGE-M3: la guía de elicitación y el dominio de la necesidad (RF-04).

Requiere los servicios `db` y `embeddings` de docker compose (`pytest -m embeddings`).
"""

from datetime import UTC, datetime

import pytest

from multiagente.agentes.elicitador.contexto import recuperar_contexto
from multiagente.orquestador.estado import Conversacion, Emisor, Turno
from multiagente.rag.colecciones import Agente
from multiagente.rag.recuperacion import Recuperador

pytestmark = pytest.mark.embeddings

AHORA = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)


def contexto_de(base_real, vectorizador, necesidad: str):
    recuperador = Recuperador(base_real, vectorizador, Agente.ELICITADOR)
    conversacion = Conversacion(
        turnos=(Turno(emisor=Emisor.CLIENTE, texto=necesidad, fecha=AHORA),)
    )
    return recuperar_contexto(recuperador, conversacion)


@pytest.mark.parametrize(
    ("necesidad", "documento_dominio"),
    [
        (
            "Necesitamos registrar las solicitudes de mutación de propietario de los predios, "
            "hoy se hace a mano",
            "dom-002",
        ),
        ("Quiero calcular el avalúo de un predio con su terreno y su construcción", "dom-003"),
    ],
)
def test_n2_recupera_la_guia_y_el_dominio_de_la_necesidad(
    base_real, vectorizador, necesidad, documento_dominio
):
    contexto = contexto_de(base_real, vectorizador, necesidad)
    assert set(contexto.fragmentos) == {"elicitacion", "dominio_negocio"}

    metodologia = {f.documento_id for f in contexto.fragmentos["elicitacion"]}
    assert {"eli-001", "eli-003", "eli-004", "eli-006", "eli-009"} <= metodologia
    assert all(documento.startswith("eli-") for documento in metodologia)

    dominio = contexto.fragmentos["dominio_negocio"]
    assert dominio, contexto.descartados
    assert all(f.documento_id.startswith("dom-") for f in dominio)
    assert dominio[0].documento_id == documento_dominio
    for fragmento in dominio:
        print(f"{fragmento.similitud:.3f} {fragmento.referencia}")
