"""Agente elicitador con recuperador y modelo falsos: N2, N3, N5 y el recorrido hasta N6."""

import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from multiagente.agentes.elicitador.calidad import verificar_conjunto
from multiagente.agentes.elicitador.contexto import (
    CONSULTAS_ELICITACION,
    etiquetar,
    mensaje_contexto,
    recuperar_contexto,
)
from multiagente.agentes.elicitador.dialogo import (
    SalidaDialogo,
    mensajes_dialogo,
    registro_desde_salida,
    validar_dialogo,
)
from multiagente.agentes.elicitador.servicio import AgenteElicitador
from multiagente.agentes.elicitador.sintesis import (
    AUTOR,
    SalidaSintesis,
    mensajes_sintesis,
    validar_sintesis,
)
from multiagente.core.configuracion import ConfiguracionOrquestador
from multiagente.llm.costos import Tarifa
from multiagente.llm.invocador import (
    CLAVE_PROBLEMAS,
    ErrorValidacionSalida,
    InvocadorNodo,
    ParametrosNodo,
)
from multiagente.llm.prompts import cargar_prompt
from multiagente.llm.traza import RegistroEnMemoria
from multiagente.orquestador.ejecucion import avanzar, configuracion_hilo, iniciar_sesion
from multiagente.orquestador.estado import (
    Contexto,
    Conversacion,
    Emisor,
    FragmentoContexto,
    RegistroCaptura,
    Requerimientos,
    Turno,
)
from multiagente.orquestador.grafo import Nodo, construir_grafo
from multiagente.orquestador.servicios import Servicios
from multiagente.orquestador.simulacion import ServiciosSimulados
from multiagente.persistencia.puntos_control import serializador
from multiagente.rag.colecciones import Agente, Coleccion
from multiagente.rag.recuperacion import Descarte, FragmentoRecuperado, ResultadoRecuperacion

AHORA = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
TARIFAS = {
    "gpt-5-nano": Tarifa(
        entrada=Decimal("0.05"), entrada_cacheada=Decimal("0.005"), salida=Decimal("0.40")
    )
}
NECESIDAD = "Necesitamos registrar las solicitudes de mutación de propietario de los predios"


# Recuperación ----------------------------------------------------------------------------------


def recuperado(
    identificador: int, coleccion: Coleccion, documento: str, titulo: str, similitud: float = 0.6
) -> FragmentoRecuperado:
    return FragmentoRecuperado(
        id=identificador,
        coleccion=coleccion,
        documento_id=documento,
        version_documento="1.0",
        titulo=titulo,
        contenido=f"Contenido de {titulo}",
        metadatos={},
        similitud=similitud,
        rango_semantico=1,
        rango_lexico=None,
        puntaje=0.016,
    )


class RecuperadorFalso:
    """Cada consulta metodológica trae la guía compartida y una sección propia."""

    def __init__(self, sin_dominio: bool = False) -> None:
        self.consultas: list[tuple[str, Coleccion, int | None]] = []
        self.sin_dominio = sin_dominio

    def recuperar(self, consulta, colecciones=None, k=None) -> ResultadoRecuperacion:
        [coleccion] = colecciones
        self.consultas.append((consulta, coleccion, k))
        descartados: tuple[Descarte, ...] = ()
        if coleccion is Coleccion.ELICITACION:
            numero = len(self.consultas)
            fragmentos = (
                recuperado(1, coleccion, "eli-006", "Guía de preguntas"),
                recuperado(100 + numero, coleccion, f"eli-10{numero}", f"Sección {numero}"),
            )
        elif self.sin_dominio:
            fragmentos = ()
            descartados = (
                Descarte(
                    fragmento=recuperado(201, coleccion, "dom-007", "Reglas", 0.2),
                    motivo="similitud 0.200 menor que el umbral 0.37 y sin coincidencia léxica",
                ),
            )
        else:
            fragmentos = (recuperado(200, coleccion, "dom-002", "Mutaciones catastrales"),)
        return ResultadoRecuperacion(
            agente=Agente.ELICITADOR,
            consulta=consulta,
            colecciones=(coleccion,),
            fragmentos=fragmentos,
            descartados=descartados,
        )


