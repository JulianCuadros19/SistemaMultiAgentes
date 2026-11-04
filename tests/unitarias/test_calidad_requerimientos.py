"""Verificación automática de la calidad de los requerimientos (RF-07) en N6."""

import json
import re
from pathlib import Path

import pytest

from multiagente.agentes.elicitador.calidad import (
    Caracteristica,
    verificar_conjunto,
    verificar_historia,
    verificar_requerimiento,
)
from multiagente.core.esquemas.requerimiento import (
    BacklogHistorias,
    HistoriaUsuario,
    RequerimientoFormal,
)
from multiagente.orquestador.estado import Requerimientos

RAIZ = Path(__file__).resolve().parents[2]
DATOS = RAIZ / "tests" / "datos" / "anexos"
PLANTILLA = RAIZ / "knowledge_base" / "elicitacion" / "03-plantilla-requerimiento-funcional.md"


def cargar(nombre: str) -> dict:
    datos = json.loads((DATOS / nombre).read_text(encoding="utf-8"))
    datos.pop("_fuente")
    return datos


def ejemplo_plantilla() -> dict:
    texto = PLANTILLA.read_text(encoding="utf-8")
    return json.loads(re.search(r"```json\n(.*?)\n```", texto, re.S).group(1))


def requerimiento(**cambios) -> RequerimientoFormal:
    datos = ejemplo_plantilla()
    for ruta, valor in cambios.items():
        destino = datos
        *intermedios, ultimo = ruta.split("__")
        for clave in intermedios:
            destino = destino[int(clave)] if clave.isdigit() else destino[clave]
        destino[int(ultimo) if ultimo.isdigit() else ultimo] = valor
    return RequerimientoFormal.model_validate(datos)


def caracteristicas(defectos) -> list[Caracteristica]:
    return [defecto.caracteristica for defecto in defectos]


def test_el_ejemplo_de_la_plantilla_cumple():
    assert verificar_requerimiento(requerimiento()) == []


def test_el_rf27_del_anexo_a_solo_incumple_el_infinitivo():
    defectos = verificar_requerimiento(
        RequerimientoFormal.model_validate(cargar("anexo_a_rf27.json"))
    )
    assert [str(defecto) for defecto in defectos] == [
        "RF-27 · C9 Conforme · titulo.quiero: el QUIERO no inicia con un verbo en infinitivo"
    ]


def test_el_backlog_del_anexo_a_tiene_defectos_de_redaccion():
    backlog = BacklogHistorias.model_validate(cargar("anexo_a_backlog.json"))
    encontrados = {
        historia.id: caracteristicas(verificar_historia(historia))
        for historia in backlog.historias
        if verificar_historia(historia)
    }
    # Las historias 3 y 4 no inician en infinitivo (ADR-0005); la 1 y la 10 unen dos
    # capacidades («e indicar», «y gestionar»).
    assert encontrados == {
        "HU-01": [Caracteristica.SINGULAR],
        "HU-03": [Caracteristica.CONFORME],
        "HU-04": [Caracteristica.CONFORME],
        "HU-10": [Caracteristica.SINGULAR],
    }


REGLA = ejemplo_plantilla()["descripcion"]["regla_negocio"]


@pytest.mark.parametrize(
    ("cambios", "caracteristica", "senal"),
    [
        ({"descripcion__regla_negocio": REGLA + " El cálculo es rápido."}, "NO_AMBIGUO", "rapido"),
        ({"descripcion__regla_negocio": "TBD"}, "COMPLETO", "tbd"),
        ({"descripcion__precondicion": "Valores por definir"}, "COMPLETO", "por definir"),
        ({"riesgo": "Pendiente de confirmar con el área"}, "COMPLETO", "pendiente de confirmar"),
        (
            {"criterios_aceptacion__0__entonces": "el sistema funciona correctamente"},
            "NO_AMBIGUO",
            "correctamente",
        ),
        ({"descripcion__regla_negocio": REGLA + " Aplica a lotes, etc."}, "COMPLETO", "etc"),
        (
            {"descripcion__regla_negocio": REGLA + " Debería redondear al peso."},
            "NECESARIO",
            "deberia",
        ),
        (
            {"criterios_aceptacion__1__entonces": "el cálculo es más rápido"},
            "VERIFICABLE",
            "mas rapido",
        ),
        (
            {"titulo__quiero": "calcular el avalúo y emitir la liquidación"},
            "SINGULAR",
            "y emitir",
        ),
        ({"titulo__quiero": "el cálculo del avalúo del predio"}, "CONFORME", "infinitivo"),
        ({"titulo__como": "el usuario"}, "CONFORME", "rol genérico"),
        (
            {"descripcion__datos_entrada__0__restriccion": "un valor razonable"},
            "NO_AMBIGUO",
            "razonable",
        ),
        ({"descripcion__datos_salida": []}, "COMPLETO", "ningún dato"),
        (
            {"criterios_aceptacion__0__cuando": "se invoca calcular_avaluo"},
            "CONFORME",
            "detalle de implementación",
        ),
        (
            {"criterios_aceptacion__0__dado_que": "el archivo esc_2019_00042.pdf"},
            "CONFORME",
            "«esc_2019_00042»",
        ),
        (
            {"criterios_aceptacion__0__dado_que": "una fecha de documento <= la radicación"},
            "CONFORME",
            "«<=»",
        ),
        (
            {"criterios_aceptacion__0__cuando": "la fecha del documento ≤ la de radicación"},
            "CONFORME",
            "«≤»",
        ),
    ],
)
def test_senal_inyectada_es_detectada(cambios, caracteristica, senal):
    defectos = verificar_requerimiento(requerimiento(**cambios))
    assert any(
        defecto.caracteristica is Caracteristica[caracteristica] and senal in defecto.detalle
        for defecto in defectos
    ), [str(defecto) for defecto in defectos]


