"""Agente desarrollador con modelo falso: mensajes, verificación, reintento, corrección y grafo."""

import inspect
import json
import subprocess
import sys
from decimal import Decimal

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from multiagente.agentes.desarrollador.generacion import (
    IntentoRechazado,
    SalidaGeneracion,
    mensajes_generacion,
    version_desde_salida,
)
from multiagente.agentes.desarrollador.servicio import (
    AgenteDesarrollador,
    crear_agente_desarrollador,
)
from multiagente.agentes.desarrollador.verificacion import SECCIONES_USO
from multiagente.core.configuracion import ConfiguracionOrquestador
from multiagente.core.esquemas.comunes import Enunciado, Impacto, Prioridad
from multiagente.core.esquemas.requerimiento import (
    DatoEntrada,
    DatoSalida,
    Descripcion,
    EscenarioAceptacion,
    HistoriaUsuario,
    RequerimientoFormal,
    TipoSolicitud,
)
from multiagente.core.estilo import cargar_estilo
from multiagente.llm.costos import Tarifa
from multiagente.llm.invocador import ErrorValidacionSalida, InvocadorNodo, ParametrosNodo
from multiagente.llm.prompts import cargar_prompt
from multiagente.llm.traza import RegistroEnMemoria
from multiagente.orquestador.ejecucion import avanzar, configuracion_hilo, iniciar_sesion
from multiagente.orquestador.estado import (
    Arquitectura,
    Contexto,
    Fase,
    Requerimientos,
    Validacion,
    VersionCodigo,
)
from multiagente.orquestador.grafo import construir_grafo
from multiagente.orquestador.servicios import Servicios, Sintesis
from multiagente.orquestador.simulacion import (
    RUTA_MODULO,
    ElicitadorFijo,
    ServiciosSimulados,
    aprobar,
    rechazar,
)
from multiagente.persistencia.puntos_control import serializador

TARIFAS = {
    "gpt-6.1-sol": Tarifa(
        entrada=Decimal("2.00"), entrada_cacheada=Decimal("0.10"), salida=Decimal("10.00")
    )
}
MODELO = "gpt-6.1-sol-2026-09-29"
ESTILO = cargar_estilo()

RF1 = RequerimientoFormal(
    id_requerimiento="RF-01",
    version="0.1",
    proyecto="Catastro",
    tipo_solicitud=TipoSolicitud.NUEVO,
    impacto=Impacto.MEDIO,
    modulo="simulado",
    autor="Agente elicitador",
    area_funcional="Simulación",
    titulo=Enunciado(
        como="analista catastral", quiero="normalizar un dato", para="registrarlo igual"
    ),
    descripcion=Descripcion(
        precondicion="El dato llega del formulario",
        regla_negocio="El dato se registra en mayúsculas; un dato vacío se rechaza.",
        datos_entrada=[DatoEntrada(nombre="dato", tipo="str", obligatorio=True)],
        datos_salida=[DatoSalida(nombre="dato_normalizado", tipo="str")],
    ),
    criterios_aceptacion=[
        EscenarioAceptacion(
            id="ESC-01", dado_que="un dato «abc»", cuando="se ejecuta", entonces="«ABC»"
        ),
        EscenarioAceptacion(
            id="ESC-02", dado_que="un dato vacío", cuando="se ejecuta", entonces="rechaza"
        ),
    ],
    prioridad=Prioridad.MEDIA,
)
SINTESIS = Sintesis(
    historias=(HistoriaUsuario(id="HU-01", enunciado=RF1.titulo),), requerimientos=(RF1,)
)
REQUERIMIENTOS = Requerimientos(historias=SINTESIS.historias, requerimientos=(RF1,))
ESPECIFICACION = (
    ServiciosSimulados().disenar(REQUERIMIENTOS, Contexto(), Arquitectura()).especificacion
)

MODULO = '''"""Funcionalidad simulada."""


def ejecutar(dato: str) -> str:
    """Devuelve el dato en mayúsculas.

    Args:
        dato: Dato a normalizar.

    Returns:
        El dato en mayúsculas.

    Raises:
        ValueError: Si el dato está vacío.
    """
    if not dato:
        raise ValueError("El dato no puede estar vacío")
    return dato.upper()
'''

PRUEBAS = """import pytest

from simulado.modulo import ejecutar


def test_rf_01_esc_01_normaliza():
    assert ejecutar("abc") == "ABC"


def test_rf_01_esc_02_rechaza_vacio():
    with pytest.raises(ValueError):
        ejecutar("")
"""