def abierta(necesidad: str = NECESIDAD) -> Conversacion:
    return Conversacion(turnos=(Turno(emisor=Emisor.CLIENTE, texto=necesidad, fecha=AHORA),))


def contexto_recuperado() -> Contexto:
    return recuperar_contexto(RecuperadorFalso(), abierta())


def test_n2_consulta_la_metodologia_y_el_dominio_de_la_necesidad():
    recuperador = RecuperadorFalso()
    contexto = recuperar_contexto(recuperador, abierta())

    metodologicas = [c for c in recuperador.consultas if c[1] is Coleccion.ELICITACION]
    assert [c[0] for c in metodologicas] == list(CONSULTAS_ELICITACION)
    assert {c[2] for c in metodologicas} == {3}
    assert recuperador.consultas[-1] == (NECESIDAD, Coleccion.DOMINIO_NEGOCIO, None)

    elicitacion = contexto.fragmentos["elicitacion"]
    # La guía compartida aparece una sola vez.
    assert [f.documento_id for f in elicitacion].count("eli-006") == 1
    assert len(elicitacion) == 1 + len(CONSULTAS_ELICITACION)
    assert [f.referencia for f in contexto.fragmentos["dominio_negocio"]] == [
        "dom-002 v1.0 · Mutaciones catastrales"
    ]
    assert contexto.descartados == ()


def test_n2_declara_la_ausencia_de_contexto_de_dominio():
    contexto = recuperar_contexto(RecuperadorFalso(sin_dominio=True), abierta())
    assert contexto.fragmentos["dominio_negocio"] == ()
    assert contexto.descartados == (
        f"dominio_negocio: sin contexto relevante para «{NECESIDAD}»",
        "dominio_negocio: dom-007 · Reglas (similitud 0.200 menor que el umbral 0.37 y sin "
        "coincidencia léxica)",
    )


def test_n2_exige_la_necesidad_inicial():
    with pytest.raises(ValueError, match="necesidad"):
        recuperar_contexto(RecuperadorFalso(), Conversacion())


def test_etiquetas_estables_solo_de_las_colecciones_del_elicitador():
    contexto = contexto_recuperado()
    ajeno = FragmentoContexto(
        documento_id="ARQ-01", version_documento="1.0", titulo="Capas", contenido="x", similitud=1
    )
    con_ajeno = contexto.combinar(Contexto(fragmentos={"arquitecturas_referencia": (ajeno,)}))
    etiquetas = etiquetar(con_ajeno)
    assert list(etiquetas) == [f"F{n}" for n in range(1, 8)]
    assert etiquetas["F1"].documento_id == "eli-006"
    assert etiquetas["F7"].documento_id == "dom-002"
    contenido = json.loads(mensaje_contexto(con_ajeno)["content"])
    assert contenido["contexto"][6] == {
        "etiqueta": "F7",
        "fuente": "dom-002 v1.0 · Mutaciones catastrales",
        "contenido": "Contenido de Mutaciones catastrales",
    }


# Diálogo ---------------------------------------------------------------------------------------

DATOS_ENTRADA = [
    {"nombre": "numero_predial", "tipo": "texto", "obligatorio": True, "restriccion": "30 dígitos"},
    {
        "nombre": "fecha_documento",
        "tipo": "fecha",
        "obligatorio": True,
        "restriccion": "no posterior a la fecha de radicación",
    },
]
DATOS_SALIDA = [{"nombre": "radicado", "tipo": "texto", "formato": "RAD-AAAA-NNNNNN"}]
COMPLETO = {
    "rol": "analista de conservación catastral",
    "funcionalidad": "registrar solicitudes de mutación de propietario con su documento soporte",
    "beneficio": "tramitar el cambio en la información del predio y hacerle seguimiento",
    "reglas_negocio": [
        "La solicitud se acepta solo si el número predial existe y el documento soporte no tiene "
        "fecha posterior a la radicación"
    ],
    "datos_entrada": DATOS_ENTRADA,
    "datos_salida": DATOS_SALIDA,
    "excepciones": ["Si el número predial no existe, la solicitud se rechaza"],
}
RESUMEN = "Le resumo lo que entendí: … ¿Es correcto?"


