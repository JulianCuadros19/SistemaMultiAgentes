"""Agente arquitecto con recuperador y modelo falsos: N7, N8 (selección y parametrización) y N9."""

import json
import re
from datetime import date
from decimal import Decimal

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from multiagente.agentes.arquitecto.catalogo import ErrorCatalogo, titulos_del_catalogo
from multiagente.agentes.arquitecto.contexto import (
    consulta_de_requerimientos,
    mensaje_contexto,
    recuperar_catalogo,
)
from multiagente.agentes.arquitecto.parametrizacion import (
    SalidaEspecificacion,
    especificacion_desde_salida,
)
from multiagente.agentes.arquitecto.seleccion import (
    SalidaSeleccion,
    registro_de_decision,
    validar_seleccion,
)
from multiagente.agentes.arquitecto.servicio import AgenteArquitecto
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
from multiagente.llm.costos import Tarifa
from multiagente.llm.invocador import ErrorValidacionSalida, InvocadorNodo, ParametrosNodo
from multiagente.llm.prompts import cargar_prompt
from multiagente.llm.traza import RegistroEnMemoria
from multiagente.orquestador.ejecucion import avanzar, configuracion_hilo, iniciar_sesion
from multiagente.orquestador.estado import Arquitectura, Contexto, FragmentoContexto, Requerimientos
from multiagente.orquestador.grafo import Nodo, construir_grafo
from multiagente.orquestador.servicios import Servicios, Sintesis
from multiagente.orquestador.simulacion import ElicitadorFijo, ServiciosSimulados, aprobar, rechazar
from multiagente.persistencia.puntos_control import serializador
from multiagente.rag.colecciones import Agente, Coleccion
from multiagente.rag.recuperacion import FragmentoRecuperado, ResultadoRecuperacion

TARIFAS = {
    "gpt-5": Tarifa(
        entrada=Decimal("1.25"), entrada_cacheada=Decimal("0.125"), salida=Decimal("10")
    )
}
TITULOS = titulos_del_catalogo()
ARQUITECTURAS = frozenset(TITULOS)
COLECCION = Coleccion.ARQUITECTURAS_REFERENCIA


# Requerimientos aprobados ----------------------------------------------------------------------


def requerimiento(identificador: str, quiero: str) -> RequerimientoFormal:
    return RequerimientoFormal(
        id_requerimiento=identificador,
        version="0.1",
        proyecto="Catastro",
        tipo_solicitud=TipoSolicitud.NUEVO,
        impacto=Impacto.ALTO,
        modulo="avaluo",
        autor="Agente elicitador",
        area_funcional="Liquidación",
        titulo=Enunciado(como="liquidador catastral", quiero=quiero, para="liquidar el impuesto"),
        descripcion=Descripcion(
            precondicion="El predio existe",
            regla_negocio="El avalúo es la suma del avalúo del terreno y de la construcción.",
            datos_entrada=[DatoEntrada(nombre="numero_predial", tipo="str", obligatorio=True)],
            datos_salida=[DatoSalida(nombre="avaluo_total", tipo="Decimal")],
        ),
        criterios_aceptacion=[
            EscenarioAceptacion(
                id="ESC-01", dado_que="un predio", cuando="se calcula", entonces="ok"
            ),
            EscenarioAceptacion(
                id="ESC-02",
                dado_que="un predio inexistente",
                cuando="se calcula",
                entonces="rechaza",
            ),
        ],
        prioridad=Prioridad.ALTA,
    )


RF1 = requerimiento("RF-01", "calcular el avalúo de un predio")
RF2 = requerimiento("RF-02", "liquidar el impuesto predial del periodo")
APROBADOS = Requerimientos(
    historias=(HistoriaUsuario(id="HU-01", enunciado=RF1.titulo),),
    requerimientos=(RF1, RF2),
)


# N7 --------------------------------------------------------------------------------------------


def recuperado(identificador: int, documento: str, titulo: str) -> FragmentoRecuperado:
    return FragmentoRecuperado(
        id=identificador,
        coleccion=COLECCION,
        documento_id=documento,
        version_documento="1.0",
        titulo=titulo,
        contenido=f"Contenido de {titulo}",
        metadatos={},
        similitud=0.6,
        rango_semantico=1,
        rango_lexico=1,
        puntaje=0.03,
    )


