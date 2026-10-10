"""Tester, N13 y N14: criterios recuperados, dictamen por caso, juez y regla de veredicto."""

import json
from decimal import Decimal

import pytest

from multiagente.agentes.tester.analisis import hallazgo
from multiagente.agentes.tester.contexto import CONSULTAS_FIJAS, recuperar_criterios
from multiagente.agentes.tester.reglas import cargar_reglas_calidad
from multiagente.agentes.tester.veredicto import (
    dictaminar_version,
    hallazgos_de_ejecucion,
    pruebas_fuente,
    sugerencia_de_ejecucion,
)
from multiagente.llm.costos import Tarifa
from multiagente.llm.invocador import InvocadorNodo, ParametrosNodo
from multiagente.llm.prompts import cargar_prompt
from multiagente.llm.traza import RegistroEnMemoria
from multiagente.orquestador.estado import (
    CasoPrueba,
    Contexto,
    EjecucionPruebas,
    PruebaEjecutada,
    ResultadoPrueba,
    Severidad,
    Validacion,
    Veredicto,
    VersionCodigo,
)
from multiagente.rag.colecciones import Agente, Coleccion
from multiagente.rag.recuperacion import FragmentoRecuperado, ResultadoRecuperacion

REGLAS = cargar_reglas_calidad()
MODELO = "gpt-6-luna-2026-09-22"
TARIFAS = {
    "gpt-6-luna": Tarifa(
        entrada=Decimal("0.10"),
        entrada_cacheada=Decimal("0.01"),
        salida=Decimal("0.50"),
        escritura_cache=Decimal("0.125"),
    )
}


def caso(numero: int, entonces: str = "el avalúo es 6") -> CasoPrueba:
    return CasoPrueba(
        id=f"CP-RF-01-ESC-0{numero}",
        id_requerimiento="RF-01",
        id_escenario=f"ESC-0{numero}",
        dado_que="un predio de 2 m² a 3 pesos el m²",
        cuando="se calcula el avalúo",
        entonces=entonces,
    )


PLAN = (caso(1), caso(2, "el sistema rechaza un valor cero"))

PRUEBAS = """import pytest

from aplicacion.avaluo import calcular_avaluo


def test_rf_01_esc_01_calcula():
    assert calcular_avaluo(2, 3) == 6


@pytest.mark.parametrize("valor", [0, -1])
def test_rf_01_esc_02_rechaza(valor):
    with pytest.raises(ValueError):
        calcular_avaluo(2, valor)
"""


def ejecutada(nombre: str, resultado=ResultadoPrueba.PASO, mensaje="") -> PruebaEjecutada:
    return PruebaEjecutada(
        archivo="tests/test_avaluo.py", nombre=nombre, resultado=resultado, mensaje=mensaje
    )


EJECUCION = EjecucionPruebas(
    pruebas=(
        ejecutada("test_rf_01_esc_01_calcula"),
        ejecutada("test_rf_01_esc_02_rechaza[0]"),
        ejecutada("test_rf_01_esc_02_rechaza[-1]"),
    ),
    duracion_ms=900,
)


def version(pruebas: str = PRUEBAS) -> VersionCodigo:
    return VersionCodigo(numero=1, archivos={"tests/test_avaluo.py": pruebas, "USO.md": "# Uso"})


def dictaminar(validacion=None, pruebas=PRUEBAS, juez=None, umbral=0):
    validacion = validacion or Validacion(plan_pruebas=PLAN, ejecucion=EJECUCION)
    return dictaminar_version(PLAN, validacion, Contexto(), version(pruebas), REGLAS, umbral, juez)


def reglas_de(dictamen) -> set[str]:
    return {h.regla for h in dictamen.hallazgos}


# Parte determinística ---------------------------------------------------------------------------


def test_fuentes_de_las_pruebas_con_su_codigo():
    fuentes = pruebas_fuente(version().archivos)
    assert [f.nombre for f in fuentes] == ["test_rf_01_esc_01_calcula", "test_rf_01_esc_02_rechaza"]
    assert all(f.verifica for f in fuentes)
    assert fuentes[0].codigo.startswith("def test_rf_01_esc_01_calcula")