def salida_dialogo(**cambios) -> SalidaDialogo:
    base = {
        "rol": None,
        "funcionalidad": None,
        "beneficio": None,
        "reglas_negocio": [],
        "datos_entrada": [],
        "datos_salida": [],
        "excepciones": [],
        "supuestos": [],
        "preguntas_abiertas": [],
        "confirma_resumen": False,
        "siguiente_pregunta": None,
    }
    return SalidaDialogo.model_validate(base | cambios)


def registro_completo() -> RegistroCaptura:
    return registro_desde_salida(salida_dialogo(**COMPLETO), RegistroCaptura())


def esperando_confirmacion(respuesta: str | None = "Sí, es correcto") -> Conversacion:
    """Conversación con el registro completo, el resumen presentado y quizá una respuesta."""
    turnos = [
        Turno(emisor=Emisor.CLIENTE, texto=NECESIDAD, fecha=AHORA),
        Turno(emisor=Emisor.ELICITADOR, texto=RESUMEN, fecha=AHORA),
    ]
    conversacion = Conversacion(
        turnos=tuple(turnos), turnos_procesados=2, registro=registro_completo()
    )
    if respuesta is None:
        return conversacion
    turno = Turno(emisor=Emisor.CLIENTE, texto=respuesta, fecha=AHORA)
    return conversacion.model_copy(update={"turnos": (*turnos, turno)})


def test_mensajes_del_dialogo():
    conversacion = abierta()
    [contexto, estado] = mensajes_dialogo(conversacion, contexto_recuperado())
    assert json.loads(contexto["content"])["contexto"][0]["etiqueta"] == "F1"
    datos = json.loads(estado["content"])
    assert datos["pendientes"][0] == "rol"
    assert datos["respuesta_nueva"] == NECESIDAD
    assert datos["transcripcion"] == [{"emisor": "cliente", "texto": NECESIDAD}]
    assert datos["observaciones_revisor"] == []


def test_extrae_y_pregunta_por_lo_que_falta():
    dialogo = validar_dialogo(
        salida_dialogo(
            funcionalidad="registrar solicitudes de mutación",
            siguiente_pregunta="¿Qué cargo tiene la persona que registra las solicitudes?",
        ),
        abierta(),
    )
    assert dialogo.registro.funcionalidad == "registrar solicitudes de mutación"
    assert dialogo.registro.pendientes[0] == "rol"
    assert dialogo.siguiente_pregunta.startswith("¿Qué cargo")


def test_lo_capturado_no_se_pierde_por_omision():
    previo = registro_completo()
    conversacion = esperando_confirmacion("Además, el radicado incluye el año")
    conversacion = conversacion.model_copy(update={"registro": previo})
    dialogo = validar_dialogo(
        salida_dialogo(
            reglas_negocio=[*COMPLETO["reglas_negocio"], "El radicado incluye el año"],
            siguiente_pregunta=RESUMEN,
        ),
        conversacion,
    )
    assert dialogo.registro.rol == previo.rol
    assert dialogo.registro.datos_entrada == previo.datos_entrada
    assert len(dialogo.registro.reglas_negocio) == 2


def test_confirmacion_valida_cierra_sin_pregunta():
    # Diferencias de mayúsculas y espacios no cuentan como cambio del registro.
    cambios = COMPLETO | {"rol": "Analista de conservación  catastral"}
    dialogo = validar_dialogo(
        salida_dialogo(**cambios, confirma_resumen=True, siguiente_pregunta="¿Algo más?"),
        esperando_confirmacion(),
    )
    assert dialogo.registro.resumen_confirmado
    assert dialogo.registro.pendientes == []
    assert dialogo.siguiente_pregunta is None


