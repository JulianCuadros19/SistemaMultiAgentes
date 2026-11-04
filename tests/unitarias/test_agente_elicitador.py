"""Agente elicitador con recuperador y modelo falsos: N2, N3, N5 y el recorrido hasta N6."""

import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import ValidationError

from multiagente.agentes.elicitador.calidad import verificar_conjunto
from multiagente.agentes.elicitador.contexto import (
    CONSULTA_PATRONES_DE_REGLAS,
    CONSULTAS_ELICITACION,
    FRAGMENTOS_PATRONES_DE_REGLAS,
    etiquetar,
    mensaje_contexto,
    recuperar_contexto,
)
from multiagente.agentes.elicitador.dialogo import (
    PREGUNTA_ALGO_MAS,
    PREGUNTA_CIERRE,
    SIN_RESPUESTA,
    SalidaExtraccion,
    SalidaPregunta,
    aplicar_extraccion,
    dichos_del_cliente,
    mensajes_extraccion,
    mensajes_pregunta,
    obligatoriedad_dicha,
    registro_desde_salida,
    resumen_para_confirmar,
    validar_caso_limite,
    validar_pregunta,
)
from multiagente.agentes.elicitador.fidelidad import (
    dice_no_saber,
    raices,
    raices_del_cliente,
    respaldado,
)
from multiagente.agentes.elicitador.servicio import AgenteElicitador
from multiagente.agentes.elicitador.sintesis import (
    AUTOR,
    POR_CONFIRMAR,
    SalidaSintesis,
    mensajes_sintesis,
    validar_sintesis,
)
from multiagente.core.configuracion import ConfiguracionOrquestador
from multiagente.core.esquemas.comunes import Prioridad
from multiagente.core.esquemas.requerimiento import DatoEntrada, DatoSalida
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
    INTENTOS_SIN_RESPUESTA,
    Contexto,
    Conversacion,
    Emisor,
    FragmentoContexto,
    RegistroCaptura,
    Requerimientos,
    Turno,
)
from multiagente.orquestador.grafo import Nodo, construir_grafo
from multiagente.orquestador.servicios import Servicios, VerificacionCalidad
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
    assert recuperador.consultas[-2:] == [
        (NECESIDAD, Coleccion.DOMINIO_NEGOCIO, None),
        (CONSULTA_PATRONES_DE_REGLAS, Coleccion.DOMINIO_NEGOCIO, FRAGMENTOS_PATRONES_DE_REGLAS),
    ]

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
    descarte = (
        "dominio_negocio: dom-007 · Reglas (similitud 0.200 menor que el umbral 0.37 y sin "
        "coincidencia léxica)"
    )
    assert contexto.descartados == (
        f"dominio_negocio: sin contexto relevante para «{NECESIDAD}»",
        descarte,
        f"dominio_negocio: sin contexto relevante para «{CONSULTA_PATRONES_DE_REGLAS}»",
        descarte,
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
DICHO_POR_EL_CLIENTE = (
    "El analista de conservación catastral registra solicitudes de mutación de propietario con "
    "su documento soporte, para tramitar el cambio en la información del predio y hacerle "
    "seguimiento. La solicitud se acepta solo si el número predial existe y el documento "
    "soporte no tiene fecha posterior a la radicación; el predio existe en la base catastral con "
    "ficha vigente. Se necesita el número predial de 30 dígitos y la fecha del documento; se "
    "entrega un radicado único RAD-AAAA-NNNNNN con estado inicial en trámite. Si el número "
    "predial no existe, la solicitud se rechaza."
)
REGLA_DEL_DOMINIO = (
    "Una mutación de cuarta clase por englobe exige que todos los predios a englobar pertenezcan "
    "al mismo propietario y sean colindantes"
)


CASO_LIMITE = "Si el documento soporte tiene más de un año, la solicitud igual se acepta"


def salida_pregunta(
    texto: str, categoria: str | None = None, sin_mas: bool = False
) -> SalidaPregunta:
    return SalidaPregunta(
        siguiente_pregunta=texto, categoria_caso_limite=categoria, sin_mas_casos_limite=sin_mas
    )


def salida_extraccion(**cambios) -> SalidaExtraccion:
    base = {
        "rol": None,
        "usuarios": None,
        "funcionalidad": None,
        "beneficio": None,
        "reglas_negocio": None,
        "datos_entrada": None,
        "datos_salida": None,
        "excepciones": None,
        "condiciones": None,
        "casos_limite": None,
        "ejemplos": None,
        "prioridad": None,
        "retirar": [],
        "supuestos": [],
        "preguntas_abiertas": [],
        "confirma_resumen": False,
    }
    return SalidaExtraccion.model_validate(base | cambios)


def registro_completo(casos_limite_cerrados: bool = True) -> RegistroCaptura:
    """Registro con todos los atributos; por defecto, listo para confirmar el resumen.

    Con la fase de casos límite cerrada, también se dio por hecha la pregunta por algo más.
    """
    registro = registro_desde_salida(
        salida_extraccion(**COMPLETO), RegistroCaptura(), raices(DICHO_POR_EL_CLIENTE)
    )
    return registro.model_copy(
        update={
            "casos_limite_cerrados": casos_limite_cerrados,
            "algo_mas_preguntado": casos_limite_cerrados,
        }
    )


def conversacion_completa() -> Conversacion:
    turnos = (
        Turno(emisor=Emisor.CLIENTE, texto=NECESIDAD, fecha=AHORA),
        Turno(emisor=Emisor.ELICITADOR, texto="¿Cómo funciona hoy?", fecha=AHORA),
        Turno(emisor=Emisor.CLIENTE, texto=DICHO_POR_EL_CLIENTE, fecha=AHORA),
    )
    return Conversacion(turnos=turnos, turnos_procesados=3, registro=registro_completo())


def con_respuesta(registro: RegistroCaptura, pregunta: str, respuesta: str | None) -> Conversacion:
    """Conversación con un registro, la última pregunta del elicitador y quizá una respuesta."""
    turnos = (
        Turno(emisor=Emisor.CLIENTE, texto=NECESIDAD, fecha=AHORA),
        Turno(emisor=Emisor.ELICITADOR, texto=pregunta, fecha=AHORA),
    )
    conversacion = Conversacion(turnos=turnos, turnos_procesados=2, registro=registro)
    if respuesta is None:
        return conversacion
    turno = Turno(emisor=Emisor.CLIENTE, texto=respuesta, fecha=AHORA)
    return conversacion.model_copy(update={"turnos": (*turnos, turno)})


def esperando_confirmacion(respuesta: str | None = "Sí, es correcto") -> Conversacion:
    resumen = f"{resumen_para_confirmar(registro_completo())}\n{PREGUNTA_CIERRE}"
    return con_respuesta(registro_completo(), resumen, respuesta)


def test_la_extraccion_no_ve_el_contexto_de_dominio():
    conversacion = con_respuesta(RegistroCaptura(), "¿Quién lo usa?", "El analista catastral")
    [mensaje] = mensajes_extraccion(conversacion)
    datos = json.loads(mensaje["content"])
    assert set(datos) == {
        "registro",
        "transcripcion",
        "pregunta_anterior",
        "caso_limite_preguntado",
        "respuesta_nueva",
    }
    assert datos["pregunta_anterior"] == "¿Quién lo usa?"
    assert datos["respuesta_nueva"] == "El analista catastral"


def test_la_pregunta_ve_el_contexto_y_el_registro_actualizado():
    registro = registro_completo()
    [contexto, estado] = mensajes_pregunta(abierta(), registro, contexto_recuperado())
    assert json.loads(contexto["content"])["contexto"][0]["etiqueta"] == "F1"
    datos = json.loads(estado["content"])
    assert datos["pendientes"] == ["confirmacion"]
    assert datos["resumen_incompleto"] is False
    assert datos["registro"]["rol"] == registro.rol
    assert datos["observaciones_revisor"] == []


def test_extrae_lo_que_aporta_la_necesidad():
    registro = aplicar_extraccion(
        salida_extraccion(funcionalidad="registrar solicitudes de mutación"), abierta()
    )
    assert registro.funcionalidad == "registrar solicitudes de mutación"
    assert registro.pendientes[0] == "rol"


def test_solo_cambia_lo_que_aporta_la_respuesta():
    previo = registro_completo()
    conversacion = esperando_confirmacion("El beneficio es hacer seguimiento al trámite")
    registro = aplicar_extraccion(
        salida_extraccion(beneficio="hacer seguimiento al trámite"), conversacion
    )
    assert registro.beneficio == "hacer seguimiento al trámite"
    assert registro.model_dump(exclude={"beneficio"}) == previo.model_dump(exclude={"beneficio"})


def test_lo_capturado_no_se_pierde_por_omision():
    previo = registro_completo()
    registro = aplicar_extraccion(
        salida_extraccion(
            reglas_negocio=[*COMPLETO["reglas_negocio"], "El radicado incluye el año"]
        ),
        esperando_confirmacion("Además, el radicado incluye el año"),
    )
    assert registro.rol == previo.rol
    assert registro.datos_entrada == previo.datos_entrada
    assert len(registro.reglas_negocio) == 2


# Caso 18 de la corrida ampliada: el registro tomó como resultados los datos que trae el aviso,
# los mismos que ya estaban como entradas.
AVISO = (("número de la venta", "texto"), ("fecha y hora", "fecha"), ("lista de ítems", "lista"))
RECHAZO_DE_RESULTADOS = (
    "No, falta algo. No me cuadra que ponga como resultados el número, la fecha y los ítems; eso "
    "es lo que trae el aviso, no lo que entrega el proceso."
)
RETIRO_DE_RESULTADOS = [{"lista": "datos_salida", "entrada": nombre} for nombre, _ in AVISO]


def registro_de_la_caja() -> RegistroCaptura:
    return registro_completo().model_copy(
        update={
            "datos_entrada": tuple(
                DatoEntrada(nombre=nombre, tipo=tipo, obligatorio=True) for nombre, tipo in AVISO
            ),
            "datos_salida": tuple(DatoSalida(nombre=nombre, tipo=tipo) for nombre, tipo in AVISO),
        }
    )


def respuesta_al_resumen(registro: RegistroCaptura, respuesta: str) -> Conversacion:
    return con_respuesta(
        registro, f"{resumen_para_confirmar(registro)}\n{PREGUNTA_CIERRE}", respuesta
    )


def test_retira_lo_que_el_cliente_rechaza_sin_reemplazo():
    previo = registro_de_la_caja()
    registro = aplicar_extraccion(
        salida_extraccion(retirar=RETIRO_DE_RESULTADOS),
        respuesta_al_resumen(previo, RECHAZO_DE_RESULTADOS),
    )
    assert registro.datos_salida == ()
    # Los mismos nombres siguen como entradas: el retiro es de la lista indicada.
    assert registro.datos_entrada == previo.datos_entrada
    assert registro.pendientes == ["datos_salida", "confirmacion"]


@pytest.mark.parametrize(
    ("retiro", "respuesta"),
    [
        # La respuesta no habla de esa entrada.
        (RETIRO_DE_RESULTADOS[0], "Las alertas salen una sola vez por día"),
        # La respuesta la menciona, pero no está en el registro, o no en esa lista.
        (
            {"lista": "datos_salida", "entrada": "código de producto"},
            "El código de producto no es un resultado",
        ),
        ({"lista": "reglas_negocio", "entrada": "número de la venta"}, RECHAZO_DE_RESULTADOS),
    ],
)
def test_no_retira_lo_que_la_respuesta_no_menciona_ni_lo_que_no_esta(retiro, respuesta):
    previo = registro_de_la_caja()
    registro = aplicar_extraccion(
        salida_extraccion(retirar=[retiro]), respuesta_al_resumen(previo, respuesta)
    )
    assert registro == previo


def test_la_respuesta_que_confirma_no_retira_nada():
    previo = registro_de_la_caja()
    registro = aplicar_extraccion(
        salida_extraccion(retirar=RETIRO_DE_RESULTADOS, confirma_resumen=True),
        respuesta_al_resumen(previo, "Sí, es correcto, con el número de la venta y la fecha"),
    )
    assert registro.datos_salida == previo.datos_salida
    assert registro.resumen_confirmado


def test_retira_un_nombre_corto_si_la_respuesta_lo_dice():
    previo = registro_completo()
    previo = previo.model_copy(
        update={"datos_salida": (*previo.datos_salida, DatoSalida(nombre="NIT", tipo="texto"))}
    )
    registro = aplicar_extraccion(
        salida_extraccion(retirar=[{"lista": "datos_salida", "entrada": "NIT"}]),
        respuesta_al_resumen(previo, "El NIT no se entrega como resultado"),
    )
    assert [dato.nombre for dato in registro.datos_salida] == ["radicado"]


# Lo que el cliente no sabe se pregunta dos veces, no sin fin (RF-02).
NO_SE = "No lo sé; nadie me ha dicho qué debe entregar."
CONDICION = "Para las pruebas, la consulta puede funcionar en memoria"


def sin_salidas(no_sabe: int = 0) -> RegistroCaptura:
    return registro_completo().model_copy(
        update={"datos_salida": (), "no_sabe": ("datos_salida",) * no_sabe}
    )


def test_dos_no_se_dejan_el_atributo_sin_respuesta():
    pregunta_salidas = "¿Qué debe entregar el registro de la solicitud?"
    primera = aplicar_extraccion(
        salida_extraccion(), con_respuesta(sin_salidas(), pregunta_salidas, NO_SE)
    )
    assert primera.no_sabe == ("datos_salida",)
    assert primera.por_preguntar == ["datos_salida", "confirmacion"]
    segunda = aplicar_extraccion(
        salida_extraccion(), con_respuesta(primera, pregunta_salidas, "No lo sé, de verdad.")
    )
    assert segunda.sin_respuesta == ["datos_salida"]
    assert segunda.por_preguntar == ["confirmacion"]


@pytest.mark.parametrize(
    ("previo", "salida", "respuesta"),
    [
        # Dice no saber un detalle, pero el atributo que se preguntaba se completa.
        (
            sin_salidas(),
            salida_extraccion(datos_salida=DATOS_SALIDA),
            "No sé el formato, pero se entrega el radicado",
        ),
        # En la respuesta al resumen no hay atributo preguntado que anotar.
        (registro_completo(), salida_extraccion(), "No lo sé, pero el resumen está bien"),
    ],
)
def test_no_anota_si_el_atributo_se_completa_ni_en_el_resumen(previo, salida, respuesta):
    registro = aplicar_extraccion(salida, respuesta_al_resumen(previo, respuesta))
    assert registro.no_sabe == ()


def test_el_resumen_muestra_lo_que_no_supo_la_prioridad_y_las_condiciones():
    registro = sin_salidas(INTENTOS_SIN_RESPUESTA).model_copy(
        update={"prioridad": Prioridad.ALTA, "condiciones": (CONDICION,)}
    )
    resumen = resumen_para_confirmar(registro)
    assert f"- Resultados que se entregan: {SIN_RESPUESTA}" in resumen
    assert f"- Condiciones ya definidas: {CONDICION}" in resumen
    assert "- Prioridad: alta" in resumen


@pytest.mark.parametrize(
    ("respuesta", "esperada"),
    [("Es de prioridad alta, porque hay plazos", Prioridad.ALTA), (NECESIDAD, None)],
)
def test_la_prioridad_solo_entra_si_el_cliente_la_dice(respuesta, esperada):
    registro = aplicar_extraccion(
        salida_extraccion(prioridad="alta"),
        con_respuesta(registro_completo(), "¿Algo más?", respuesta),
    )
    assert registro.prioridad == esperada


def test_la_prioridad_dicha_se_conserva():
    previo = registro_completo().model_copy(update={"prioridad": Prioridad.MEDIA})
    registro = aplicar_extraccion(
        salida_extraccion(), con_respuesta(previo, "¿Algo más?", "El radicado incluye el año")
    )
    assert registro.prioridad is Prioridad.MEDIA


def test_las_condiciones_del_cliente_se_registran_y_se_retiran():
    registro = aplicar_extraccion(
        salida_extraccion(condiciones=[CONDICION]),
        con_respuesta(registro_completo(), "¿Algo más?", f"{CONDICION}; eso ya está definido"),
    )
    assert registro.condiciones == (CONDICION,)
    assert registro.supuestos == ()
    sin_condicion = aplicar_extraccion(
        salida_extraccion(retirar=[{"lista": "condiciones", "entrada": CONDICION}]),
        con_respuesta(registro, "¿Algo más?", "Lo de las pruebas en memoria ya no aplica"),
    )
    assert sin_condicion.condiciones == ()


def test_confirmacion_valida():
    # Mayúsculas, espacios y paráfrasis del modelo no cuentan como cambio del registro.
    parafrasis = COMPLETO | {
        "rol": "Analista de conservación  catastral",
        "beneficio": "tramitar cambios en la información del predio y seguirlos",
        "reglas_negocio": ["Solo se acepta la solicitud si existe el número predial"],
    }
    registro = aplicar_extraccion(
        salida_extraccion(**parafrasis, confirma_resumen=True), esperando_confirmacion()
    )
    assert registro.resumen_confirmado
    assert registro.pendientes == []
    assert registro.beneficio == COMPLETO["beneficio"]
    assert registro.reglas_negocio == tuple(COMPLETO["reglas_negocio"])


def test_confirmacion_de_un_registro_cambiado_no_cuenta():
    registro = aplicar_extraccion(
        salida_extraccion(beneficio="hacer seguimiento al trámite", confirma_resumen=True),
        esperando_confirmacion("Sí, pero el beneficio es hacer seguimiento al trámite"),
    )
    assert not registro.resumen_confirmado
    assert registro.beneficio == "hacer seguimiento al trámite"


def test_confirmacion_que_agrega_una_regla_no_cuenta():
    nueva = "El radicado incluye el año de radicación"
    registro = aplicar_extraccion(
        salida_extraccion(
            reglas_negocio=[*COMPLETO["reglas_negocio"], nueva], confirma_resumen=True
        ),
        esperando_confirmacion(f"Sí, y además {nueva.lower()}"),
    )
    assert not registro.resumen_confirmado
    assert registro.reglas_negocio == (*COMPLETO["reglas_negocio"], nueva)


def test_confirmacion_que_precisa_un_dato_no_cuenta():
    formato = "RAD-año-consecutivo, con el año de radicación en cuatro dígitos"
    radicado = DATOS_SALIDA[0] | {"formato": formato}
    registro = aplicar_extraccion(
        salida_extraccion(datos_salida=[radicado], confirma_resumen=True),
        esperando_confirmacion(f"Sí, es correcto; el radicado es {formato}"),
    )
    assert not registro.resumen_confirmado
    assert registro.datos_salida[0].formato == formato


def test_confirmacion_ignora_la_parafrasis_de_un_dato():
    radicado = DATOS_SALIDA[0] | {"formato": "formato de radicado con año y número"}
    registro = aplicar_extraccion(
        salida_extraccion(datos_salida=[radicado], confirma_resumen=True), esperando_confirmacion()
    )
    assert registro.resumen_confirmado
    assert registro.datos_salida[0].formato == DATOS_SALIDA[0]["formato"]


def test_confirmacion_exige_respuesta_nueva():
    registro = aplicar_extraccion(
        salida_extraccion(confirma_resumen=True), esperando_confirmacion(None)
    )
    assert not registro.resumen_confirmado


def test_lo_que_no_dijo_el_cliente_no_entra_al_registro():
    conversacion = con_respuesta(
        RegistroCaptura(),
        "¿Qué reglas aplican?",
        "Solo se acepta si el número predial existe en la base catastral",
    )
    registro = aplicar_extraccion(
        salida_extraccion(
            rol="analista de requerimientos",
            reglas_negocio=[
                "La solicitud se acepta solo si el número predial existe en la base catastral",
                REGLA_DEL_DOMINIO,
            ],
            excepciones=["Fallo en la digitalización de los documentos escaneados"],
        ),
        conversacion,
    )
    assert registro.rol is None
    assert registro.reglas_negocio == (
        "La solicitud se acepta solo si el número predial existe en la base catastral",
    )
    assert registro.excepciones == ()


@pytest.mark.parametrize(
    ("texto", "dicho"),
    [
        ("4 dígitos", "La vigencia debe ser de cuatro dígitos"),
        ("cuatro dígitos", "La vigencia es de 4 dígitos"),
        ("30 dígitos", "El número predial tiene treinta dígitos"),
        ("área construida igual a 0", "El área construida puede ser cero"),
    ],
)
def test_un_numero_en_letras_respalda_el_mismo_en_cifras(texto, dicho):
    assert respaldado(texto, raices(dicho))


def test_los_articulos_no_cuentan_como_numeros():
    assert raices("Una solicitud por un predio") == {"solic", "predi"}


def test_la_restriccion_que_el_cliente_dice_en_letras_entra_al_registro():
    # Defecto hallado en el paso 11: el cliente dijo «cuatro dígitos», el modelo escribió
    # «4 dígitos» y el filtro la descartaba; el resumen no cambiaba y el cliente lo rechazaba
    # una y otra vez.
    completo = registro_completo()
    vigencia = DatoEntrada(nombre="vigencia", tipo="texto", obligatorio=True)
    previo = completo.model_copy(update={"datos_entrada": (*completo.datos_entrada, vigencia)})
    conversacion = con_respuesta(
        previo,
        f"{resumen_para_confirmar(previo)}\n{PREGUNTA_CIERRE}",
        "No, falta indicar que la vigencia debe ser de cuatro dígitos. Lo demás sí coincide.",
    )
    precisada = vigencia.model_dump() | {"restriccion": "4 dígitos"}
    registro = aplicar_extraccion(
        salida_extraccion(datos_entrada=[*DATOS_ENTRADA, precisada]), conversacion
    )
    assert registro.datos_entrada[-1].restriccion == "4 dígitos"
    assert not registro.resumen_confirmado


@pytest.mark.parametrize(
    ("respuesta", "conservadas"),
    [
        ("El documento soporte es obligatorio", ()),
        ("No sé qué tipos de documento se aceptan", ("¿Qué tipos de documento se aceptan?",)),
        ("Si el predio no existe, no se acepta", ()),
    ],
)
def test_solo_hay_preguntas_abiertas_si_el_cliente_no_sabe(respuesta, conservadas):
    registro = aplicar_extraccion(
        salida_extraccion(preguntas_abiertas=["¿Qué tipos de documento se aceptan?"]),
        con_respuesta(RegistroCaptura(), "¿Qué documentos se aceptan?", respuesta),
    )
    assert registro.preguntas_abiertas == conservadas


def test_resumen_para_confirmar_sale_del_registro():
    registro = registro_completo().model_copy(update={"supuestos": ("Prioridad alta",)})
    resumen = resumen_para_confirmar(registro)
    assert resumen.splitlines() == [
        "Le resumo lo que entendí:",
        "- A quién le sirve: analista de conservación catastral",
        "- Qué necesita: registrar solicitudes de mutación de propietario con su documento soporte",
        "- Para qué: tramitar el cambio en la información del predio y hacerle seguimiento",
        "- Reglas: La solicitud se acepta solo si el número predial existe y el documento "
        "soporte no tiene fecha posterior a la radicación",
        # Los nombres van como quedaron en el registro (caso 08 de la corrida ampliada), y cada
        # dato con su tipo (ADR-0015).
        "- Datos que se reciben: numero_predial (texto, obligatorio, 30 dígitos); fecha_documento "
        "(fecha, obligatorio, no posterior a la fecha de radicación)",
        "- Resultados que se entregan: radicado (texto, RAD-AAAA-NNNNNN)",
        "- Casos de error: Si el número predial no existe, la solicitud se rechaza",
        "- Supuestos por confirmar: Prioridad alta",
    ]
    assert "?" not in resumen


def test_el_resumen_muestra_junto_al_rol_quien_lo_usa():
    # Caso 14: el cliente buscaba la tarea programada junto al rol y la pedía hasta agotar los
    # turnos; un aviso que lo remitía a las condiciones lo objetaba por sí mismo (ADR-0015).
    uso = "también la usa una tarea programada cada noche"
    prueba = "para las pruebas, la carpeta puede ser local"
    registro = registro_completo().model_copy(update={"condiciones": (uso, prueba)})
    lineas = resumen_para_confirmar(registro).splitlines()
    assert lineas[1:3] == [
        "- A quién le sirve: analista de conservación catastral",
        f"- Quién lo usa y cómo: {uso}",
    ]
    assert f"- Condiciones ya definidas: {prueba}" in lineas


def test_quien_lo_usa_queda_aparte_del_rol_y_junto_a_el_en_el_resumen():
    # Casos 02, 05 y 06: el cliente distingue a quien lo usa de a quien le sirve.
    respuesta = "Lo usa el jefe de bodega al preparar cada pedido; a operaciones le sirve"
    previo = registro_completo(casos_limite_cerrados=False)
    conversacion = con_respuesta(previo, "¿Quién lo usa?", respuesta)
    usuario = "el jefe de bodega, al preparar cada pedido"
    registro = aplicar_extraccion(salida_extraccion(usuarios=[usuario]), conversacion)
    assert registro.usuarios == (usuario,)
    assert registro.rol == previo.rol
    lineas = resumen_para_confirmar(registro).splitlines()
    assert lineas[2] == f"- Quién lo usa y cómo: {usuario}"


@pytest.mark.parametrize(
    "respuesta",
    [
        "Eso no me lo especificaron.",
        "No está definido qué debe pasar en ese caso.",
        "No me han dicho qué mensaje debe mostrar.",
        "No tengo una regla para cuando los ítems no coinciden.",
        "Eso no lo tengo definido.",
        "Los mensajes exactos de error no los conozco.",
        # Corrida de la fase 7, caso 10: N3 preguntaba el rol hasta agotar los turnos.
        "No aplica; no tengo identificado un cargo del negocio que deba quedar ahí.",
        "No tengo identificado un cargo concreto para poner ahí.",
        "Eso no aplica en nuestro proceso.",
    ],
)
def test_reconoce_las_formas_de_no_saber(respuesta):
    # Caso 18: sin reconocerlas, N3 preguntaba lo mismo hasta agotar los turnos.
    assert dice_no_saber(respuesta)


@pytest.mark.parametrize(
    "respuesta",
    [
        "Si el predio no existe, no se acepta",
        "El documento no está vencido",
        "Ya me lo dijeron",
        "El descuento no aplica a los predios rurales",
    ],
)
def test_no_confunde_otras_negaciones_con_no_saber(respuesta):
    assert not dice_no_saber(respuesta)


def test_el_resumen_muestra_solo_los_tipos_que_dijo_el_cliente():
    # Caso 17: el cliente objetaba tipos que la extracción supuso, como «número entero».
    registro = registro_completo().model_copy(
        update={
            "datos_entrada": (
                DatoEntrada(nombre="tiempo de respuesta", tipo="número entero", obligatorio=True),
                DatoEntrada(nombre="valor", tipo="número decimal", obligatorio=False),
            ),
            "datos_salida": (DatoSalida(nombre="promedio", tipo="número decimal"),),
        }
    )
    lineas = resumen_para_confirmar(registro, raices("El valor lleva dos decimales")).splitlines()
    assert lineas[5:7] == [
        "- Datos que se reciben: tiempo de respuesta (obligatorio); valor (número decimal, "
        "opcional)",
        "- Resultados que se entregan: promedio (número decimal)",
    ]
    sin_tipos = resumen_para_confirmar(registro, raices("Se registra cada trámite")).splitlines()
    assert sin_tipos[5:7] == [
        "- Datos que se reciben: tiempo de respuesta (obligatorio); valor (opcional)",
        "- Resultados que se entregan: promedio",
    ]


NOMBRES = ["numero_tramite", "tipo_tramite", "fecha_cambio"]


@pytest.mark.parametrize(
    ("dichos", "esperados"),
    [
        # Corrida de la fase 7, casos 17 y 18: el cliente objeta con las mismas palabras.
        (["No quedó definido que los datos de entrada sean obligatorios ni su tipo."], set()),
        (["También sigue sin quedar definido si los datos son obligatorios."], set()),
        (["No pondría «obligatorio» en el tipo de trámite; tampoco «opcional»."], set()),
        (
            ["El número del trámite es obligatorio y la fecha del cambio es opcional."],
            {"numero_tramite", "fecha_cambio"},
        ),
        (["Todos los datos son obligatorios."], set(NOMBRES)),
        # La negación de otra cláusula no alcanza a la obligatoriedad (caso 03).
        (["No se registra si falta la fecha del cambio, porque es obligatoria."], {"fecha_cambio"}),
        (["El tipo de trámite no es opcional sino obligatorio."], {"tipo_tramite"}),
        (["Se recibe el número del trámite.", "El tipo de trámite es requerido"], {"tipo_tramite"}),
    ],
)
def test_la_obligatoriedad_cuenta_solo_si_el_cliente_la_dice_sin_negarla(dichos, esperados):
    assert obligatoriedad_dicha(NOMBRES, dichos) == esperados


def test_el_resumen_muestra_la_obligatoriedad_solo_si_el_cliente_la_dijo():
    registro = registro_completo().model_copy(
        update={
            "datos_entrada": (
                DatoEntrada(nombre="numero_tramite", tipo="texto", obligatorio=True),
                DatoEntrada(nombre="fecha_cambio", tipo="fecha", obligatorio=False),
            ),
        }
    )
    dicho = "El número del trámite es obligatorio; no definimos nada sobre la fecha."
    lineas = resumen_para_confirmar(registro, raices(dicho), [dicho]).splitlines()
    assert lineas[5] == (
        "- Datos que se reciben: numero_tramite (obligatorio); fecha_cambio (fecha)"
    )
    sin_decirlo = resumen_para_confirmar(registro, raices(dicho), ["Se recibe el trámite."])
    assert "- Datos que se reciben: numero_tramite; fecha_cambio (fecha)" in sin_decirlo


@pytest.mark.parametrize(
    ("pregunta", "mensaje"),
    [
        ("  ", "Debes formular"),
        ("¿Quién lo usa? ¿Para qué?", "una sola"),
        ("¿Qué campos de la API necesita?", "términos técnicos"),
        ("¿El numero_predial es obligatorio?", "numero_predial"),
        ("¿Cuál es el beneficio y, para cerrar, ¿está correcto este resumen?", "una sola"),
        ("Antes de seguir, ¿me confirma el resumen?", "no pidas confirmar"),
    ],
)
def test_reglas_de_la_pregunta(pregunta, mensaje):
    with pytest.raises(ErrorValidacionSalida, match=mensaje):
        validar_pregunta(salida_pregunta(pregunta), RegistroCaptura())


def test_confirmar_un_dato_puntual_es_una_pregunta_valida():
    pregunta = "Estoy asumiendo que el número predial tiene 30 dígitos, ¿puede confirmarlo?"
    assert validar_pregunta(salida_pregunta(pregunta), RegistroCaptura()) == (pregunta)


def test_la_pregunta_de_cierre_lleva_el_resumen():
    registro = registro_completo()
    pregunta = validar_pregunta(salida_pregunta("El revisor pide el año; ¿lo incluimos?"), registro)
    assert pregunta == f"{resumen_para_confirmar(registro)}\nEl revisor pide el año; ¿lo incluimos?"


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
        conversacion_completa(),
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
    assert [dato.nombre for dato in rf1.descripcion.datos_entrada] == [
        "numero_predial",
        "fecha_documento",
    ]
    assert sintesis.referencias["RF-01"] == (
        "dom-002 v1.0 · Mutaciones catastrales",
        "eli-006 v1.0 · Guía de preguntas",
    )


def test_sintesis_toma_la_prioridad_del_registro():
    # El modelo propone «alta»; el cliente dijo «media» y quedó en el registro.
    conversacion = conversacion_completa()
    registro = conversacion.registro.model_copy(update={"prioridad": Prioridad.MEDIA})
    sintesis = validar_sintesis(
        salida_sintesis(),
        conversacion.model_copy(update={"registro": registro}),
        contexto_recuperado(),
        Requerimientos(),
        "Gestión catastral",
    )
    [historia] = sintesis.historias
    assert historia.prioridad is Prioridad.MEDIA
    assert sintesis.requerimientos[0].prioridad is Prioridad.MEDIA


def conversacion_con(texto: str) -> Conversacion:
    turno = Turno(emisor=Emisor.CLIENTE, texto=texto, fecha=AHORA)
    completa = conversacion_completa()
    return completa.model_copy(update={"turnos": (*completa.turnos, turno)})


def test_sintesis_convierte_los_nombres_de_los_datos_en_identificadores():
    entrada = DATOS_ENTRADA[0] | {"nombre": "Número predial"}
    salida = salida_sintesis(requerimiento_modelo(datos_entrada=[entrada, DATOS_ENTRADA[1]]))
    sintesis = validar_sintesis(
        salida, conversacion_completa(), contexto_recuperado(), Requerimientos(), "Catastro"
    )
    assert sintesis.requerimientos[0].descripcion.datos_entrada[0].nombre == "numero_predial"


def test_sintesis_descarta_las_reglas_que_no_dijo_el_cliente():
    regla = (
        "La solicitud se acepta únicamente si el número predial existe y el documento soporte "
        f"no tiene fecha posterior a la radicación. {REGLA_DEL_DOMINIO}. Las mutaciones producen "
        "efectos fiscales a partir de la vigencia siguiente a su inscripción."
    )
    sintesis = validar_sintesis(
        salida_sintesis(requerimiento_modelo(regla_negocio=regla)),
        conversacion_completa(),
        contexto_recuperado(),
        Requerimientos(),
        "Catastro",
    )
    assert sintesis.requerimientos[0].descripcion.regla_negocio == (
        "La solicitud se acepta únicamente si el número predial existe y el documento soporte "
        "no tiene fecha posterior a la radicación."
    )


def test_sintesis_sin_nada_de_lo_dicho_se_rechaza():
    with pytest.raises(ErrorValidacionSalida, match="regla_negocio no contiene nada"):
        validar_sintesis(
            salida_sintesis(requerimiento_modelo(regla_negocio=REGLA_DEL_DOMINIO)),
            conversacion_completa(),
            contexto_recuperado(),
            Requerimientos(),
            "Catastro",
        )


def test_sintesis_con_registro_incompleto_declara_lo_pendiente():
    incompleta = conversacion_completa().model_copy(
        update={"registro": registro_completo().model_copy(update={"reglas_negocio": ()})}
    )
    sintesis = validar_sintesis(
        salida_sintesis(requerimiento_modelo(regla_negocio=REGLA_DEL_DOMINIO)),
        incompleta,
        contexto_recuperado(),
        Requerimientos(),
        "Catastro",
    )
    regla = sintesis.requerimientos[0].descripcion.regla_negocio
    assert regla == POR_CONFIRMAR
    requerimientos = Requerimientos(
        historias=sintesis.historias,
        requerimientos=sintesis.requerimientos,
        referencias=sintesis.referencias,
    )
    defectos = verificar_conjunto(requerimientos)
    assert any(defecto.requiere_cliente for defecto in defectos)


def test_sintesis_quita_las_palabras_clave_repetidas_en_los_escenarios():
    escenario = {
        "nombre": "Solicitud válida",
        "dado_que": "DADO QUE Dado que un predio registrado y un documento del 2026-09-30.",
        "cuando": "Cuando se registra la solicitud el 2026-10-01.",
        "entonces": "ENTONCES: el sistema genera el radicado",
    }
    escenarios = [escenario, *requerimiento_modelo()["escenarios"][1:]]
    sintesis = validar_sintesis(
        salida_sintesis(requerimiento_modelo(escenarios=escenarios)),
        conversacion_completa(),
        contexto_recuperado(),
        Requerimientos(),
        "Catastro",
    )
    primero = sintesis.requerimientos[0].criterios_aceptacion[0]
    assert (primero.dado_que, primero.cuando, primero.entonces) == (
        "un predio registrado y un documento del 2026-09-30",
        "se registra la solicitud el 2026-10-01",
        "el sistema genera el radicado",
    )


def test_sintesis_une_los_saltos_de_linea_escapados():
    salida = salida_sintesis(
        requerimiento_modelo(regla_negocio="Primera regla.\\nSegunda regla.\n  Tercera.")
    )
    sintesis = validar_sintesis(
        salida,
        conversacion_con("Primera regla. Segunda regla. Tercera."),
        contexto_recuperado(),
        Requerimientos(),
        "Catastro",
    )
    regla = sintesis.requerimientos[0].descripcion.regla_negocio
    assert regla == "Primera regla. Segunda regla. Tercera."


ECO_DE_LA_EXPLORACION = "¿Qué debe pasar si el documento soporte vence durante el trámite?"


def salida_con_preguntas(*preguntas: str) -> SalidaSintesis:
    salida = salida_sintesis()
    historia = salida.historia.model_copy(update={"preguntas_abiertas": list(preguntas)})
    return salida.model_copy(update={"historia": historia})


def test_con_el_resumen_confirmado_las_preguntas_abiertas_son_las_del_registro():
    # Corridas de la fase 5: N5 volvía preguntas abiertas los «no sé» de los casos límite, que no
    # bloquean los requerimientos, y N6 escalaba sin corregir lo demás.
    abierta = "¿Qué tipos de documento se aceptan?"
    registro = RegistroCaptura.model_validate(
        {**registro_completo().model_dump(), "preguntas_abiertas": (abierta,)}
        | {"resumen_confirmado": True}
    )
    conversacion = conversacion_completa().model_copy(update={"registro": registro})
    sintesis = validar_sintesis(
        salida_con_preguntas(ECO_DE_LA_EXPLORACION),
        conversacion,
        contexto_recuperado(),
        Requerimientos(),
        "Catastro",
    )
    assert sintesis.historias[0].preguntas_abiertas == [abierta]


def test_sin_confirmar_la_sintesis_puede_agregar_preguntas_abiertas():
    sintesis = validar_sintesis(
        salida_con_preguntas(ECO_DE_LA_EXPLORACION),
        conversacion_completa(),
        contexto_recuperado(),
        Requerimientos(),
        "Catastro",
    )
    assert sintesis.historias[0].preguntas_abiertas == [ECO_DE_LA_EXPLORACION]


def test_preguntas_abiertas_requieren_al_cliente(cliente_falso):
    contexto = contexto_recuperado()
    sintesis = validar_sintesis(
        salida_sintesis(), conversacion_completa(), contexto, Requerimientos(), "Catastro"
    )
    historia = sintesis.historias[0].model_copy(
        update={"preguntas_abiertas": ["¿Qué tipos de documento se aceptan?"]}
    )
    requerimientos = Requerimientos(
        historias=(historia,),
        requerimientos=sintesis.requerimientos,
        referencias=sintesis.referencias,
    )
    verificacion = agente(cliente_falso(), RegistroEnMemoria()).verificar_calidad(requerimientos)
    assert verificacion.requiere_cliente
    assert verificacion.defectos == (
        "HU-01 · C4 Completo · preguntas_abiertas: quedan 1 preguntas sin resolver con el cliente",
    )
    assert verificacion.del_cliente == verificacion.defectos
    assert verificacion.corregibles == ()


def test_los_defectos_del_cliente_estan_entre_los_defectos():
    with pytest.raises(ValidationError, match="defectos del cliente"):
        VerificacionCalidad(defectos=("uno",), del_cliente=("otro",))
    verificacion = VerificacionCalidad(defectos=("uno", "otro"), del_cliente=("otro",))
    assert verificacion.corregibles == ("uno",)


def test_sintesis_limpia_pasa_la_verificacion_de_calidad():
    sintesis = validar_sintesis(
        salida_sintesis(),
        conversacion_completa(),
        contexto_recuperado(),
        Requerimientos(),
        "Gestión catastral",
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
            conversacion_completa(),
            contexto_recuperado(),
            Requerimientos(),
            "Gestión catastral",
        )


def test_mensajes_de_correccion_incluyen_los_defectos():
    contexto = contexto_recuperado()
    sintesis = validar_sintesis(
        salida_sintesis(), conversacion_completa(), contexto, Requerimientos(), "Catastro"
    )
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
        recuperador or RecuperadorFalso(),
        invocador("N3", "extraccion"),
        invocador("N3", "dialogo"),
        invocador("N5", "sintesis"),
        invocador("N5", "enmienda"),
    )