USO = "# Uso\n\n" + "\n\n".join(f"## {s}\n\nLlame a `ejecutar`." for s in SECCIONES_USO)


def salida(archivos: dict[str, str], uso: str = USO) -> dict:
    return {
        "archivos": [
            {"ruta": ruta, "contenido": contenido} for ruta, contenido in archivos.items()
        ],
        "documentacion_uso": uso,
    }


VALIDA = salida({RUTA_MODULO: MODULO, "tests/test_modulo.py": PRUEBAS})


def agente(cliente, registro=None) -> AgenteDesarrollador:
    parametros = ParametrosNodo(
        nodo="N10",
        despliegue="gpt-6.1-sol",
        esfuerzo="low",
        max_tokens_salida=32000,
        tiempo_espera_s=600,
    )
    invocador = InvocadorNodo(
        cliente,
        parametros,
        cargar_prompt("desarrollador", "generacion"),
        registro or RegistroEnMemoria(),
        TARIFAS,
    )
    return AgenteDesarrollador(invocador, ESTILO)


def datos_de(llamada, indice):
    return json.loads(llamada["messages"][indice]["content"])


# Mensajes ---------------------------------------------------------------------------------------


def test_mensajes_sin_contexto_recuperado():
    mensajes = mensajes_generacion(REQUERIMIENTOS, ESPECIFICACION, ESTILO, Validacion(), None)
    assert len(mensajes) == 1
    datos = json.loads(mensajes[0]["content"])
    assert set(datos) == {"estilo", "especificacion", "requerimientos"}
    assert datos["estilo"] == {"archivo": "ruff.toml", "contenido": ESTILO.texto}
    assert datos["especificacion"]["modulos"][0]["ruta"] == RUTA_MODULO
    assert datos["requerimientos"][0]["id_requerimiento"] == "RF-01"
    assert "contexto" not in mensajes[0]["content"]


def test_correccion_lleva_la_version_previa_y_los_defectos_etiquetados():
    previa = VersionCodigo(numero=1, archivos={RUTA_MODULO: MODULO})
    validacion = Validacion(retroalimentacion=("Falta validar espacios", "Renombrar la prueba"))
    mensajes = mensajes_generacion(REQUERIMIENTOS, ESPECIFICACION, ESTILO, validacion, previa)
    correccion = json.loads(mensajes[1]["content"])["correccion"]
    assert correccion["version_previa"] == {
        "numero": 1,
        "archivos": [{"ruta": RUTA_MODULO, "contenido": MODULO}],
    }
    assert correccion["retroalimentacion"] == [
        {"etiqueta": "D1", "defecto": "Falta validar espacios"},
        {"etiqueta": "D2", "defecto": "Renombrar la prueba"},
    ]


def test_el_desarrollador_no_tiene_recuperacion():
    # Decisión 1: la fábrica no recibe conexión ni vectorizador, y nada del agente importa RAG.
    assert list(inspect.signature(crear_agente_desarrollador).parameters) == [
        "registrador",
        "cliente",
    ]
    codigo = (
        "import sys, multiagente.agentes.desarrollador.servicio; "
        "print(any(m.startswith('multiagente.rag') for m in sys.modules))"
    )
    resultado = subprocess.run(
        [sys.executable, "-c", codigo], capture_output=True, text=True, check=True
    )
    assert resultado.stdout.strip() == "False"


# Generación -------------------------------------------------------------------------------------


def test_genera_la_primera_version(cliente_falso, completar_respuesta):
    cliente = cliente_falso(completar_respuesta(VALIDA, modelo=MODELO, salida=9000))
    registro = RegistroEnMemoria()
    version = agente(cliente, registro).generar(REQUERIMIENTOS, ESPECIFICACION, Validacion(), None)

    assert version.numero == 1
    assert set(version.archivos) == {RUTA_MODULO, "tests/test_modulo.py", "USO.md"}
    assert version.archivos["USO.md"].endswith("`ejecutar`.\n")
    assert version.defectos_atendidos == ()
    assert version.huella_estilo == ESTILO.huella

    argumentos = cliente.llamadas[0]
    assert argumentos["model"] == "gpt-6.1-sol"
    assert argumentos["reasoning_effort"] == "low"
    assert argumentos["max_completion_tokens"] == 32000
    assert argumentos["response_format"]["json_schema"]["name"] == "SalidaGeneracion"
    assert cliente.opciones == {"timeout": 600}
    (llamada,) = registro.llamadas
    assert (llamada.nodo, llamada.prompt) == ("N10", "desarrollador.generacion@1.5")
    assert llamada.costo_usd == Decimal("0.091")