def test_confirmacion_de_un_registro_cambiado_no_cuenta():
    cambios = COMPLETO | {"beneficio": "hacer seguimiento al trámite"}
    dialogo = validar_dialogo(
        salida_dialogo(**cambios, confirma_resumen=True, siguiente_pregunta=RESUMEN),
        esperando_confirmacion("Sí, pero el beneficio es hacer seguimiento al trámite"),
    )
    assert not dialogo.registro.resumen_confirmado
    assert dialogo.siguiente_pregunta == RESUMEN

    with pytest.raises(ErrorValidacionSalida, match="pide de nuevo la confirmación"):
        validar_dialogo(
            salida_dialogo(**cambios, confirma_resumen=True),
            esperando_confirmacion("Sí, pero el beneficio es hacer seguimiento al trámite"),
        )


def test_confirmacion_exige_respuesta_nueva():
    with pytest.raises(ErrorValidacionSalida, match="respuesta nueva"):
        validar_dialogo(
            salida_dialogo(**COMPLETO, confirma_resumen=True), esperando_confirmacion(None)
        )


@pytest.mark.parametrize(
    ("pregunta", "mensaje"),
    [
        (None, "no formulaste la siguiente pregunta"),
        ("¿Quién lo usa? ¿Para qué?", "una sola"),
        ("¿Qué campos de la API necesita?", "términos técnicos"),
    ],
)
def test_reglas_de_la_pregunta(pregunta, mensaje):
    with pytest.raises(ErrorValidacionSalida, match=mensaje):
        validar_dialogo(salida_dialogo(siguiente_pregunta=pregunta), abierta())


# Síntesis --------------------------------------------------------------------------------------


def requerimiento_modelo(**cambios) -> dict:
    base = {
        "tipo_solicitud": "nuevo",
        "impacto": "alto",
        "modulo": "conservacion",
        "riesgo": None,
        "area_funcional": "Conservación catastral",
        "funcional_responsable": None,
        "precondicion": "El predio existe en la base catastral con ficha vigente",
        "regla_negocio": (
            "La solicitud se acepta únicamente si el número predial existe y el documento "
            "soporte tiene fecha no posterior a la fecha de radicación. Al aceptarse se genera "
            "un radicado único con estado inicial «en trámite»."
        ),
        "datos_entrada": DATOS_ENTRADA,
        "datos_salida": DATOS_SALIDA,
        "escenarios": [
            {
                "nombre": "Solicitud válida",
                "dado_que": "un predio registrado y un documento soporte del 2026-09-30",
                "cuando": "se registra la solicitud el 2026-10-01",
                "entonces": "el sistema genera un radicado único con estado «en trámite»",
            },
            {
                "nombre": "Documento del mismo día",
                "dado_que": "un documento soporte con fecha igual a la de radicación",
                "cuando": "se registra la solicitud",
                "entonces": "el sistema genera el radicado de la solicitud",
            },
            {
                "nombre": "Predio inexistente",
                "dado_que": "un número predial que no corresponde a ningún predio registrado",
                "cuando": "se registra la solicitud",
                "entonces": "el sistema rechaza la solicitud e informa que el predio no existe",
            },
        ],
        "relacionados": [],
        "fuentes": ["F7", "F1"],
    }
    return base | cambios


def salida_sintesis(*requerimientos: dict) -> SalidaSintesis:
    return SalidaSintesis.model_validate(
        {
            "historia": {
                "enunciado": {
                    "como": COMPLETO["rol"],
                    "quiero": COMPLETO["funcionalidad"],
                    "para": COMPLETO["beneficio"],
                },
                "epica": "Conservación catastral",
                "prioridad": "alta",
                "supuestos": ["Prioridad alta, propuesta sin indicación del cliente"],
                "preguntas_abiertas": [],
            },
            "requerimientos": list(requerimientos) or [requerimiento_modelo()],
        }
    )