def test_casos_con_pruebas_que_pasan_se_aprueban_sin_juez():
    dictamen = dictaminar()
    assert dictamen.veredicto is Veredicto.APROBADO
    assert all(v.cumple for v in dictamen.veredictos)
    assert dictamen.veredictos[1].pruebas == ("tests/test_avaluo.py::test_rf_01_esc_02_rechaza",)
    assert dictamen.retroalimentacion == ()
    assert "Veredicto: APROBADO" in dictamen.reporte


def test_caso_sin_prueba():
    sin_esc_02 = PRUEBAS.replace("test_rf_01_esc_02_rechaza", "test_rechaza")
    dictamen = dictaminar(pruebas=sin_esc_02)
    assert dictamen.veredicto is Veredicto.RECHAZADO
    assert not dictamen.veredictos[1].cumple
    (falta,) = [h for h in dictamen.hallazgos if h.regla == "CAL-FS-001"]
    assert falta.ubicacion == "CP-RF-01-ESC-02" and falta.severidad is Severidad.ALTA
    assert "el sistema rechaza un valor cero" in falta.descripcion
    assert dictamen.retroalimentacion[0].startswith("[CAL-FS-001 · alta] CP-RF-01-ESC-02 · ")
    assert " · Sugerencia: " in dictamen.retroalimentacion[0]


def test_prueba_que_falla():
    fallida = EjecucionPruebas(
        pruebas=(
            ejecutada(
                "test_rf_01_esc_01_calcula",
                ResultadoPrueba.FALLO,
                "    def test_x():\n>       assert 5 == 6\nE       assert 5 == 6\n",
            ),
            *EJECUCION.pruebas[1:],
        )
    )
    dictamen = dictaminar(Validacion(plan_pruebas=PLAN, ejecucion=fallida))
    assert dictamen.veredicto is Veredicto.RECHAZADO
    assert not dictamen.veredictos[0].cumple
    assert "assert 5 == 6" in dictamen.veredictos[0].evidencia
    (falla,) = [h for h in dictamen.hallazgos if h.regla == "CAL-FS-002"]
    assert falla.ubicacion == "tests/test_avaluo.py::test_rf_01_esc_01_calcula"


def test_prueba_sin_asercion():
    sin_asercion = PRUEBAS.replace(
        "    assert calcular_avaluo(2, 3) == 6", "    calcular_avaluo(2, 3)"
    )
    dictamen = dictaminar(pruebas=sin_asercion)
    assert not dictamen.veredictos[0].cumple
    assert "no tienen assert" in dictamen.veredictos[0].evidencia
    assert "CAL-FS-001" in reglas_de(dictamen)


def test_importacion_recoleccion_y_tiempo_vencido():
    ejecucion = EJECUCION.model_copy(
        update={
            "errores_importacion": {"aplicacion.avaluo": "Traceback\nSyntaxError: invalid syntax"},
            "errores_recoleccion": ("tests/test_otro.py: ImportError",),
            "vencido": True,
        }
    )
    dictamen = dictaminar(Validacion(plan_pruebas=PLAN, ejecucion=ejecucion))
    ubicaciones = {(h.regla, h.ubicacion) for h in dictamen.hallazgos}
    assert ("CAL-FS-003", "aplicacion.avaluo") in ubicaciones
    assert ("CAL-FS-002", "tests/test_otro.py") in ubicaciones
    assert ("CAL-FS-002", "tests/") in ubicaciones
    assert dictamen.veredicto is Veredicto.RECHAZADO


def con_hallazgo(regla: str) -> Validacion:
    estatico = hallazgo(REGLAS, regla, "src/a.py:1", "descripción", "prueba")
    return Validacion(plan_pruebas=PLAN, ejecucion=EJECUCION, hallazgos=(estatico,))


@pytest.mark.parametrize(
    ("regla", "umbral", "esperado"),
    [
        ("CAL-SG-002", 5, Veredicto.RECHAZADO),  # alta: siempre rechaza
        ("CAL-MT-004", 0, Veredicto.RECHAZADO),  # media sobre el umbral 0
        ("CAL-MT-004", 1, Veredicto.APROBADO),  # media dentro del umbral
        ("CAL-MT-009", 0, Veredicto.APROBADO),  # baja: solo observación
    ],
)
def test_regla_de_veredicto(regla, umbral, esperado):
    dictamen = dictaminar(con_hallazgo(regla), umbral=umbral)
    assert dictamen.veredicto is esperado
    assert (dictamen.retroalimentacion != ()) is (esperado is Veredicto.RECHAZADO)