CRITERIOS = recuperado(1, "arq-003", "Criterios de selección de arquitectura › Paso 1")


class RecuperadorFalso:
    """Como el real: el documento de criterios, que nombra todas las ARQ, sale primero."""

    def __init__(self, sin: str | None = None) -> None:
        self.consultas: list[tuple[str, int | None]] = []
        self.sin = sin

    def recuperar(self, consulta, colecciones=None, k=None) -> ResultadoRecuperacion:
        assert list(colecciones) == [COLECCION]
        self.consultas.append((consulta, k))
        if consulta[:6] in TITULOS:
            identificador = consulta[:6]
            fragmentos = [CRITERIOS]
            if identificador != self.sin:
                numero = int(identificador[-2:])
                documento = f"arq-arq-0{numero}"
                fragmentos.append(recuperado(100 + numero, documento, TITULOS[identificador]))
        elif consulta.startswith("Criterios"):
            fragmentos = [CRITERIOS]
        elif consulta.startswith(("Plantilla", "Esquema", "Catálogo")):
            documento = {"Plantilla": "arq-001", "Esquema": "arq-002", "Catálogo": "arq-004"}[
                consulta.split()[0]
            ]
            fragmentos = [recuperado(200 + len(self.consultas), documento, consulta[:20])]
        else:
            fragmentos = [recuperado(300, "arq-005", "Patrones de diseño aplicables › Repositorio")]
        return ResultadoRecuperacion(
            agente=Agente.ARQUITECTO,
            consulta=consulta,
            colecciones=(COLECCION,),
            fragmentos=tuple(fragmentos),
            descartados=(),
        )


def test_n7_recupera_las_seis_arquitecturas_primero_y_sin_repetir():
    recuperador = RecuperadorFalso()
    contexto = recuperar_catalogo(recuperador, APROBADOS)
    documentos = [f.documento_id for f in contexto.fragmentos[COLECCION.value]]
    assert documentos[:6] == [f"arq-arq-0{n}" for n in range(1, 7)]
    assert set(documentos[6:]) == {"arq-003", "arq-001", "arq-002", "arq-004", "arq-005"}
    assert len(documentos) == len(set(documentos))
    assert set(contexto.fragmentos) == {COLECCION.value}
    assert recuperador.consultas[0] == ("ARQ-01 · Arquitectura en capas", 5)


def test_n7_falla_si_falta_una_arquitectura_del_catalogo():
    with pytest.raises(ErrorCatalogo, match="ARQ-04"):
        recuperar_catalogo(RecuperadorFalso(sin="ARQ-04"), APROBADOS)


def test_consulta_construida_con_los_requerimientos_completos():
    consulta = consulta_de_requerimientos(APROBADOS)
    assert "calcular el avalúo de un predio" in consulta
    assert "liquidar el impuesto predial" in consulta
    assert "numero_predial" in consulta


def test_el_arquitecto_solo_ve_su_coleccion():
    ajeno = FragmentoContexto(
        documento_id="eli-006", version_documento="1.0", titulo="Guía", contenido="x", similitud=1
    )
    contexto = recuperar_catalogo(RecuperadorFalso(), APROBADOS).combinar(
        Contexto(fragmentos={"elicitacion": (ajeno,)})
    )
    fuentes = [f["fuente"] for f in json.loads(mensaje_contexto(contexto)["content"])["contexto"]]
    assert not any(fuente.startswith("eli-") for fuente in fuentes)


# N8 · selección --------------------------------------------------------------------------------


def opcion(identificador: str, motivo: str | None) -> dict:
    return {
        "id": identificador,
        "favorables": ["estructura familiar"],
        "desfavorables": ["capas anémicas"],
        "motivo_descarte": motivo,
    }