def pregunta(texto: str) -> SalidaPregunta:
    return salida_pregunta(texto)


def test_los_prompts_del_elicitador_estan_versionados():
    for nombre, nodo in (
        ("extraccion", "N3"),
        ("dialogo", "N3"),
        ("sintesis", "N5"),
        ("enmienda", "N5"),
    ):
        prompt = cargar_prompt("elicitador", nombre)
        assert prompt.metadatos.nodo == nodo
        assert prompt.identificador == f"elicitador.{nombre}@{prompt.metadatos.version}"
        assert CLAVE_PROBLEMAS in prompt.texto


def test_n3_extrae_sin_contexto_y_pregunta_con_contexto(cliente_falso, completar_respuesta):
    cliente = cliente_falso(
        completar_respuesta(salida_extraccion(funcionalidad="registrar solicitudes de mutación")),
        completar_respuesta(pregunta("¿Qué cargo tiene quien registra las solicitudes?")),
    )
    dialogo = agente(cliente, RegistroEnMemoria()).dialogar(abierta(), contexto_recuperado())
    assert dialogo.registro.funcionalidad == "registrar solicitudes de mutación"
    assert dialogo.siguiente_pregunta == "¿Qué cargo tiene quien registra las solicitudes?"
    extraccion, siguiente = (llamada["messages"] for llamada in cliente.llamadas)
    assert extraccion[0]["content"] == cargar_prompt("elicitador", "extraccion").texto
    assert len(extraccion) == 2 and "contexto" not in json.loads(extraccion[1]["content"])
    assert siguiente[0]["content"] == cargar_prompt("elicitador", "dialogo").texto
    assert "contexto" in json.loads(siguiente[1]["content"])