def test_hallazgos_ordenados_por_severidad_y_sin_repetir():
    validacion = Validacion(
        plan_pruebas=PLAN,
        ejecucion=EJECUCION,
        hallazgos=(
            hallazgo(REGLAS, "CAL-MT-009", "src/a.py:3", "línea larga", "ruff:E501"),
            hallazgo(REGLAS, "CAL-SG-002", "src/a.py:1", "eval", "ruff:S307"),
            hallazgo(REGLAS, "CAL-SG-002", "src/a.py:1", "eval", "ruff:S307"),
        ),
    )
    dictamen = dictaminar(validacion)
    assert [h.regla for h in dictamen.hallazgos] == ["CAL-SG-002", "CAL-MT-009"]
    assert "### Severidad alta" in dictamen.reporte and "### Severidad baja" in dictamen.reporte


# Juez -------------------------------------------------------------------------------------------


def juez(cliente, registro=None) -> InvocadorNodo:
    parametros = ParametrosNodo(
        nodo="N14", despliegue="gpt-6-luna", esfuerzo="low", max_tokens_salida=6000
    )
    return InvocadorNodo(
        cliente,
        parametros,
        cargar_prompt("tester", "veredicto"),
        registro or RegistroEnMemoria(),
        TARIFAS,
    )


def juicios(*items) -> dict:
    return {
        "juicios": [
            {"id_caso": i, "cumple": c, "justificacion": "Compara con 6", "sugerencia": s}
            for i, c, s in items
        ]
    }


def test_el_juez_recibe_solo_los_casos_cuyas_pruebas_pasaron(cliente_falso, completar_respuesta):
    sin_esc_02 = PRUEBAS.replace("test_rf_01_esc_02_rechaza", "test_rechaza")
    respuesta = juicios(("CP-RF-01-ESC-01", True, ""))
    cliente = cliente_falso(completar_respuesta(respuesta, modelo=MODELO))
    dictamen = dictaminar(pruebas=sin_esc_02, juez=juez(cliente))
    datos = json.loads(cliente.llamadas[0]["messages"][-1]["content"])
    enviados = datos["casos"]
    # El juez ve completos los archivos de prueba: ahí están los fixtures del «dado que».
    assert datos["archivos_prueba"] == [{"ruta": "tests/test_avaluo.py", "contenido": sin_esc_02}]
    assert [c["id_caso"] for c in enviados] == ["CP-RF-01-ESC-01"]
    assert enviados[0]["pruebas"][0]["codigo"].startswith("def test_rf_01_esc_01_calcula")
    assert enviados[0]["entonces"] == "el avalúo es 6"
    assert dictamen.veredictos[0].cumple
    assert "Compara con 6" in dictamen.veredictos[0].evidencia


def test_el_juez_detecta_una_prueba_que_no_verifica_el_escenario(
    cliente_falso, completar_respuesta
):
    respuesta = juicios(
        ("CP-RF-01-ESC-01", False, "Compara con el valor exacto 6"),
        ("CP-RF-01-ESC-02", True, ""),
    )
    cliente = cliente_falso(completar_respuesta(respuesta, modelo=MODELO))
    dictamen = dictaminar(juez=juez(cliente))
    assert dictamen.veredicto is Veredicto.RECHAZADO
    (juicio,) = [h for h in dictamen.hallazgos if h.origen == "juez"]
    assert juicio.regla == "CAL-FS-001"
    assert juicio.sugerencia == "Compara con el valor exacto 6"
    assert juicio.ubicacion == "tests/test_avaluo.py::test_rf_01_esc_01_calcula"


def test_el_juez_reintenta_si_omite_un_caso(cliente_falso, completar_respuesta):
    incompleta = juicios(("CP-RF-01-ESC-01", True, ""))
    completa = juicios(("CP-RF-01-ESC-01", True, ""), ("CP-RF-01-ESC-02", True, ""))
    cliente = cliente_falso(
        completar_respuesta(incompleta, modelo=MODELO),
        completar_respuesta(completa, modelo=MODELO),
    )
    dictamen = dictaminar(juez=juez(cliente))
    assert dictamen.veredicto is Veredicto.APROBADO
    problemas = json.loads(cliente.llamadas[1]["messages"][-1]["content"])
    assert "CP-RF-01-ESC-02" in problemas["problemas_intento_anterior"][0]


