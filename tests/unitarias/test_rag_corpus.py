"""Pruebas del corpus, la segmentación, el mapa de acceso y la fusión, sin base ni modelo."""

from collections import Counter
from pathlib import Path

import pytest

from multiagente.rag.colecciones import (
    ACCESO,
    Agente,
    Coleccion,
    ErrorAccesoNoAutorizado,
    autorizar,
)
from multiagente.rag.documentos import ErrorDocumento, Estrategia, cargar_corpus, leer_documento
from multiagente.rag.segmentacion import MAX_CARACTERES, partir_con_solapamiento, segmentar

CORPUS = cargar_corpus()
POR_RUTA = {documento.ruta: documento for documento in CORPUS}


def fragmentos_de(ruta: str):
    return segmentar(POR_RUTA[ruta])


def test_corpus_completo_y_valido():
    assert len(CORPUS) == 36
    assert Counter(d.metadatos.coleccion for d in CORPUS) == {
        Coleccion.ELICITACION: 10,
        Coleccion.DOMINIO_NEGOCIO: 7,
        Coleccion.ARQUITECTURAS_REFERENCIA: 11,
        Coleccion.CRITERIOS_CALIDAD: 8,
    }
    assert not any(d.ruta.endswith(("README.md", "00-MANIFIESTO.md")) for d in CORPUS)


def test_cada_documento_declara_un_agente_autorizado():
    for documento in CORPUS:
        metadatos = documento.metadatos
        assert metadatos.coleccion in ACCESO[metadatos.agente_consumidor], documento.ruta


def test_version_se_lee_como_texto(tmp_path: Path):
    carpeta = tmp_path / "elicitacion"
    carpeta.mkdir()
    archivo = carpeta / "x.md"
    archivo.write_text(
        "---\nid: x\ntitulo: X\nfuente: F\ntipo_fuente: t\ntags: [a, b]\nversion: 1.10\n"
        "fecha: 2026-10-08\nagente_consumidor: elicitador\nsegmentacion: por_seccion\n"
        "coleccion: elicitacion\n---\n# X\n\nTexto.\n",
        encoding="utf-8",
    )
    documento = leer_documento(archivo, tmp_path)
    assert documento.metadatos.version == "1.10"
    assert documento.metadatos.tags == ["a", "b"]


def test_rechaza_coleccion_distinta_a_la_carpeta(tmp_path: Path):
    carpeta = tmp_path / "dominio_negocio"
    carpeta.mkdir()
    archivo = carpeta / "x.md"
    archivo.write_text(
        "---\nid: x\ntitulo: X\nfuente: F\ntipo_fuente: t\nversion: 1.0\nfecha: 2026-10-08\n"
        "agente_consumidor: elicitador\nsegmentacion: por_seccion\ncoleccion: elicitacion\n"
        "---\n# X\n",
        encoding="utf-8",
    )
    with pytest.raises(ErrorDocumento, match="carpeta|está en"):
        leer_documento(archivo, tmp_path)


def test_rechaza_agente_no_autorizado(tmp_path: Path):
    carpeta = tmp_path / "criterios_calidad"
    carpeta.mkdir()
    archivo = carpeta / "x.md"
    archivo.write_text(
        "---\nid: x\ntitulo: X\nfuente: F\ntipo_fuente: t\nversion: 1.0\nfecha: 2026-10-08\n"
        "agente_consumidor: desarrollador\nsegmentacion: una_regla_por_fragmento\n"
        "coleccion: criterios_calidad\n---\n# X\n",
        encoding="utf-8",
    )
    with pytest.raises(ErrorDocumento, match="no está autorizado"):
        leer_documento(archivo, tmp_path)


def test_una_regla_por_fragmento_con_metadatos():
    reglas = [
        f.metadatos
        for d in CORPUS
        if d.metadatos.segmentacion is Estrategia.UNA_REGLA_POR_FRAGMENTO
        for f in segmentar(d)
        if "regla" in f.metadatos
    ]
    assert len(reglas) == 31
    assert len({r["regla"] for r in reglas}) == 31
    assert all({"severidad", "caracteristica", "norma"} <= set(r) for r in reglas)


def test_cada_arquitectura_del_catalogo_es_un_solo_fragmento():
    catalogo = [d for d in CORPUS if d.ruta.startswith("arquitecturas_referencia/catalogo/")]
    assert len(catalogo) == 6
    for documento in catalogo:
        fragmentos = segmentar(documento)
        assert len(fragmentos) == 1
        assert "Consecuencias" in fragmentos[0].contenido or len(fragmentos[0].contenido) > 1000


def test_titulos_dentro_de_bloques_de_codigo_no_parten_el_documento():
    fragmentos = fragmentos_de("arquitecturas_referencia/01-plantilla-decision-arquitectonica.md")
    titulos = [f.titulo for f in fragmentos]
    assert not any("Contexto y planteamiento" in titulo for titulo in titulos)
    assert any("```markdown" in f.contenido for f in fragmentos)


def test_por_seccion_un_fragmento_por_seccion():
    fragmentos = fragmentos_de("dominio_negocio/02-mutaciones-catastrales.md")
    assert [f.titulo.split(" › ")[-1] for f in fragmentos[1:]] == [
        "Clasificación por tipo",
        "Reglas de negocio típicas",
        "Estados del trámite",
        "Datos mínimos de una solicitud de mutación",
    ]
    assert [f.orden for f in fragmentos] == list(range(len(fragmentos)))


def test_ningun_fragmento_de_prosa_supera_el_limite():
    for documento in CORPUS:
        if documento.metadatos.segmentacion is Estrategia.POR_SECCION:
            assert all(len(f.contenido) <= MAX_CARACTERES for f in segmentar(documento))


def test_partir_con_solapamiento():
    parrafos = [f"Párrafo {i} " + "x" * 300 for i in range(20)]
    partes = partir_con_solapamiento("\n\n".join(parrafos), maximo=1000, solapamiento=100)
    assert len(partes) > 1
    assert all(len(parte) <= 1000 + 100 + 2 for parte in partes)
    for anterior, siguiente in zip(partes, partes[1:], strict=False):
        assert siguiente.startswith(anterior[-100:])


def test_mapa_de_acceso():
    assert autorizar(Agente.ELICITADOR) == {Coleccion.ELICITACION, Coleccion.DOMINIO_NEGOCIO}
    assert autorizar(Agente.ARQUITECTO) == {Coleccion.ARQUITECTURAS_REFERENCIA}
    assert autorizar(Agente.TESTER) == {Coleccion.CRITERIOS_CALIDAD}
    with pytest.raises(ErrorAccesoNoAutorizado, match="no consulta"):
        autorizar(Agente.DESARROLLADOR)
    with pytest.raises(ErrorAccesoNoAutorizado, match="criterios_calidad"):
        autorizar(Agente.ELICITADOR, [Coleccion.CRITERIOS_CALIDAD])