def casi_completo(casos_limite_cerrados: bool) -> Conversacion:
    """Conversación a la que solo le falta el caso de error, que trae la respuesta nueva."""
    parcial = {k: v for k, v in COMPLETO.items() if k != "excepciones"}
    registro_parcial = registro_desde_salida(
        salida_extraccion(**parcial), RegistroCaptura(), raices(DICHO_POR_EL_CLIENTE)
    ).model_copy(
        update={
            "casos_limite_cerrados": casos_limite_cerrados,
            "algo_mas_preguntado": casos_limite_cerrados,
        }
    )
    return con_respuesta(
        registro_parcial, "¿Qué pasa si hay un error?", "Si el número predial no existe, se rechaza"
    )


def test_n3_presenta_el_resumen_sin_pedir_pregunta(cliente_falso, completar_respuesta):
    cliente = cliente_falso(
        completar_respuesta(salida_extraccion(excepciones=COMPLETO["excepciones"]))
    )
    conversacion = casi_completo(casos_limite_cerrados=True)
    dialogo = agente(cliente, RegistroEnMemoria()).dialogar(conversacion, contexto_recuperado())
    assert len(cliente.llamadas) == 1
    resumen = resumen_para_confirmar(
        dialogo.registro, raices_del_cliente(conversacion), dichos_del_cliente(conversacion)
    )
    assert dialogo.siguiente_pregunta == f"{resumen}\n{PREGUNTA_CIERRE}"
    # El cliente no dijo si los datos son obligatorios: el resumen no lo afirma.
    assert "numero_predial (30 dígitos)" in resumen and "obligatorio" not in resumen