def test_si_el_juez_no_da_un_juicio_valido_los_casos_quedan_sin_juicio(
    cliente_falso, completar_respuesta
):
    # Un incumplido sin sugerencia es inválido; tras el reintento, el juez no bloquea la versión:
    # los casos cuyas pruebas pasan quedan sin juicio y la persona los revisa en N17.
    sin_sugerencia = juicios(("CP-RF-01-ESC-01", False, ""), ("CP-RF-01-ESC-02", True, ""))
    cliente = cliente_falso(
        completar_respuesta(sin_sugerencia, modelo=MODELO),
        completar_respuesta(sin_sugerencia, modelo=MODELO),
    )
    dictamen = dictaminar(juez=juez(cliente))
    assert dictamen.veredicto is Veredicto.APROBADO
    assert all(v.cumple for v in dictamen.veredictos)
    assert all(
        "sin juicio del modelo: el juez no respondió" in v.evidencia for v in dictamen.veredictos
    )
    assert "necesita una sugerencia" in dictamen.veredictos[0].evidencia


def test_sin_casos_por_juzgar_no_se_llama_al_modelo(cliente_falso):
    sin_pruebas = "def test_otro():\n    assert True\n"
    dictamen = dictaminar(pruebas=sin_pruebas, juez=juez(cliente_falso()))
    assert dictamen.veredicto is Veredicto.RECHAZADO
    assert not any(v.cumple for v in dictamen.veredictos)


# N13 --------------------------------------------------------------------------------------------


class RecuperadorFalso:
    def __init__(self):
        self.consultas = []

    def recuperar(self, consulta, colecciones=None, k=None):
        self.consultas.append((consulta, tuple(colecciones), k))
        fragmento = FragmentoRecuperado(
            id=len(self.consultas),
            coleccion=Coleccion.CRITERIOS_CALIDAD,
            documento_id="cal-sg",
            version_documento="1.0",
            titulo=f"Fragmento para {consulta[:20]}",
            contenido=f"Contenido {consulta[:20]}",
            metadatos={},
            similitud=0.6,
            rango_semantico=1,
            rango_lexico=1,
            puntaje=0.03,
        )
        return ResultadoRecuperacion(
            agente=Agente.TESTER,
            consulta=consulta,
            colecciones=tuple(colecciones),
            fragmentos=(fragmento,),
            descartados=(),
        )


def test_n13_consulta_cada_regla_citada_y_los_criterios_del_juicio():
    recuperador = RecuperadorFalso()
    validacion = con_hallazgo("CAL-SG-002").model_copy(
        update={
            "hallazgos": (
                hallazgo(REGLAS, "CAL-SG-002", "a", "eval", "x"),
                hallazgo(REGLAS, "CAL-MT-001", "b", "doc", "x"),
                hallazgo(REGLAS, "CAL-SG-002", "c", "eval", "x"),
            )
        }
    )
    contexto = recuperar_criterios(recuperador, validacion)
    consultas = [consulta for consulta, _, _ in recuperador.consultas]
    assert consultas[:2] == ["CAL-MT-001", "CAL-SG-002"]
    assert consultas[2:] == [consulta for consulta, _ in CONSULTAS_FIJAS]
    assert all(
        colecciones == (Coleccion.CRITERIOS_CALIDAD,) for _, colecciones, _ in recuperador.consultas
    )
    assert len(contexto.fragmentos["criterios_calidad"]) == len(consultas)


def test_una_libreria_que_falta_tiene_una_sugerencia_precisa():
    mensaje = "ModuleNotFoundError: No module named 'openpyxl'"
    assert "«openpyxl»" in sugerencia_de_ejecucion(mensaje)
    # Un módulo propio que no se encuentra, o cualquier otra falla, usan la sugerencia de la regla.
    assert sugerencia_de_ejecucion("No module named 'dominio.avaluo'") is None
    assert sugerencia_de_ejecucion("AssertionError: assert 1 == 2") is None

    ejecucion = EjecucionPruebas(
        pruebas=(
            PruebaEjecutada(
                archivo="tests/test_reporte.py",
                nombre="test_rf_01_esc_01_genera",
                resultado=ResultadoPrueba.FALLO,
                mensaje=mensaje,
            ),
        )
    )
    [falla] = hallazgos_de_ejecucion(ejecucion, cargar_reglas_calidad())
    assert falla.regla == "CAL-FS-002" and "«openpyxl»" in falla.sugerencia
