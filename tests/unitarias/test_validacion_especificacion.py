"""Validaciones de la especificación de diseño en N9 (Anexo B) y catálogos del arquitecto."""

import json
import re
from pathlib import Path

import pytest

from multiagente.agentes.arquitecto.catalogo import (
    arquitecturas_del_catalogo,
    cargar_catalogo_tecnologico,
)
from multiagente.agentes.arquitecto.validacion import validar_especificacion
from multiagente.core.esquemas.comunes import Enunciado, Impacto, Prioridad
from multiagente.core.esquemas.especificacion_diseno import EspecificacionDiseno
from multiagente.core.esquemas.requerimiento import (
    Descripcion,
    EscenarioAceptacion,
    RequerimientoFormal,
    TipoSolicitud,
)
from multiagente.orquestador.estado import Requerimientos

CATALOGO = cargar_catalogo_tecnologico()
ARQUITECTURAS = arquitecturas_del_catalogo()


def test_catalogo_tecnologico_leido_de_la_base_de_conocimiento():
    assert CATALOGO.autorizadas == {
        "pydantic",
        "typer",
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "psycopg",
        "pandas",
        "openpyxl",
        "numpy",
        "pytest",
    }
    assert CATALOGO.estandar == {"datetime", "zoneinfo", "decimal", "logging"}


def test_catalogo_cerrado_de_arquitecturas():
    assert ARQUITECTURAS == {f"ARQ-0{n}" for n in range(1, 7)}


def requerimiento(identificador: str) -> RequerimientoFormal:
    return RequerimientoFormal(
        id_requerimiento=identificador,
        version="0.1",
        proyecto="Catastro",
        tipo_solicitud=TipoSolicitud.NUEVO,
        impacto=Impacto.ALTO,
        modulo="avaluo",
        autor="Agente elicitador",
        area_funcional="Liquidación",
        titulo=Enunciado(como="liquidador catastral", quiero="calcular el avalúo", para="liquidar"),
        descripcion=Descripcion(
            precondicion="El predio existe",
            regla_negocio="El avalúo es la suma del terreno y la construcción",
            datos_entrada=[],
            datos_salida=[],
        ),
        criterios_aceptacion=[
            EscenarioAceptacion(
                id="ESC-01", dado_que="un predio", cuando="se calcula", entonces="ok"
            )
        ],
        prioridad=Prioridad.ALTA,
    )


APROBADOS = Requerimientos(requerimientos=(requerimiento("RF-01"), requerimiento("RF-02")))


def especificacion(**cambios) -> EspecificacionDiseno:
    datos = {
        "id_especificacion": "ED-01",
        "version": "0.1",
        "arquitectura_base": "ARQ-01",
        "requerimientos_cubiertos": ["RF-01", "RF-02"],
        "modulos": [
            {
                "nombre": "dominio.predio",
                "ruta": "src/dominio/predio.py",
                "responsabilidad": "Predio y su avalúo",
                "capa": "dominio",
                "interfaces_publicas": [
                    {
                        "nombre": "Predio",
                        "tipo": "clase",
                        "firma": "Predio(numero_predial: str, area_terreno: Decimal)",
                        "descripcion": "Predio con sus atributos físicos",
                    },
                    {
                        "nombre": "calcular_avaluo",
                        "tipo": "funcion",
                        "firma": "calcular_avaluo(predio: Predio, valor_m2: Decimal) -> Decimal",
                        "descripcion": "Calcula el avalúo del predio",
                    },
                ],
                "requerimientos": ["RF-01"],
            },
            {
                "nombre": "aplicacion.liquidacion",
                "ruta": "src/aplicacion/liquidacion.py",
                "responsabilidad": "Caso de uso de liquidación",
                "capa": "aplicacion",
                "interfaces_publicas": [
                    {
                        "nombre": "liquidar",
                        "tipo": "funcion",
                        "firma": "liquidar(numero_predial: str) -> Decimal",
                        "descripcion": "Liquida el impuesto del predio",
                    }
                ],
                "dependencias_permitidas": ["dominio.predio"],
                "requerimientos": ["RF-02"],
            },
        ],
        "modelo_datos": [
            {
                "nombre": "Predio",
                "campos": [
                    {"nombre": "numero_predial", "tipo": "str", "obligatorio": True},
                    {"nombre": "avaluo_total", "tipo": "Decimal", "obligatorio": True},
                ],
            }
        ],
        "dependencias_externas": [{"paquete": "pydantic", "proposito": "validar datos"}],
        "reglas_de_dependencia": ["La capa de dominio no importa de ninguna otra capa"],
    }
    for ruta, valor in cambios.items():
        destino = datos
        *intermedios, ultimo = ruta.split("__")
        for clave in intermedios:
            destino = destino[int(clave)] if clave.isdigit() else destino[clave]
        destino[int(ultimo) if ultimo.isdigit() else ultimo] = valor
    return EspecificacionDiseno.model_validate(datos)