def test_n3_con_todo_capturado_pregunta_un_caso_limite(cliente_falso, completar_respuesta):
    caso = "¿Qué debe pasar si el documento soporte es de hace más de un año?"
    cliente = cliente_falso(
        completar_respuesta(salida_extraccion(excepciones=COMPLETO["excepciones"])),
        completar_respuesta(salida_pregunta(caso, categoria="vigencia")),
    )
    dialogo = agente(cliente, RegistroEnMemoria()).dialogar(
        casi_completo(casos_limite_cerrados=False), contexto_recuperado()
    )
    assert dialogo.siguiente_pregunta == caso
    assert dialogo.registro.categorias_casos_limite == ("vigencia",)
    assert dialogo.registro.caso_limite_preguntado == "vigencia"
    estado = json.loads(cliente.llamadas[1]["messages"][2]["content"])
    assert estado["pendientes"] == ["casos_limite", "confirmacion"]
    assert estado["categorias_casos_limite_preguntadas"] == []


def test_un_caso_limite_no_repite_su_categoria():
    registro = registro_completo(casos_limite_cerrados=False).model_copy(
        update={"categorias_casos_limite": ("vigencia",)}
    )
    with pytest.raises(ErrorValidacionSalida, match="Ya preguntaste por la categoría"):
        validar_caso_limite(salida_pregunta("¿Y si cambia la vigencia?", "vigencia"), registro)
    with pytest.raises(ErrorValidacionSalida, match="categoria_caso_limite"):
        validar_caso_limite(salida_pregunta("¿Y si el predio no existe?"), registro)
    assert validar_caso_limite(salida_pregunta("", sin_mas=True), registro) is None
    # Sin ninguna pregunta todavía, no puede darse la fase por terminada.
    sin_preguntas = registro.model_copy(update={"categorias_casos_limite": ()})
    with pytest.raises(ErrorValidacionSalida, match="al menos por un caso límite"):
        validar_caso_limite(salida_pregunta("", sin_mas=True), sin_preguntas)
    assert validar_caso_limite(
        salida_pregunta("¿Qué debe pasar si el predio no existe?", "existencia"), registro
    ) == ("¿Qué debe pasar si el predio no existe?", "existencia")