@pytest.mark.parametrize(
    "cambios",
    [
        {"descripcion__regla_negocio": REGLA + " Se reporta el saldo pendiente de pago."},
        {"criterios_aceptacion__1__entonces": "la tarifa es mejor que la del año anterior"},
        {"descripcion__regla_negocio": REGLA + " El titular y el predio deben existir."},
        {"titulo__quiero": "registrar la mutación con su titular y fecha"},
        {"criterios_aceptacion__2__dado_que": "un numero_predial de 29 dígitos"},
        {
            "descripcion__datos_entrada__0__nombre": "Número predial",
            "criterios_aceptacion__2__dado_que": "un numero_predial de 29 dígitos",
        },
        # Un código o un nombre de archivo en mayúsculas es un valor que dio el cliente.
        {"criterios_aceptacion__0__dado_que": "la carpeta contiene el archivo ESC_2019_00042.pdf"},
    ],
)
def test_usos_legitimos_no_son_defectos(cambios):
    assert verificar_requerimiento(requerimiento(**cambios)) == []


def test_escenarios_insuficientes():
    datos = ejemplo_plantilla()
    solo_feliz = verificar_requerimiento(
        requerimiento(criterios_aceptacion=datos["criterios_aceptacion"][:1])
    )
    assert [d.detalle for d in solo_feliz] == [
        "1 escenarios: faltan el camino feliz, el alterno o el de error (al menos 3)",
        "ningún escenario cubre un caso de error o una entrada inválida",
    ]
    # Con dos escenarios falta el tercero que pide eli-004, aunque uno sea de error.
    dos = verificar_requerimiento(
        requerimiento(criterios_aceptacion=datos["criterios_aceptacion"][:2])
    )
    assert [d.detalle for d in dos] == [
        "2 escenarios: faltan el camino feliz, el alterno o el de error (al menos 3)",
        "ningún escenario cubre un caso de error o una entrada inválida",
    ]
    assert set(caracteristicas(dos)) == {Caracteristica.VERIFICABLE}


def conjunto(rf: RequerimientoFormal | None = None, **cambios_historia) -> Requerimientos:
    rf = rf or requerimiento()
    historia = HistoriaUsuario(id="HU-01", enunciado=rf.titulo, **cambios_historia)
    return Requerimientos(
        historias=(historia,),
        requerimientos=(rf,),
        referencias={rf.id_requerimiento: ("eli-003 v1.1 · Plantilla",)},
    )


def test_conjunto_trazable_cumple():
    assert verificar_conjunto(conjunto()) == []


def test_conjunto_sin_referencias_al_contexto():
    sin_referencias = conjunto().model_copy(update={"referencias": {}})
    [defecto] = verificar_conjunto(sin_referencias)
    assert (defecto.artefacto, defecto.caracteristica, defecto.campo) == (
        "RF-014",
        Caracteristica.TRAZABLE,
        "referencias",
    )


def test_conjunto_con_historia_sin_requerimiento():
    rf = requerimiento()
    otra = HistoriaUsuario(
        id="HU-02", enunciado=rf.titulo.model_copy(update={"quiero": "consultar el avalúo"})
    )
    datos = conjunto(rf)
    defectos = verificar_conjunto(datos.model_copy(update={"historias": (otra,)}))
    assert {(d.artefacto, d.caracteristica) for d in defectos} == {
        ("HU-02", Caracteristica.TRAZABLE),
        ("RF-014", Caracteristica.TRAZABLE),
    }


def test_conjunto_con_preguntas_abiertas():
    defectos = verificar_conjunto(conjunto(preguntas_abiertas=["¿Qué tipos de mutación aplican?"]))
    assert [str(d) for d in defectos] == [
        "HU-01 · C4 Completo · preguntas_abiertas: quedan 1 preguntas sin resolver con el cliente"
    ]


def test_defecto_del_titulo_no_se_repite_en_la_historia():
    rf = requerimiento(titulo__como="usuario")
    defectos = verificar_conjunto(conjunto(rf))
    assert [d.artefacto for d in defectos] == ["RF-014"]


def test_conjunto_vacio():
    [defecto] = verificar_conjunto(Requerimientos())
    assert defecto.caracteristica is Caracteristica.COMPLETO