def validar(espec: EspecificacionDiseno, requerimientos: Requerimientos = APROBADOS) -> list[str]:
    return validar_especificacion(espec, requerimientos, CATALOGO, ARQUITECTURAS)


def test_especificacion_valida_no_tiene_errores():
    assert validar(especificacion()) == []


def test_el_ejemplo_de_la_plantilla_arq_002_cumple_salvo_la_cobertura():
    plantilla = Path(__file__).resolve().parents[2] / (
        "knowledge_base/arquitecturas_referencia/02-especificacion-de-diseno.md"
    )
    texto = plantilla.read_text(encoding="utf-8")
    ejemplo = EspecificacionDiseno.model_validate(
        json.loads(re.search(r"```json\n(.*?)\n```", texto, re.S).group(1))
    )
    aprobados = Requerimientos(requerimientos=(requerimiento("RF-021"),))
    # El ejemplo es un extracto: declara RF-022 y RF-023 cubiertos sin módulo que los implemente.
    assert validar(ejemplo, aprobados) == [
        "Validación 2 · cobertura: RF-022 no es un requerimiento aprobado",
        "Validación 2 · cobertura: RF-023 no es un requerimiento aprobado",
    ]


@pytest.mark.parametrize(
    ("cambios", "esperado"),
    [
        ({"modulos__1__requerimientos": ["RF-01"]}, "Validación 2 · cobertura: RF-02 no está"),
        ({"arquitectura_base": "ARQ-07"}, "Validación 3 · catálogo: ARQ-07 no pertenece"),
        (
            {"dependencias_externas": [{"paquete": "requests", "proposito": "HTTP"}]},
            "Validación 3 · catálogo: requests no pertenece",
        ),
        (
            {"dependencias_externas": [{"paquete": "decimal", "proposito": "dinero"}]},
            "decimal es de la biblioteca estándar",
        ),
        (
            {"modulos__0__interfaces_publicas__1__firma": "calcular_avaluo(predio: Predio)"},
            "no declara el tipo de retorno",
        ),
        (
            {"modulos__0__interfaces_publicas__1__firma": "calcular_avaluo(predio) -> Decimal"},
            "no declara el tipo de ['predio']",
        ),
        (
            {"modulos__0__interfaces_publicas__1__firma": "calcular avaluo del predio"},
            "no es una firma de Python válida",
        ),
        (
            {"modulos__0__interfaces_publicas__1__firma": "avaluo(predio: Predio) -> Decimal"},
            "declara el nombre avaluo",
        ),
        ({"modulos__0__ruta": "src/predio.py"}, "no corresponde al módulo dominio.predio"),
        (
            {
                "modulos__0__ruta": "src/infraestructura/predio.py",
                "modulos__0__nombre": "infraestructura.predio",
            },
            "no está en una carpeta de la capa «dominio»",
        ),
        (
            {
                "modulos__0__nombre": "io.predio",
                "modulos__0__ruta": "src/io/predio.py",
                "modulos__0__capa": "io",
            },
            "el paquete «io» de io.predio tapa un módulo de la biblioteca estándar",
        ),
        (
            {"modelo_datos__0__campos__1__tipo": "float"},
            "Dinero en Decimal: el campo Predio.avaluo_total es monetario y usa float",
        ),
        (
            {
                "modulos__0__interfaces_publicas__1__firma": (
                    "calcular_avaluo(predio: Predio, valor_m2: float) -> Decimal"
                )
            },
            "el parámetro valor_m2 de dominio.predio.calcular_avaluo es monetario y usa float",
        ),
    ],
)
def test_cada_regla_detecta_su_error(cambios, esperado):
    if "modulos__0__nombre" in cambios:
        # Renombrar el módulo exige actualizar la dependencia que lo nombra.
        cambios["modulos__1__dependencias_permitidas"] = [cambios["modulos__0__nombre"]]
    errores = validar(especificacion(**cambios))
    assert any(esperado in error for error in errores), errores