def test_sin_mas_casos_limite_cierra_la_fase_y_pregunta_por_algo_mas(
    cliente_falso, completar_respuesta
):
    cliente = cliente_falso(
        completar_respuesta(salida_extraccion(excepciones=COMPLETO["excepciones"])),
        completar_respuesta(salida_pregunta("", sin_mas=True)),
    )
    conversacion = casi_completo(casos_limite_cerrados=False)
    ya_preguntado = conversacion.registro.model_copy(
        update={"categorias_casos_limite": ("vigencia",)}
    )
    dialogo = agente(cliente, RegistroEnMemoria()).dialogar(
        conversacion.model_copy(update={"registro": ya_preguntado}), contexto_recuperado()
    )
    assert dialogo.registro.casos_limite_cerrados
    # Antes del resumen, una sola vez, la pregunta de cierre de eli-006, sin llamar al modelo.
    assert dialogo.siguiente_pregunta == PREGUNTA_ALGO_MAS
    assert dialogo.registro.algo_mas_preguntado
    assert dialogo.registro.por_preguntar == ["confirmacion"]


def test_lo_que_define_el_cliente_queda_como_caso_limite_y_va_al_resumen():
    respuesta = "Si el documento soporte tiene más de un año, la solicitud igual se acepta"
    previo = registro_completo(casos_limite_cerrados=False).model_copy(
        update={"categorias_casos_limite": ("vigencia",), "caso_limite_preguntado": "vigencia"}
    )
    conversacion = con_respuesta(
        previo, "¿Qué debe pasar si el documento soporte es de hace más de un año?", respuesta
    )
    datos = json.loads(mensajes_extraccion(conversacion)[0]["content"])
    assert datos["caso_limite_preguntado"] == "vigencia"
    assert "categorias_casos_limite" not in datos["registro"]
    registro = aplicar_extraccion(salida_extraccion(casos_limite=[respuesta]), conversacion)
    assert registro.casos_limite == (respuesta,)
    assert registro.caso_limite_preguntado is None
    # Un «no sé» a un caso límite no cuenta contra un atributo.
    assert registro.no_sabe == ()
    assert f"- Casos especiales acordados: {respuesta}" in resumen_para_confirmar(registro)


