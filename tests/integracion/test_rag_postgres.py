"""Migraciones, ingesta y recuperación sobre PostgreSQL con un vectorizador de prueba.

Cada prueba trabaja en un esquema temporal (`conexion_aislada`), sin tocar el índice real.
"""

import shutil
from pathlib import Path

import pytest

from multiagente.core.configuracion import ConfiguracionRecuperacion
from multiagente.persistencia.migraciones import (
    CARPETA_MIGRACIONES,
    ErrorMigracionModificada,
    aplicar_migraciones,
)
from multiagente.rag.colecciones import ACCESO, Agente, Coleccion, ErrorAccesoNoAutorizado
from multiagente.rag.documentos import RAIZ_CONOCIMIENTO, cargar_corpus
from multiagente.rag.ingesta import ingestar
from multiagente.rag.recuperacion import Recuperador

pytestmark = pytest.mark.integracion

CONFIGURACION = ConfiguracionRecuperacion(
    _env_file=None, fragmentos=5, candidatos=20, umbral_similitud=0.0
)


@pytest.fixture
def base_con_corpus(conexion_aislada, vectorizador_prueba):
    aplicar_migraciones(conexion_aislada)
    ingestar(conexion_aislada, cargar_corpus(), vectorizador_prueba)
    conexion_aislada.commit()
    return conexion_aislada


def test_migraciones_idempotentes(conexion_aislada):
    assert aplicar_migraciones(conexion_aislada) == ["0001_bases_conocimiento"]
    assert aplicar_migraciones(conexion_aislada) == []


def test_migracion_aplicada_no_puede_cambiar(conexion_aislada, tmp_path: Path):
    copia = tmp_path / "migraciones"
    shutil.copytree(CARPETA_MIGRACIONES, copia)
    aplicar_migraciones(conexion_aislada, copia)
    archivo = copia / "0001_bases_conocimiento.sql"
    archivo.write_text(archivo.read_text() + "\n-- cambio\n")
    with pytest.raises(ErrorMigracionModificada):
        aplicar_migraciones(conexion_aislada, copia)


def test_ingesta_completa_e_idempotente(conexion_aislada, vectorizador_prueba):
    aplicar_migraciones(conexion_aislada)
    corpus = cargar_corpus()
    primera = ingestar(conexion_aislada, corpus, vectorizador_prueba)
    assert len(primera.nuevos) == 36
    assert primera.fragmentos_por_coleccion == {
        "arquitecturas_referencia": 33,
        "criterios_calidad": 51,
        "dominio_negocio": 40,
        "elicitacion": 62,
    }
    llamadas = vectorizador_prueba.llamadas
    segunda = ingestar(conexion_aislada, corpus, vectorizador_prueba)
    assert len(segunda.sin_cambios) == 36
    assert not segunda.nuevos and not segunda.actualizados and not segunda.eliminados
    assert vectorizador_prueba.llamadas == llamadas


def test_reindexa_documento_modificado_y_borra_el_eliminado(
    conexion_aislada, vectorizador_prueba, tmp_path: Path
):
    raiz = tmp_path / "knowledge_base"
    shutil.copytree(RAIZ_CONOCIMIENTO, raiz)
    aplicar_migraciones(conexion_aislada)
    ingestar(conexion_aislada, cargar_corpus(raiz), vectorizador_prueba)

    modificado = raiz / "dominio_negocio" / "03-avaluo-catastral.md"
    modificado.write_text(modificado.read_text() + "\n## Nueva sección\n\nTexto agregado.\n")
    (raiz / "elicitacion" / "02-criterios-invest.md").unlink()
    resumen = ingestar(conexion_aislada, cargar_corpus(raiz), vectorizador_prueba)

    assert resumen.actualizados == ["dom-003"]
    assert resumen.eliminados == ["eli-002"]
    assert len(resumen.sin_cambios) == 34
    restantes = conexion_aislada.execute(
        "SELECT count(*) FROM kb_fragmentos WHERE documento_id = %s", (resumen.eliminados[0],)
    ).fetchone()[0]
    assert restantes == 0


def test_fragmento_no_puede_cambiar_de_coleccion(base_con_corpus):
    with pytest.raises(Exception, match="foreign key|llave foránea|violates"):
        base_con_corpus.execute(
            "UPDATE kb_fragmentos SET coleccion = 'criterios_calidad' "
            "WHERE coleccion = 'elicitacion'"
        )
    base_con_corpus.rollback()


@pytest.mark.parametrize("agente", [Agente.ELICITADOR, Agente.ARQUITECTO, Agente.TESTER])
@pytest.mark.parametrize(
    "consulta",
    [
        "regla CAL-MT-005 modularidad conforme a la especificación",
        "ARQ-04 servicio API REST",
        "mutación catastral de primera clase",
        "criterios INVEST de la historia de usuario",
    ],
)
def test_cada_agente_solo_recupera_de_sus_colecciones(
    base_con_corpus, vectorizador_prueba, agente, consulta
):
    recuperador = Recuperador(base_con_corpus, vectorizador_prueba, agente, CONFIGURACION)
    resultado = recuperador.recuperar(consulta, k=20)
    autorizadas = ACCESO[agente]
    assert resultado.fragmentos
    assert {f.coleccion for f in resultado.fragmentos} <= autorizadas
    assert {d.fragmento.coleccion for d in resultado.descartados} <= autorizadas


def test_desarrollador_sin_recuperador(base_con_corpus, vectorizador_prueba):
    with pytest.raises(ErrorAccesoNoAutorizado):
        Recuperador(base_con_corpus, vectorizador_prueba, Agente.DESARROLLADOR, CONFIGURACION)


def test_coleccion_ajena_rechazada(base_con_corpus, vectorizador_prueba):
    recuperador = Recuperador(base_con_corpus, vectorizador_prueba, Agente.TESTER, CONFIGURACION)
    with pytest.raises(ErrorAccesoNoAutorizado):
        recuperador.recuperar("avalúo", colecciones=[Coleccion.DOMINIO_NEGOCIO])


@pytest.mark.parametrize(
    ("agente", "consulta", "esperado"),
    [
        (Agente.TESTER, "CAL-MT-005", "CAL-MT-005"),
        (Agente.TESTER, "CAL-SG-002", "CAL-SG-002"),
        (Agente.ARQUITECTO, "ARQ-04", "ARQ-04"),
    ],
)
def test_terminos_exactos_en_primer_lugar(
    base_con_corpus, vectorizador_prueba, agente, consulta, esperado
):
    recuperador = Recuperador(base_con_corpus, vectorizador_prueba, agente, CONFIGURACION)
    primero = recuperador.recuperar(consulta).fragmentos[0]
    assert esperado in primero.titulo or esperado in primero.contenido
    assert primero.rango_lexico == 1