def salida_seleccion(**cambios) -> SalidaSeleccion:
    base = {
        "titulo": "Arquitectura del módulo de avalúo",
        "contexto": "El módulo calcula el avalúo (RF-01) y liquida el impuesto (RF-02).",
        "factores": ["lógica de negocio moderada"],
        "opciones": [
            opcion("arq-01", None),
            opcion("ARQ-02", "RF-01 tiene reglas simples: la hexagonal sería sobreingeniería"),
        ],
        "elegida": "ARQ-01",
        "justificacion": "RF-01 y RF-02 concentran reglas moderadas con flujo predecible.",
        "consecuencias_favorables": ["separación clara de responsabilidades"],
        "consecuencias_desfavorables": ["el dominio queda acoplado a la infraestructura"],
        "confirmacion": "Verificar que el dominio no importe de aplicación ni infraestructura.",
    }
    return SalidaSeleccion.model_validate(base | cambios)


def test_seleccion_valida_normaliza_identificadores():
    salida = validar_seleccion(salida_seleccion(), {"RF-01", "RF-02"}, ARQUITECTURAS)
    assert [o.id for o in salida.opciones] == ["ARQ-01", "ARQ-02"]


@pytest.mark.parametrize(
    ("cambios", "mensaje"),
    [
        ({"opciones": [opcion("ARQ-01", None)]}, "al menos dos"),
        ({"opciones": [opcion("ARQ-01", None), opcion("ARQ-09", "RF-01")]}, "no pertenecen"),
        ({"elegida": "ARQ-03"}, "debe estar entre las opciones"),
        (
            {"opciones": [opcion("ARQ-01", None), opcion("ARQ-02", "es sobreingeniería")]},
            "citando un requerimiento",
        ),
        ({"justificacion": "Es la más sencilla."}, "La justificación debe citar"),
        ({"justificacion": "Lo exigen RF-01 y RF-99."}, "no están aprobados: ['RF-99']"),
        ({"consecuencias_desfavorables": ["  "]}, "consecuencia desfavorable"),
        ({"confirmacion": ""}, "confirmación verificable"),
    ],
)
def test_reglas_de_la_seleccion(cambios, mensaje):
    with pytest.raises(ErrorValidacionSalida, match=re.escape(mensaje)):
        validar_seleccion(salida_seleccion(**cambios), {"RF-01", "RF-02"}, ARQUITECTURAS)


def test_registro_de_decision_con_la_estructura_madr():
    salida = validar_seleccion(salida_seleccion(), {"RF-01", "RF-02"}, ARQUITECTURAS)
    registro = registro_de_decision(salida, TITULOS, date(2026, 10, 9))
    assert registro.startswith("---\nestado: propuesta\nfecha: 2026-10-09\n")
    for seccion in (
        "# Registro de decisión · Arquitectura del módulo de avalúo",
        "## Contexto y planteamiento del problema",
        "## Factores de decisión",
        "## Opciones consideradas",
        "- ARQ-02 · Arquitectura hexagonal o de puertos y adaptadores",
        "Opción elegida: «ARQ-01 · Arquitectura en capas», porque RF-01 y RF-02",
        "- Desfavorable, porque el dominio queda acoplado a la infraestructura",
        "### Confirmación",
        "- Descartada, porque RF-01 tiene reglas simples",
    ):
        assert seccion in registro


# N8 · parametrización --------------------------------------------------------------------------


def salida_especificacion(**cambios) -> SalidaEspecificacion:
    base = {
        "modulos": [
            {
                "nombre": "dominio.avaluo",
                "ruta": "src/dominio/avaluo.py",
                "responsabilidad": "Cálculo del avalúo",
                "capa": "dominio",
                "interfaces_publicas": [
                    {
                        "nombre": "calcular_avaluo",
                        "tipo": "funcion",
                        "firma": "calcular_avaluo(numero_predial: str) -> Decimal",
                        "descripcion": "Calcula el avalúo total",
                        "excepciones": ["PredioInexistente"],
                    }
                ],
                "dependencias_permitidas": [],
                "requerimientos": ["RF-01"],
            },
            {
                "nombre": "aplicacion.liquidacion",
                "ruta": "src/aplicacion/liquidacion.py",
                "responsabilidad": "Liquidación del impuesto",
                "capa": "aplicacion",
                "interfaces_publicas": [
                    {
                        "nombre": "liquidar",
                        "tipo": "funcion",
                        "firma": "liquidar(numero_predial: str, vigencia: int) -> Decimal",
                        "descripcion": "Liquida el impuesto del periodo",
                        "excepciones": [],
                    }
                ],
                "dependencias_permitidas": ["dominio.avaluo"],
                "requerimientos": ["RF-02"],
            },
        ],
        "modelo_datos": [
            {
                "nombre": "Predio",
                "campos": [
                    {
                        "nombre": "numero_predial",
                        "tipo": "str",
                        "obligatorio": True,
                        "restriccion": " ",
                    },
                    {
                        "nombre": "avaluo_total",
                        "tipo": "Decimal",
                        "obligatorio": True,
                        "restriccion": None,
                    },
                ],
            }
        ],
        "dependencias_externas": [{"paquete": "pydantic", "proposito": "validar datos"}],
        "reglas_de_dependencia": ["La capa de dominio no importa de ninguna otra capa"],
    }
    return SalidaEspecificacion.model_validate(base | cambios)