def test_n3_pregunta_por_lo_que_falta_si_el_cliente_no_lo_da(cliente_falso, completar_respuesta):
    # Caso 06: «falta el ejemplo con cifras» sin darlo; repetir el resumen no ayuda.
    especifica = "¿Cuáles son las cifras del ejemplo que usan para verificar?"
    cliente = cliente_falso(
        completar_respuesta(salida_extraccion()), completar_respuesta(pregunta(especifica))
    )
    dialogo = agente(cliente, RegistroEnMemoria()).dialogar(
        esperando_confirmacion("Falta incluir que hay un ejemplo con cifras"), contexto_recuperado()
    )
    assert dialogo.siguiente_pregunta == especifica
    estado = json.loads(cliente.llamadas[1]["messages"][-1]["content"])
    assert estado["resumen_incompleto"] is True
    assert estado["pendientes"] == ["confirmacion"]


def test_n3_vuelve_al_resumen_cuando_el_cliente_dice_que_falta(cliente_falso, completar_respuesta):
    # Tras «¿qué falta?», una respuesta que agrega un dato muestra el resumen actualizado.
    nueva = "Si la fecha del documento es posterior a la radicación, se rechaza"
    conversacion = con_respuesta(registro_completo(), "¿Qué falta en el resumen?", nueva)
    cliente = cliente_falso(
        completar_respuesta(salida_extraccion(excepciones=[*COMPLETO["excepciones"], nueva]))
    )
    dialogo = agente(cliente, RegistroEnMemoria()).dialogar(conversacion, contexto_recuperado())
    assert dialogo.siguiente_pregunta.startswith("Le resumo lo que entendí:")
    assert nueva in dialogo.siguiente_pregunta