def test_reintenta_sobre_el_intento_rechazado(cliente_falso, completar_respuesta):
    # El reintento devuelve solo la prueba corregida: se combina sobre el intento, y la versión
    # conserva el módulo y el documento de uso del primero.
    sin_esc_02 = salida(
        {RUTA_MODULO: MODULO, "tests/test_modulo.py": PRUEBAS.replace("rf_01_esc_02_", "")}
    )
    cliente = cliente_falso(
        completar_respuesta(sin_esc_02, modelo=MODELO),
        completar_respuesta(salida({"tests/test_modulo.py": PRUEBAS}, uso=""), modelo=MODELO),
    )
    version = agente(cliente).generar(REQUERIMIENTOS, ESPECIFICACION, Validacion(), None)

    assert version.numero == 1
    assert version.archivos == primera_version().archivos
    intento = datos_de(cliente.llamadas[1], -1)["intento_rechazado"]
    assert {archivo["ruta"] for archivo in intento["archivos"]} == {
        RUTA_MODULO,
        "tests/test_modulo.py",
        "USO.md",
    }
    assert any("falta una prueba test_rf_01_esc_02_" in p for p in intento["problemas"])
    # El reintento repite los mensajes de la generación y agrega el intento.
    assert datos_de(cliente.llamadas[1], 1) == datos_de(cliente.llamadas[0], 1)
    assert len(cliente.llamadas[1]["messages"]) == len(cliente.llamadas[0]["messages"]) + 1


def test_una_salida_que_no_se_combina_se_reintenta_completa(cliente_falso, completar_respuesta):
    repetida = {
        "archivos": [
            {"ruta": RUTA_MODULO, "contenido": MODULO},
            {"ruta": RUTA_MODULO, "contenido": MODULO},
        ],
        "documentacion_uso": USO,
    }
    cliente = cliente_falso(
        completar_respuesta(repetida, modelo=MODELO),
        completar_respuesta(VALIDA, modelo=MODELO),
    )
    version = agente(cliente).generar(REQUERIMIENTOS, ESPECIFICACION, Validacion(), None)
    assert version.archivos == primera_version().archivos
    intento = datos_de(cliente.llamadas[1], -1)["intento_rechazado"]
    assert intento["archivos"] == []
    assert "repetidos" in intento["problemas"][0]


def test_dos_salidas_invalidas_hacen_fallar_el_nodo(cliente_falso, completar_respuesta):
    sin_modulo = salida({"tests/test_modulo.py": PRUEBAS})
    cliente = cliente_falso(
        completar_respuesta(sin_modulo, modelo=MODELO),
        completar_respuesta(sin_modulo, modelo=MODELO),
    )
    with pytest.raises(ErrorValidacionSalida, match="falta src/simulado/modulo.py"):
        agente(cliente).generar(REQUERIMIENTOS, ESPECIFICACION, Validacion(), None)


# Corrección (RF-19) ---------------------------------------------------------------------------


def primera_version() -> VersionCodigo:
    return version_desde_salida(
        SalidaGeneracion.model_validate(VALIDA),
        REQUERIMIENTOS,
        ESPECIFICACION,
        Validacion(),
        None,
        ESTILO,
    )


def test_correccion_combina_solo_los_archivos_que_cambian(cliente_falso, completar_respuesta):
    previa = primera_version()
    corregido = MODULO.replace("if not dato:", "if not dato.strip():")
    cliente = cliente_falso(
        completar_respuesta(salida({RUTA_MODULO: corregido}, uso=""), modelo=MODELO)
    )
    validacion = Validacion(retroalimentacion=("Un dato con solo espacios debe rechazarse",))
    version = agente(cliente).generar(REQUERIMIENTOS, ESPECIFICACION, validacion, previa)

    assert version.numero == 2
    assert version.archivos[RUTA_MODULO] == corregido
    assert version.archivos["tests/test_modulo.py"] == previa.archivos["tests/test_modulo.py"]
    assert version.archivos["USO.md"] == previa.archivos["USO.md"]
    assert version.defectos_atendidos == validacion.retroalimentacion
    assert len(datos_de(cliente.llamadas[0], 2)["correccion"]["version_previa"]["archivos"]) == 3