def test_parametrizacion_asigna_los_campos_deterministas():
    especificacion = especificacion_desde_salida(
        salida_especificacion(), APROBADOS, "ARQ-01", "0.3"
    )
    assert (especificacion.id_especificacion, especificacion.version) == ("ED-01", "0.3")
    assert especificacion.arquitectura_base == "ARQ-01"
    assert especificacion.requerimientos_cubiertos == ["RF-01", "RF-02"]
    assert especificacion.modelo_datos[0].campos[0].restriccion is None


def test_parametrizacion_con_ciclo_se_rechaza():
    salida = salida_especificacion()
    salida.modulos[0].dependencias_permitidas = ["aplicacion.liquidacion"]
    with pytest.raises(ErrorValidacionSalida, match="Dependencias circulares"):
        especificacion_desde_salida(salida, APROBADOS, "ARQ-01", "0.1")


# Agente con el modelo falso --------------------------------------------------------------------


def agente(cliente, registro: RegistroEnMemoria | None = None) -> AgenteArquitecto:
    def invocador(nombre: str) -> InvocadorNodo:
        parametros = ParametrosNodo(
            nodo="N8", despliegue="gpt-5", esfuerzo="medium", max_tokens_salida=16000
        )
        return InvocadorNodo(
            cliente,
            parametros,
            cargar_prompt("arquitecto", nombre),
            registro or RegistroEnMemoria(),
            TARIFAS,
        )

    return AgenteArquitecto(
        RecuperadorFalso(), invocador("seleccion"), invocador("parametrizacion")
    )


def contexto_recuperado() -> Contexto:
    return recuperar_catalogo(RecuperadorFalso(), APROBADOS)


def test_los_prompts_del_arquitecto_estan_versionados():
    for nombre in ("seleccion", "parametrizacion"):
        prompt = cargar_prompt("arquitecto", nombre)
        assert prompt.metadatos.nodo == "N8"
        assert "problemas_intento_anterior" in prompt.texto


def test_primer_diseno_selecciona_y_parametriza(cliente_falso, completar_respuesta):
    cliente = cliente_falso(
        completar_respuesta(salida_seleccion(), modelo="gpt-5-2025-08-07"),
        completar_respuesta(salida_especificacion(), modelo="gpt-5-2025-08-07"),
    )
    registro = RegistroEnMemoria()
    diseno = agente(cliente, registro).disenar(APROBADOS, contexto_recuperado(), Arquitectura())
    assert diseno.especificacion.version == "0.1"
    assert diseno.especificacion.arquitectura_base == "ARQ-01"
    assert "Opción elegida: «ARQ-01 · Arquitectura en capas»" in diseno.registro_decision
    assert [llamada.prompt for llamada in registro.llamadas] == [
        cargar_prompt("arquitecto", "seleccion").identificador,
        cargar_prompt("arquitecto", "parametrizacion").identificador,
    ]
    assert registro.llamadas[0].costo_usd > 0


def diseno_previo(**cambios) -> Arquitectura:
    especificacion = especificacion_desde_salida(
        salida_especificacion(), APROBADOS, "ARQ-01", "0.1"
    )
    base = {
        "registro_decision": "# Registro previo",
        "especificacion": especificacion,
        "disenos": 1,
    }
    return Arquitectura(**(base | cambios))