def test_pytest_y_las_firmas_con_self_se_admiten():
    espec = especificacion(
        **{
            "dependencias_externas": [{"paquete": "pytest", "proposito": "pruebas"}],
            "modulos__0__interfaces_publicas__0__firma": "Predio(self, numero_predial: str)",
        }
    )
    assert validar(espec) == []


@pytest.mark.parametrize(
    ("firma", "funcion"),
    [
        ("suscribir(self, manejador: callable) -> None", "callable"),
        ("suscribir(self, manejadores: list[callable]) -> None", "callable"),
        ("leer(clave: str) -> any", "any"),
    ],
)
def test_una_funcion_integrada_no_es_un_tipo(firma, funcion):
    espec = especificacion(
        **{
            "modulos__0__interfaces_publicas__1__nombre": firma.split("(")[0],
            "modulos__0__interfaces_publicas__1__firma": firma,
        }
    )
    assert any(f"usa «{funcion}», que es una función y no un tipo" in e for e in validar(espec))


def test_callable_de_collections_abc_se_admite():
    firma = "suscribir(manejador: Callable[[Predio], None]) -> None"
    espec = especificacion(
        **{
            "modulos__0__interfaces_publicas__1__nombre": "suscribir",
            "modulos__0__interfaces_publicas__1__firma": firma,
        }
    )
    assert validar(espec) == []


@pytest.mark.parametrize(
    ("firma", "propio"),
    [
        ("consumir_venta(self, evento: str) -> None", "self"),
        ("consumir_venta(cls, evento: str) -> None", "cls"),
        ("consumir_venta(evento: str, self) -> None", "self"),
    ],
)
def test_una_funcion_de_modulo_no_recibe_self_ni_cls(firma, propio):
    # Corrida de la fase 7 (ADR-0015): los consumidores de ARQ-06 se declararon como funciones
    # con self, y el código generado solo cumplía el estilo silenciándolo.
    espec = especificacion(
        **{
            "modulos__0__interfaces_publicas__1__nombre": "consumir_venta",
            "modulos__0__interfaces_publicas__1__firma": firma,
        }
    )
    esperado = f"la función dominio.predio.consumir_venta recibe {propio}, que solo lleva un método"
    assert any(esperado in error for error in validar(espec)), validar(espec)


def con_metodo(nombre: str, firma: str, tipo: str = "funcion") -> EspecificacionDiseno:
    datos = especificacion().model_dump(mode="json")
    datos["modulos"][0]["interfaces_publicas"].append(
        {
            "nombre": nombre,
            "tipo": tipo,
            "firma": firma,
            "descripcion": "Operación del predio",
            "excepciones": [],
        }
    )
    return EspecificacionDiseno.model_validate(datos)


def test_un_metodo_de_una_clase_declarada_se_admite():
    assert validar(con_metodo("Predio.area_total", "area_total(self) -> Decimal")) == []
    # El modelo a veces repite la clase en la firma; se admite, como el prefijo `def`.
    assert validar(con_metodo("Predio.area_total", "Predio.area_total(self) -> Decimal")) == []
    assert validar(con_metodo("Predio.desde_texto", "desde_texto(cls, texto: str) -> Predio")) == []


@pytest.mark.parametrize(
    ("nombre", "firma", "tipo", "esperado"),
    [
        (
            "Avaluo.calcular",
            "calcular(self) -> Decimal",
            "funcion",
            "el método dominio.predio.Avaluo.calcular es de la clase Avaluo, que dominio.predio no "
            "declara",
        ),
        ("Predio.area_total", "area_total() -> Decimal", "funcion", "recibe self (o cls)"),
        ("Predio.Lote.area", "area(self) -> Decimal", "funcion", "con un solo punto"),
        ("Predio.Lote", "Lote(area: Decimal)", "clase", "se declara en el nivel superior"),
        ("Predio.area_total", "area(self) -> Decimal", "funcion", "declara el nombre area"),
        ("Predio.area_total", "area_total(self)", "funcion", "no declara el tipo de retorno"),
    ],
)
def test_reglas_de_los_metodos(nombre, firma, tipo, esperado):
    errores = validar(con_metodo(nombre, firma, tipo))
    assert any(esperado in error for error in errores), errores