def test_el_reintento_de_una_correccion_parte_del_intento(cliente_falso, completar_respuesta):
    # La corrección cambia el módulo pero rompe una prueba; el reintento arregla solo la prueba.
    previa = primera_version()
    corregido = MODULO.replace("if not dato:", "if not dato.strip():")
    rota = PRUEBAS.replace("rf_01_esc_02_", "")
    cliente = cliente_falso(
        completar_respuesta(
            salida({RUTA_MODULO: corregido, "tests/test_modulo.py": rota}, uso=""), modelo=MODELO
        ),
        completar_respuesta(salida({"tests/test_modulo.py": PRUEBAS}, uso=""), modelo=MODELO),
    )
    validacion = Validacion(retroalimentacion=("Un dato con solo espacios debe rechazarse",))
    version = agente(cliente).generar(REQUERIMIENTOS, ESPECIFICACION, validacion, previa)

    assert version.numero == 2
    assert version.archivos[RUTA_MODULO] == corregido
    assert version.archivos["tests/test_modulo.py"] == PRUEBAS
    assert version.defectos_atendidos == validacion.retroalimentacion
    intento = datos_de(cliente.llamadas[1], -1)["intento_rechazado"]
    archivos = {archivo["ruta"]: archivo["contenido"] for archivo in intento["archivos"]}
    assert archivos[RUTA_MODULO] == corregido
    assert "correccion" in datos_de(cliente.llamadas[1], 2)


def test_correccion_que_no_cambia_nada_se_rechaza():
    previa = primera_version()
    sin_cambios = SalidaGeneracion.model_validate(salida({RUTA_MODULO: MODULO}, uso=""))
    validacion = Validacion(retroalimentacion=("Defecto",))
    with pytest.raises(IntentoRechazado, match="no modifica ningún archivo"):
        version_desde_salida(
            sin_cambios, REQUERIMIENTOS, ESPECIFICACION, validacion, previa, ESTILO
        )


def test_rutas_repetidas_se_rechazan():
    repetida = SalidaGeneracion.model_validate(
        {
            "archivos": [
                {"ruta": RUTA_MODULO, "contenido": MODULO},
                {"ruta": RUTA_MODULO, "contenido": MODULO},
            ],
            "documentacion_uso": "# Uso",
        }
    )
    with pytest.raises(ErrorValidacionSalida, match="repetidos"):
        version_desde_salida(repetida, REQUERIMIENTOS, ESPECIFICACION, Validacion(), None, ESTILO)


# Grafo ------------------------------------------------------------------------------------------


def test_n10_en_el_grafo_genera_y_corrige_tras_el_rechazo_final(cliente_falso, completar_respuesta):
    corregido = MODULO.replace("if not dato:", "if not dato.strip():")
    cliente = cliente_falso(
        completar_respuesta(VALIDA, modelo=MODELO),
        completar_respuesta(salida({RUTA_MODULO: corregido}, uso=""), modelo=MODELO),
    )
    simulados = ServiciosSimulados(fallos_veredicto=0)
    servicios = Servicios(
        elicitador=ElicitadorFijo(SINTESIS),
        arquitecto=simulados,
        desarrollador=agente(cliente),
        tester=simulados,
    )
    app = construir_grafo(servicios, ConfiguracionOrquestador(_env_file=None)).compile(
        checkpointer=InMemorySaver(serde=serializador())
    )
    id_sesion, _ = iniciar_sesion(app, "Cliente", "Catastro", "Normalizar datos")
    avanzar(app, id_sesion, aprobar())  # N6
    avance = avanzar(app, id_sesion, aprobar())  # N9 → N10 … N17

    assert avance.pausa.punto == "final"
    assert avance.pausa.datos["version"] == 1
    assert avance.pausa.datos["archivos"] == sorted([RUTA_MODULO, "USO.md", "tests/test_modulo.py"])

    observacion = "Un dato con solo espacios debe rechazarse"
    avance = avanzar(app, id_sesion, rechazar(observacion))  # N17 → N10 … N17
    assert avance.pausa.datos["version"] == 2
    avance = avanzar(app, id_sesion, aprobar())
    assert avance.fase is Fase.VALIDADO

    codigo = app.get_state(configuracion_hilo(id_sesion)).values["codigo"]
    assert [version.numero for version in codigo.versiones] == [1, 2]
    assert codigo.vigente.defectos_atendidos == (observacion,)
    assert codigo.vigente.archivos[RUTA_MODULO] == corregido