def test_correccion_por_errores_de_validacion_solo_reparametriza(
    cliente_falso, completar_respuesta
):
    previa = diseno_previo(errores_validacion=("Validación 3 · catálogo: requests no pertenece",))
    cliente = cliente_falso(completar_respuesta(salida_especificacion(), modelo="gpt-5-2025-08-07"))
    diseno = agente(cliente).disenar(APROBADOS, contexto_recuperado(), previa)
    assert len(cliente.llamadas) == 1
    assert diseno.registro_decision == "# Registro previo"
    assert diseno.especificacion.version == "0.2"
    datos = json.loads(cliente.llamadas[0]["messages"][2]["content"])
    assert datos["correccion"]["errores_validacion"] == [
        "Validación 3 · catálogo: requests no pertenece"
    ]


def test_observacion_nueva_vuelve_a_seleccionar(cliente_falso, completar_respuesta):
    previa = diseno_previo(observaciones_revisor=("Usar arquitectura hexagonal",))
    cliente = cliente_falso(
        completar_respuesta(salida_seleccion(), modelo="gpt-5-2025-08-07"),
        completar_respuesta(salida_especificacion(), modelo="gpt-5-2025-08-07"),
    )
    agente(cliente).disenar(APROBADOS, contexto_recuperado(), previa)
    assert len(cliente.llamadas) == 2
    datos = json.loads(cliente.llamadas[0]["messages"][2]["content"])
    assert datos["observaciones_revisor"] == ["Usar arquitectura hexagonal"]
    assert datos["registro_previo"] == "# Registro previo"


def test_validar_aplica_el_anexo_b(cliente_falso):
    especificacion = especificacion_desde_salida(
        salida_especificacion(), APROBADOS, "ARQ-01", "0.1"
    )
    arquitecto = agente(cliente_falso())
    assert arquitecto.validar(especificacion, APROBADOS) == []
    solo_rf1 = Requerimientos(requerimientos=(RF1, requerimiento("RF-03", "consultar el avalúo")))
    assert "Validación 2 · cobertura: RF-03 no está asignado a ningún módulo" in arquitecto.validar(
        especificacion, solo_rf1
    )


def test_requerimientos_aprobados_llegan_a_una_especificacion_valida(
    cliente_falso, completar_respuesta
):
    cliente = cliente_falso(
        completar_respuesta(salida_seleccion(), modelo="gpt-5-2025-08-07"),
        completar_respuesta(salida_especificacion(), modelo="gpt-5-2025-08-07"),
    )
    simulados = ServiciosSimulados()
    sintesis = Sintesis(
        historias=APROBADOS.historias,
        requerimientos=APROBADOS.requerimientos,
        referencias={
            "RF-01": ("eli-003 v1.1 · Plantilla",),
            "RF-02": ("eli-003 v1.1 · Plantilla",),
        },
    )
    servicios = Servicios(
        elicitador=ElicitadorFijo(sintesis),
        arquitecto=agente(cliente),
        desarrollador=simulados,
        tester=simulados,
    )
    app = construir_grafo(servicios, ConfiguracionOrquestador(_env_file=None)).compile(
        checkpointer=InMemorySaver(serde=serializador())
    )
    id_sesion, avance = iniciar_sesion(app, "Realtix", "Catastro", "Liquidar el impuesto predial")
    assert avance.pausa.punto == "requerimientos"
    avance = avanzar(app, id_sesion, aprobar())
    assert avance.pausa.punto == "especificacion"
    assert avance.pausa.datos["errores"] == []
    assert avance.pausa.datos["especificacion"]["arquitectura_base"] == "ARQ-01"
    assert "Registro de decisión" in avance.pausa.datos["registro_decision"]

    # Un rechazo humano vuelve a seleccionar y parametrizar con la observación.
    cliente.pendientes += [
        completar_respuesta(salida_seleccion(), modelo="gpt-5-2025-08-07"),
        completar_respuesta(salida_especificacion(), modelo="gpt-5-2025-08-07"),
    ]
    avance = avanzar(app, id_sesion, rechazar("Separar la liquidación en su propio módulo"))
    assert avance.pausa.punto == "especificacion"
    arquitectura = app.get_state(configuracion_hilo(id_sesion)).values["arquitectura"]
    assert (arquitectura.disenos, arquitectura.observaciones_atendidas) == (2, 1)
    assert Nodo.N8 in avance.nodos
    assert len(cliente.llamadas) == 4
