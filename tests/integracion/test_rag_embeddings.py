"""Condición de terminado del paso 6 con el modelo real BGE-M3.

Se ingiere el corpus real en un esquema temporal y cada agente consulta con preguntas pensadas
para atraer fragmentos de colecciones ajenas: todos los resultados deben pertenecer a sus
colecciones autorizadas. Requiere los servicios `db` y `embeddings` de docker compose.
"""

import math
import uuid

import psycopg
import pytest

from multiagente.core.configuracion import ConfiguracionBaseDatos, ConfiguracionRecuperacion
from multiagente.persistencia.migraciones import aplicar_migraciones
from multiagente.rag.colecciones import ACCESO, Agente, ErrorAccesoNoAutorizado
from multiagente.rag.documentos import cargar_corpus
from multiagente.rag.embeddings import VectorizadorTEI
from multiagente.rag.ingesta import ingestar
from multiagente.rag.recuperacion import Recuperador

pytestmark = pytest.mark.embeddings

CONFIGURACION = ConfiguracionRecuperacion()

CONSULTAS_AJENAS = {
    Agente.ELICITADOR: [
        "Regla CAL-MT-005 de modularidad conforme a la especificación",
        "Arquitectura hexagonal de puertos y adaptadores",
        "Un hallazgo de severidad alta bloquea la aprobación del código",
    ],
    Agente.ARQUITECTO: [
        "¿Cómo se calcula el avalúo catastral de un predio?",
        "Criterios INVEST para evaluar una historia de usuario",
        "Precisión en cálculos monetarios sin punto flotante",
    ],
    Agente.TESTER: [
        "Mutación catastral de primera clase por cambio de propietario",
        "Plantilla de la historia de usuario: como, quiero, para",
        "ARQ-04 servicio API REST con contrato de interfaz",
    ],
}


@pytest.fixture(scope="module")
def vectorizador():
    return VectorizadorTEI()


@pytest.fixture(scope="module")
def base_real(vectorizador):
    cadena = ConfiguracionBaseDatos().cadena_conexion()
    esquema = f"prueba_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(cadena, autocommit=True) as administracion:
        administracion.execute(f'CREATE SCHEMA "{esquema}"')
    try:
        with psycopg.connect(cadena, options=f"-c search_path={esquema},public") as conexion:
            aplicar_migraciones(conexion)
            ingestar(conexion, cargar_corpus(), vectorizador)
            conexion.commit()
            yield conexion
    finally:
        with psycopg.connect(cadena, autocommit=True) as administracion:
            administracion.execute(f'DROP SCHEMA "{esquema}" CASCADE')


def test_vectores_de_dimension_1024_normalizados(vectorizador):
    vector = vectorizador.vectorizar(["Avalúo catastral del predio"])[0]
    assert len(vector) == 1024
    assert math.isclose(math.sqrt(sum(v * v for v in vector)), 1.0, rel_tol=1e-3)


@pytest.mark.parametrize(
    ("agente", "consulta"),
    [
        (agente, consulta)
        for agente, consultas in CONSULTAS_AJENAS.items()
        for consulta in consultas
    ],
)
def test_cada_agente_solo_recupera_de_sus_colecciones(base_real, vectorizador, agente, consulta):
    resultado = Recuperador(base_real, vectorizador, agente, CONFIGURACION).recuperar(
        consulta, k=20
    )
    autorizadas = ACCESO[agente]
    assert {f.coleccion for f in resultado.fragmentos} <= autorizadas
    assert {d.fragmento.coleccion for d in resultado.descartados} <= autorizadas


def test_desarrollador_no_recupera(base_real, vectorizador):
    with pytest.raises(ErrorAccesoNoAutorizado):
        Recuperador(base_real, vectorizador, Agente.DESARROLLADOR, CONFIGURACION)


@pytest.mark.parametrize(
    ("agente", "consulta", "esperado"),
    [
        (Agente.ELICITADOR, "¿Cómo se calcula el avalúo catastral de un predio?", "dom-003"),
        (
            Agente.ARQUITECTO,
            "Necesito exponer las funciones del módulo como un servicio HTTP",
            "arq-arq-04",
        ),
        (
            Agente.TESTER,
            "El código usa float para calcular valores en pesos",
            "CAL-FS-005",
        ),
    ],
)
def test_calidad_semantica(base_real, vectorizador, agente, consulta, esperado):
    resultado = Recuperador(base_real, vectorizador, agente, CONFIGURACION).recuperar(consulta, k=3)
    encontrados = [(f.documento_id, f.metadatos.get("regla")) for f in resultado.fragmentos]
    assert any(esperado in identificadores for identificadores in encontrados), encontrados


def test_consulta_fuera_de_dominio_declara_ausencia(base_real, vectorizador):
    resultado = Recuperador(base_real, vectorizador, Agente.ELICITADOR, CONFIGURACION).recuperar(
        "Receta tradicional de arepas con chocolate caliente"
    )
    assert resultado.sin_contexto
    assert resultado.descartados