def test_n3_pregunta_por_lo_retirado_en_lugar_de_que_falta(cliente_falso, completar_respuesta):
    # Caso 18: retirar los resultados cambia el registro, así que N3 pregunta por ellos.
    siguiente = "¿Qué debe quedar hecho cuando llega el aviso de una venta?"
    cliente = cliente_falso(
        completar_respuesta(salida_extraccion(retirar=RETIRO_DE_RESULTADOS)),
        completar_respuesta(pregunta(siguiente)),
    )
    dialogo = agente(cliente, RegistroEnMemoria()).dialogar(
        respuesta_al_resumen(registro_de_la_caja(), RECHAZO_DE_RESULTADOS), contexto_recuperado()
    )
    assert dialogo.registro.pendientes == ["datos_salida", "confirmacion"]
    assert dialogo.siguiente_pregunta == siguiente
    assert len(cliente.llamadas) == 2


def test_n3_tras_dos_no_se_pregunta_por_el_siguiente_atributo(cliente_falso, completar_respuesta):
    previo = sin_salidas(INTENTOS_SIN_RESPUESTA - 1).model_copy(update={"excepciones": ()})
    siguiente = "¿Qué pasa si el número predial no existe?"
    cliente = cliente_falso(
        completar_respuesta(salida_extraccion()), completar_respuesta(pregunta(siguiente))
    )
    conversacion = con_respuesta(previo, "¿Qué debe entregar el registro?", NO_SE)
    dialogo = agente(cliente, RegistroEnMemoria()).dialogar(conversacion, contexto_recuperado())
    assert dialogo.registro.sin_respuesta == ["datos_salida"]
    assert dialogo.siguiente_pregunta == siguiente
    estado = json.loads(cliente.llamadas[1]["messages"][-1]["content"])
    assert estado["pendientes"] == ["excepciones", "confirmacion"]
    assert estado["sin_respuesta"] == ["datos_salida"]


def test_n3_cierra_al_confirmar_sin_lo_que_el_cliente_no_supo(cliente_falso, completar_respuesta):
    cliente = cliente_falso(completar_respuesta(salida_extraccion(confirma_resumen=True)))
    dialogo = agente(cliente, RegistroEnMemoria()).dialogar(
        respuesta_al_resumen(sin_salidas(INTENTOS_SIN_RESPUESTA), "Sí, es correcto"),
        contexto_recuperado(),
    )
    assert dialogo.registro.resumen_confirmado
    assert dialogo.registro.pendientes == ["datos_salida"]
    assert dialogo.siguiente_pregunta is None
    assert len(cliente.llamadas) == 1


def test_n3_cierra_sin_pregunta_al_confirmar(cliente_falso, completar_respuesta):
    cliente = cliente_falso(completar_respuesta(salida_extraccion(confirma_resumen=True)))
    dialogo = agente(cliente, RegistroEnMemoria()).dialogar(
        esperando_confirmacion(), contexto_recuperado()
    )
    assert dialogo.registro.resumen_confirmado
    assert dialogo.siguiente_pregunta is None
    assert len(cliente.llamadas) == 1


def test_n3_tras_un_rechazo_solo_pregunta(cliente_falso, completar_respuesta):
    conversacion = esperando_confirmacion(None).model_copy(
        update={"observaciones_revisor": ("Falta indicar si el radicado incluye el año",)}
    )
    cliente = cliente_falso(
        completar_respuesta(pregunta("¿El radicado debe incluir el año de radicación?"))
    )
    dialogo = agente(cliente, RegistroEnMemoria()).dialogar(conversacion, contexto_recuperado())
    [llamada] = cliente.llamadas
    assert json.loads(llamada["messages"][2]["content"])["observaciones_revisor"] == [
        "Falta indicar si el radicado incluye el año"
    ]
    assert dialogo.siguiente_pregunta.endswith("¿El radicado debe incluir el año de radicación?")
    assert dialogo.siguiente_pregunta.startswith("Le resumo lo que entendí:")


def test_reintento_con_los_problemas_del_intento_anterior(cliente_falso, completar_respuesta):
    cliente = cliente_falso(
        completar_respuesta(salida_extraccion()),
        completar_respuesta(pregunta("¿Quién? ¿Cuándo?")),
        completar_respuesta(pregunta("¿Quién lo usa?")),
    )
    registro = RegistroEnMemoria()
    dialogo = agente(cliente, registro).dialogar(abierta(), contexto_recuperado())
    assert dialogo.siguiente_pregunta == "¿Quién lo usa?"
    reintento = cliente.llamadas[2]["messages"]
    assert reintento[:-1] == cliente.llamadas[1]["messages"]
    assert CLAVE_PROBLEMAS in json.loads(reintento[-1]["content"])
    extraccion = cargar_prompt("elicitador", "extraccion").identificador
    dialogo_id = cargar_prompt("elicitador", "dialogo").identificador
    assert [llamada.prompt for llamada in registro.llamadas] == [extraccion, *[dialogo_id] * 2]


def test_reintento_agotado_propaga_el_error(cliente_falso, completar_respuesta):
    invalida = completar_respuesta(pregunta("¿Quién? ¿Cuándo?"))
    registro = RegistroEnMemoria()
    cliente = cliente_falso(completar_respuesta(salida_extraccion()), invalida, invalida)
    with pytest.raises(ErrorValidacionSalida, match="una sola"):
        agente(cliente, registro).dialogar(abierta(), contexto_recuperado())
    assert len(registro.llamadas) == 3


