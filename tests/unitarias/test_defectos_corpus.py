"""Corpus de defectos inyectados: integridad, alineación con la base y detección estática (N12)."""

import pytest

from multiagente.agentes.tester.analisis import analizar_version
from multiagente.agentes.tester.reglas import cargar_reglas_calidad
from multiagente.interfaces.defectos import (
    DefectoInyectado,
    ErrorCorpus,
    aplicar,
    cargar_corpus_de_defectos,
)
from multiagente.orquestador.estado import (
    Requerimientos,
    Validacion,
    Veredicto,
    VersionCodigo,
)
from multiagente.orquestador.simulacion import DesarrolladorFijo

REGLAS = cargar_reglas_calidad()
CORPUS = {corpus.nombre: corpus for corpus in cargar_corpus_de_defectos()}
ESTATICOS = {
    "avaluo": {"D02", "D03", "D04", "D05", "D06", "D07", "D08", "D09", "D10", "D11", "D13"}
    | {"D17", "J03"},
    "pagos": {"D01"},
}
"""Defectos que N12 detecta sin ejecutar el código, por corpus. Desde el ADR-0015, J03 y las
pruebas que inyectan atributos los detecta N12 (CAL-FS-006)."""


def analizar(corpus, archivos):
    caso = corpus.caso
    requerimientos = Requerimientos(
        historias=caso.sintesis.historias, requerimientos=caso.sintesis.requerimientos
    )
    version = VersionCodigo(numero=1, archivos=archivos)
    return analizar_version(version, caso.especificacion, requerimientos, REGLAS)


def test_corpus_con_tres_controles_y_veintiun_defectos():
    assert set(CORPUS) == {"avaluo", "mutacion", "pagos"}
    avaluo, pagos = CORPUS["avaluo"].definicion, CORPUS["pagos"].definicion
    assert (len(avaluo.defectos), len(pagos.defectos)) == (18, 3)
    assert sum(defecto.solo_juez for defecto in avaluo.defectos) == 3
    assert sum(defecto.solo_juez for defecto in pagos.defectos) == 2
    assert all(c.definicion.control.veredicto is Veredicto.APROBADO for c in CORPUS.values())
    assert all(
        defecto.esperado.veredicto is Veredicto.RECHAZADO and defecto.esperado.reglas
        for corpus in CORPUS.values()
        for defecto in corpus.definicion.defectos
    )


def test_las_reglas_esperadas_existen_en_la_base_de_conocimiento():
    esperadas = {
        regla
        for corpus in CORPUS.values()
        for defecto in corpus.definicion.defectos
        for regla in defecto.esperado.reglas
    }
    assert esperadas <= set(REGLAS)


@pytest.mark.parametrize("nombre", ["avaluo", "mutacion", "pagos"])
def test_las_bases_no_tienen_hallazgos_estaticos(nombre):
    corpus = CORPUS[nombre]
    assert analizar(corpus, corpus.base).hallazgos == ()


@pytest.mark.parametrize(
    ("nombre", "variante"),
    [
        (nombre, v)
        for nombre, estaticos in ESTATICOS.items()
        for v in CORPUS[nombre].variantes()
        if v.defecto and v.defecto.id in estaticos
    ],
    ids=lambda valor: valor if isinstance(valor, str) else valor.id,
)
def test_n12_detecta_cada_defecto_estatico(nombre, variante):
    reglas = {h.regla for h in analizar(CORPUS[nombre], variante.archivos).hallazgos}
    assert set(variante.esperado.reglas) <= reglas, reglas


@pytest.mark.parametrize(
    ("nombre", "variante"),
    [
        (nombre, v)
        for nombre, corpus in CORPUS.items()
        for v in corpus.variantes()
        if v.defecto and v.defecto.solo_juez
    ],
    ids=lambda valor: valor if isinstance(valor, str) else valor.id,
)
def test_los_defectos_del_juez_no_los_detecta_n12(nombre, variante):
    # Así el corpus mide al juez: N12 no deja ningún hallazgo en estas variantes.
    assert analizar(CORPUS[nombre], variante.archivos).hallazgos == ()


def test_una_inyeccion_desalineada_hace_fallar_la_carga():
    base = {"src/a.py": "x = 1\nx = 1\n"}
    repetido = DefectoInyectado.model_validate(
        {
            "id": "X1",
            "clase": "prueba",
            "descripcion": "texto repetido",
            "cambios": [{"ruta": "src/a.py", "buscar": "x = 1", "reemplazar": "x = 2"}],
            "esperado": {"veredicto": "rechazado"},
        }
    )
    with pytest.raises(ErrorCorpus, match="2 veces"):
        aplicar(base, repetido)
    datos = repetido.model_dump() | {"cambios": [{"ruta": "src/b.py", "eliminar": True}]}
    with pytest.raises(ErrorCorpus, match="no existe"):
        aplicar(base, DefectoInyectado.model_validate(datos))


def test_desarrollador_fijo_entrega_las_versiones_en_orden():
    fijo = DesarrolladorFijo(versiones=[{"src/a.py": "v1\n"}, {"src/a.py": "v2\n"}])
    especificacion = CORPUS["avaluo"].caso.especificacion
    primera = fijo.generar(Requerimientos(), especificacion, Validacion(), None)
    retro = Validacion(retroalimentacion=("[CAL-SG-002 · alta] …",))
    segunda = fijo.generar(Requerimientos(), especificacion, retro, primera)
    tercera = fijo.generar(Requerimientos(), especificacion, retro, segunda)
    assert [primera.numero, segunda.numero, tercera.numero] == [1, 2, 3]
    assert [v.archivos["src/a.py"] for v in (primera, segunda, tercera)] == ["v1\n", "v2\n", "v2\n"]
    assert segunda.defectos_atendidos == retro.retroalimentacion