def test_sintesis_asigna_los_campos_deterministas():
    previos = Requerimientos(sintesis=1)
    sintesis = validar_sintesis(
        salida_sintesis(requerimiento_modelo(relacionados=[2]), requerimiento_modelo()),
        contexto_recuperado(),
        previos,
        "Gestión catastral",
    )
    [historia] = sintesis.historias
    rf1, rf2 = sintesis.requerimientos
    assert historia.id == "HU-01"
    assert (rf1.id_requerimiento, rf2.id_requerimiento) == ("RF-01", "RF-02")
    assert (rf1.version, rf1.proyecto, rf1.autor) == ("0.2", "Gestión catastral", AUTOR)
    assert rf1.titulo == historia.enunciado
    assert rf1.prioridad == historia.prioridad
    assert [e.id for e in rf1.criterios_aceptacion] == ["ESC-01", "ESC-02", "ESC-03"]
    assert rf1.requerimientos_relacionados == ["RF-02"]
    assert sintesis.referencias["RF-01"] == (
        "dom-002 v1.0 · Mutaciones catastrales",
        "eli-006 v1.0 · Guía de preguntas",
    )


def test_sintesis_limpia_pasa_la_verificacion_de_calidad():
    sintesis = validar_sintesis(
        salida_sintesis(), contexto_recuperado(), Requerimientos(), "Gestión catastral"
    )
    requerimientos = Requerimientos(
        historias=sintesis.historias,
        requerimientos=sintesis.requerimientos,
        referencias=sintesis.referencias,
    )
    assert verificar_conjunto(requerimientos) == []


@pytest.mark.parametrize(
    ("cambios", "mensaje"),
    [
        ({"fuentes": []}, "cita al menos un fragmento"),
        ({"fuentes": ["F99"]}, "no existen"),
        ({"relacionados": [1]}, "no son posiciones"),
        ({"regla_negocio": "  "}, "regla_negocio"),
        ({"escenarios": []}, "criterios_aceptacion"),
    ],
)
def test_sintesis_invalida(cambios, mensaje):
    with pytest.raises(ErrorValidacionSalida, match=mensaje):
        validar_sintesis(
            salida_sintesis(requerimiento_modelo(**cambios)),
            contexto_recuperado(),
            Requerimientos(),
            "Gestión catastral",
        )


def test_mensajes_de_correccion_incluyen_los_defectos():
    contexto = contexto_recuperado()
    sintesis = validar_sintesis(salida_sintesis(), contexto, Requerimientos(), "Catastro")
    previos = Requerimientos(
        historias=sintesis.historias,
        requerimientos=sintesis.requerimientos,
        defectos=("RF-01 · C3 No ambiguo · descripcion.regla_negocio: cuantificador vago",),
    )
    conversacion = esperando_confirmacion()
    sin_defectos = json.loads(
        mensajes_sintesis(conversacion, contexto, Requerimientos(), "Catastro")[1]["content"]
    )
    assert "correccion" not in sin_defectos
    datos = json.loads(mensajes_sintesis(conversacion, contexto, previos, "Catastro")[1]["content"])
    assert datos["proyecto"] == "Catastro"
    assert datos["correccion"]["defectos"] == list(previos.defectos)
    assert datos["correccion"]["artefactos_previos"]["requerimientos"][0]["id_requerimiento"] == (
        "RF-01"
    )


# Agente con el modelo falso --------------------------------------------------------------------


def agente(cliente, registro: RegistroEnMemoria, recuperador=None) -> AgenteElicitador:
    def invocador(nodo: str, nombre: str) -> InvocadorNodo:
        parametros = ParametrosNodo(
            nodo=nodo, despliegue="gpt-5-nano", esfuerzo="low", max_tokens_salida=4000
        )
        return InvocadorNodo(
            cliente, parametros, cargar_prompt("elicitador", nombre), registro, TARIFAS
        )

    return AgenteElicitador(
        recuperador or RecuperadorFalso(), invocador("N3", "dialogo"), invocador("N5", "sintesis")
    )


def test_los_prompts_del_elicitador_estan_versionados():
    for nombre, nodo in (("dialogo", "N3"), ("sintesis", "N5")):
        prompt = cargar_prompt("elicitador", nombre)
        assert prompt.metadatos.nodo == nodo
        assert prompt.identificador == f"elicitador.{nombre}@1.0"
        assert CLAVE_PROBLEMAS in prompt.texto