def test_una_conversacion_produce_un_requerimiento_que_pasa_la_calidad(
    cliente_falso, completar_respuesta
):
    parcial = {k: COMPLETO[k] for k in ("rol", "funcionalidad", "beneficio", "reglas_negocio")}
    cliente = cliente_falso(
        # Necesidad: extracción y pregunta.
        completar_respuesta(salida_extraccion(funcionalidad=COMPLETO["funcionalidad"])),
        completar_respuesta(pregunta("¿Qué cargo tiene la persona que procesa las solicitudes?")),
        # Rol, beneficio y reglas: extracción y pregunta por los datos.
        completar_respuesta(salida_extraccion(**parcial)),
        completar_respuesta(pregunta("¿Qué información necesita tener a la mano?")),
        # Datos y errores: con todo capturado, pregunta por un caso límite.
        completar_respuesta(salida_extraccion(**COMPLETO)),
        completar_respuesta(
            salida_pregunta(
                "¿Qué debe pasar si el documento soporte es de hace más de un año?", "vigencia"
            )
        ),
        # El cliente define el caso; no queda otra categoría que aplique, y sigue la pregunta por
        # algo más, que hace el sistema.
        completar_respuesta(salida_extraccion(casos_limite=[CASO_LIMITE])),
        completar_respuesta(salida_pregunta("", sin_mas=True)),
        completar_respuesta(salida_extraccion()),
        # Confirmación y síntesis.
        completar_respuesta(salida_extraccion(confirma_resumen=True)),
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
    preguntas = []
    for respuesta in (
        DICHO_POR_EL_CLIENTE,
        "El número predial de 30 dígitos y la fecha del documento; entrega un radicado "
        "RAD-AAAA-NNNNNN. Si el número predial no existe, la solicitud se rechaza.",
        CASO_LIMITE,
        "No, eso es todo",
        "Sí, es correcto",
    ):
        assert avance.pausa.punto == "dialogo"
        preguntas.append(avance.pausa.datos["pregunta"])
        avance = avanzar(app, id_sesion, respuesta)

    assert preguntas[2].startswith("¿Qué debe pasar si el documento soporte")
    assert preguntas[3] == PREGUNTA_ALGO_MAS
    assert preguntas[4].startswith("Le resumo lo que entendí:")
    assert f"Casos especiales acordados: {CASO_LIMITE}" in preguntas[4]
    assert avance.pausa.punto == "requerimientos"
    assert avance.pausa.datos["defectos"] == []
    assert avance.pausa.datos["referencias"]["RF-01"]
    estado = app.get_state(configuracion_hilo(id_sesion)).values
    [requerimiento] = estado["requerimientos"].requerimientos
    assert requerimiento.proyecto == "Gestión catastral"
    assert estado["conversacion"].registro.resumen_confirmado
    assert [llamada.nodo for llamada in registro.llamadas] == ["N3"] * 10 + ["N5"]
    # El prompt de pregunta y el contexto forman un prefijo idéntico, apto para la caché.
    assert cliente.llamadas[1]["messages"][:2] == cliente.llamadas[3]["messages"][:2]
    assert avance.nodos == (Nodo.N3, Nodo.N4, Nodo.N5)


def test_un_no_se_a_un_caso_limite_no_deja_preguntas_abiertas():
    previo = registro_completo(casos_limite_cerrados=False).model_copy(
        update={"categorias_casos_limite": ("estado",), "caso_limite_preguntado": "estado"}
    )
    conversacion = con_respuesta(
        previo, "¿Qué debe pasar si se reversa un abono ya reversado?", "No lo sé"
    )
    registro = aplicar_extraccion(
        salida_extraccion(preguntas_abiertas=["Qué pasa al reversar un abono ya reversado"]),
        conversacion,
    )
    assert registro.preguntas_abiertas == ()
    assert registro.casos_limite == ()


def test_una_lista_parcial_de_datos_no_borra_los_demas():
    previo = registro_completo(casos_limite_cerrados=False)
    respuesta = "La fecha del documento es obligatoria y no puede ser posterior a hoy"
    conversacion = con_respuesta(previo, "¿Qué restricciones tiene la fecha?", respuesta)
    corregida = {
        "nombre": "fecha_documento",
        "tipo": "fecha",
        "obligatorio": True,
        "restriccion": "no puede ser posterior a hoy",
    }
    registro = aplicar_extraccion(salida_extraccion(datos_entrada=[corregida]), conversacion)
    # El dato mencionado se corrige y el que no se mencionó se conserva.
    assert [d.nombre for d in registro.datos_entrada] == ["numero_predial", "fecha_documento"]
    assert registro.datos_entrada[1].restriccion == "no puede ser posterior a hoy"


CONDICION_NOCTURNA = "Se ejecuta cada noche como tarea programada"


def test_una_lista_parcial_de_textos_conserva_lo_que_la_respuesta_no_menciona():
    # Caso 15: la extracción devolvía solo la condición nueva y la nocturna se perdía.
    previo = registro_completo(casos_limite_cerrados=False).model_copy(
        update={"condiciones": (CONDICION_NOCTURNA,)}
    )
    respuesta = "Para las pruebas, el archivo puede leerse de una carpeta local"
    conversacion = con_respuesta(previo, "¿Cómo se prueba?", respuesta)
    registro = aplicar_extraccion(salida_extraccion(condiciones=[respuesta]), conversacion)
    assert registro.condiciones == (CONDICION_NOCTURNA, respuesta)


def test_lo_que_la_respuesta_corrige_sale_de_la_lista():
    previo = registro_completo(casos_limite_cerrados=False).model_copy(
        update={"condiciones": (CONDICION_NOCTURNA,)}
    )
    respuesta = "No es cada noche: se ejecuta cada hora como tarea programada"
    conversacion = con_respuesta(previo, "¿Cuándo se ejecuta?", respuesta)
    corregida = "Se ejecuta cada hora como tarea programada"
    registro = aplicar_extraccion(salida_extraccion(condiciones=[corregida]), conversacion)
    assert registro.condiciones == (corregida,)


def test_lo_que_la_respuesta_quita_sale_aunque_el_modelo_no_lo_retire():
    local = "Para las pruebas, el archivo puede leerse de una carpeta local"
    previo = registro_completo(casos_limite_cerrados=False).model_copy(
        update={"condiciones": (CONDICION_NOCTURNA, local)}
    )
    respuesta = "Ya no se ejecuta cada noche como tarea programada: la lanza el analista"
    conversacion = con_respuesta(previo, "¿Cómo se ejecuta?", respuesta)
    registro = aplicar_extraccion(salida_extraccion(condiciones=[local]), conversacion)
    assert registro.condiciones == (local,)


REGLAS_DEL_TIPO = (
    "El tipo en minúsculas se corrige a mayúsculas",
    "El consecutivo de menos de cinco dígitos se completa con ceros a la izquierda",
)


def test_una_regla_que_solo_comparte_una_palabra_con_la_respuesta_se_conserva():
    # Caso 14: «falta que el tipo solo puede ser ESC, CER o PAZ» compartía «tipo» con la regla de
    # las minúsculas, que se perdía y el cliente volvía a pedir en el resumen siguiente.
    previo = registro_completo(casos_limite_cerrados=False).model_copy(
        update={"reglas_negocio": REGLAS_DEL_TIPO}
    )
    respuesta = "No del todo: falta especificar que el tipo solo puede ser ESC, CER o PAZ"
    conversacion = respuesta_al_resumen(previo, respuesta)
    nueva = "El tipo solo puede ser ESC, CER o PAZ"
    registro = aplicar_extraccion(
        salida_extraccion(reglas_negocio=[REGLAS_DEL_TIPO[1], nueva]), conversacion
    )
    assert registro.reglas_negocio == (*REGLAS_DEL_TIPO, nueva)


def test_dos_palabras_frecuentes_no_bastan_para_hablar_de_una_entrada():
    # Caso 15: la respuesta sobre los valores por defecto comparte «archivo» y «comprimir» con la
    # regla de los archivos de hoy, pero no habla de ella.
    hoy = "Un archivo modificado hoy nunca se comprime"
    compresion = "El límite para comprimir es de 7 días por defecto"
    previo = registro_completo(casos_limite_cerrados=False).model_copy(
        update={"reglas_negocio": (hoy, compresion)}
    )
    respuesta = (
        "El límite para comprimir y el límite para purgar van por defecto en 7 y 90 días; el "
        "estado muestra cada archivo con su tamaño"
    )
    purga = "El límite para purgar es de 90 días por defecto"
    registro = aplicar_extraccion(
        salida_extraccion(reglas_negocio=[compresion, purga]),
        respuesta_al_resumen(previo, respuesta),
    )
    assert registro.reglas_negocio == (hoy, compresion, purga)


def test_una_regla_reformulada_reemplaza_a_la_previa_en_su_lugar():
    vaga = "Los nombres de los archivos deben seguir la convención definida"
    previo = registro_completo(casos_limite_cerrados=False).model_copy(
        update={"reglas_negocio": (vaga, REGLAS_DEL_TIPO[0])}
    )
    respuesta = "Los nombres de los archivos siguen la convención exacta TIPO_AAAA_NNNNN.pdf"
    conversacion = respuesta_al_resumen(previo, respuesta)
    precisa = "Los nombres de los archivos deben seguir la convención exacta TIPO_AAAA_NNNNN.pdf"
    registro = aplicar_extraccion(salida_extraccion(reglas_negocio=[precisa]), conversacion)
    assert registro.reglas_negocio == (precisa, REGLAS_DEL_TIPO[0])


def test_los_ejemplos_del_cliente_quedan_en_el_registro_y_en_el_resumen():
    ejemplo = "Un predio con 30 dígitos radicado hoy recibe el radicado RAD-2026-000123"
    previo = registro_completo(casos_limite_cerrados=False)
    conversacion = con_respuesta(previo, "¿Tiene un ejemplo con cifras?", ejemplo)
    registro = aplicar_extraccion(salida_extraccion(ejemplos=[ejemplo]), conversacion)
    assert registro.ejemplos == (ejemplo,)
    assert f"- Ejemplos para verificar: {ejemplo}" in resumen_para_confirmar(registro)
