"""N7 con el modelo real BGE-M3: el catálogo completo y la metodología del arquitecto (RF-09).

Requiere los servicios `db` y `embeddings` de docker compose (`pytest -m embeddings`).
"""

import pytest

from multiagente.agentes.arquitecto.contexto import recuperar_catalogo
from multiagente.core.esquemas.comunes import Enunciado, Impacto, Prioridad
from multiagente.core.esquemas.requerimiento import (
    DatoEntrada,
    Descripcion,
    EscenarioAceptacion,
    RequerimientoFormal,
    TipoSolicitud,
)
from multiagente.orquestador.estado import Requerimientos
from multiagente.rag.colecciones import Agente
from multiagente.rag.recuperacion import Recuperador

pytestmark = pytest.mark.embeddings


def aprobados(quiero: str, regla: str) -> Requerimientos:
    requerimiento = RequerimientoFormal(
        id_requerimiento="RF-01",
        version="0.1",
        proyecto="Catastro",
        tipo_solicitud=TipoSolicitud.NUEVO,
        impacto=Impacto.ALTO,
        modulo="catastro",
        autor="Agente elicitador",
        area_funcional="Conservación",
        titulo=Enunciado(como="analista de conservación catastral", quiero=quiero, para="tramitar"),
        descripcion=Descripcion(
            precondicion="El predio existe",
            regla_negocio=regla,
            datos_entrada=[DatoEntrada(nombre="numero_predial", tipo="str", obligatorio=True)],
            datos_salida=[],
        ),
        criterios_aceptacion=[
            EscenarioAceptacion(
                id="ESC-01", dado_que="un predio", cuando="se procesa", entonces="ok"
            )
        ],
        prioridad=Prioridad.ALTA,
    )
    return Requerimientos(requerimientos=(requerimiento,))


@pytest.mark.parametrize(
    ("quiero", "regla"),
    [
        (
            "registrar solicitudes de mutación de propietario",
            "La solicitud se acepta solo si el número predial existe en la base catastral.",
        ),
        (
            "liquidar cada noche el impuesto de todos los predios en lote",
            "El proceso lee los avalúos vigentes, aplica la tarifa y deja un reporte por lote.",
        ),
    ],
)
def test_n7_recupera_el_catalogo_completo_y_la_metodologia(base_real, vectorizador, quiero, regla):
    recuperador = Recuperador(base_real, vectorizador, Agente.ARQUITECTO)
    contexto = recuperar_catalogo(recuperador, aprobados(quiero, regla))
    assert set(contexto.fragmentos) == {"arquitecturas_referencia"}
    fragmentos = contexto.fragmentos["arquitecturas_referencia"]
    documentos = [f.documento_id for f in fragmentos]
    assert documentos[:6] == [f"arq-arq-0{n}" for n in range(1, 7)]
    assert {"arq-001", "arq-002", "arq-003", "arq-004"} <= set(documentos)
    criterios = {f.titulo for f in fragmentos if f.documento_id == "arq-003"}
    for seccion in ("Paso 1", "Paso 2", "Paso 3", "Paso 4", "Prohibiciones"):
        assert any(seccion in titulo for titulo in criterios), criterios
    for fragmento in fragmentos:
        print(f"{fragmento.similitud:.3f} {fragmento.referencia}")