def test_reintento_con_los_problemas_del_intento_anterior(cliente_falso, completar_respuesta):
    cliente = cliente_falso(
        completar_respuesta(salida_dialogo(siguiente_pregunta="¿Quién? ¿Cuándo?")),
        completar_respuesta(salida_dialogo(siguiente_pregunta="¿Quién lo usa?")),
    )
    registro = RegistroEnMemoria()
    dialogo = agente(cliente, registro).dialogar(abierta(), contexto_recuperado())
    assert dialogo.siguiente_pregunta == "¿Quién lo usa?"
    reintento = cliente.llamadas[1]["messages"]
    assert reintento[:-1] == cliente.llamadas[0]["messages"]
    assert CLAVE_PROBLEMAS in json.loads(reintento[-1]["content"])
    assert [llamada.prompt for llamada in registro.llamadas] == ["elicitador.dialogo@1.0"] * 2


def test_reintento_agotado_propaga_el_error(cliente_falso, completar_respuesta):
    invalida = completar_respuesta(salida_dialogo(siguiente_pregunta="¿Quién? ¿Cuándo?"))
    registro = RegistroEnMemoria()
    with pytest.raises(ErrorValidacionSalida, match="una sola"):
        agente(cliente_falso(invalida, invalida), registro).dialogar(
            abierta(), contexto_recuperado()
        )
    assert len(registro.llamadas) == 2


def test_una_conversacion_produce_un_requerimiento_que_pasa_la_calidad(
    cliente_falso, completar_respuesta
):
    parcial = {k: COMPLETO[k] for k in ("rol", "funcionalidad", "beneficio", "reglas_negocio")}
    cliente = cliente_falso(
        completar_respuesta(
            salida_dialogo(
                funcionalidad=COMPLETO["funcionalidad"],
                siguiente_pregunta="¿Qué cargo tiene la persona que procesa estas solicitudes?",
            )
        ),
        completar_respuesta(
            salida_dialogo(
                **parcial,
                siguiente_pregunta="¿Qué información necesita tener a la mano para registrarla?",
            )
        ),
        completar_respuesta(salida_dialogo(**COMPLETO, siguiente_pregunta=RESUMEN)),
        completar_respuesta(salida_dialogo(**COMPLETO, confirma_resumen=True)),
        completar_respuesta(salida_sintesis()),
    )
    registro = RegistroEnMemoria()
    simulados = ServiciosSimulados()
    servicios = Servicios(
        elicitador=agente(cliente, registro),
        arquitecto=simulados,
        desarrollador=simulados,
        tester=simulados,
    )
    configuracion = ConfiguracionOrquestador(_env_file=None)
    app = construir_grafo(servicios, configuracion).compile(
        checkpointer=InMemorySaver(serde=serializador())
    )

    id_sesion, avance = iniciar_sesion(app, "Realtix", "Gestión catastral", NECESIDAD)
    for respuesta in (
        "El analista de conservación catastral, para tramitar el cambio y hacerle seguimiento",
        "El número predial y la fecha del documento; entrega un radicado",
        "Sí, es correcto",
    ):
        assert avance.pausa.punto == "dialogo"
        avance = avanzar(app, id_sesion, respuesta)

    assert avance.pausa.punto == "requerimientos"
    assert avance.pausa.datos["defectos"] == []
    assert avance.pausa.datos["referencias"]["RF-01"]
    estado = app.get_state(configuracion_hilo(id_sesion)).values
    [requerimiento] = estado["requerimientos"].requerimientos
    assert requerimiento.proyecto == "Gestión catastral"
    assert estado["conversacion"].registro.resumen_confirmado
    assert [llamada.nodo for llamada in registro.llamadas] == ["N3"] * 4 + ["N5"]
    # El prompt y el contexto forman un prefijo idéntico en cada turno, apto para la caché.
    assert cliente.llamadas[0]["messages"][:2] == cliente.llamadas[3]["messages"][:2]
    assert avance.nodos == (Nodo.N3, Nodo.N4, Nodo.N5)
