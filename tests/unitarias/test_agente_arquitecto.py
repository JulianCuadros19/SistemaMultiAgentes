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
    InterfazModelo,
    SalidaEspecificacion,
    especificacion_desde_salida,
)
from multiagente.agentes.arquitecto.recorridos import (
    anotar_escenarios,
    errores_de_recorridos,
    nombre_limpio,
    recorridos_desde_salida,
    sin_anotaciones,
)
from multiagente.agentes.arquitecto.seleccion import (
    SalidaSeleccion,
    con_revisiones,
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
        "respuesta_observaciones": "",
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


def test_con_observaciones_nuevas_la_seleccion_debe_responderlas():
    with pytest.raises(ErrorValidacionSalida, match="Responde a las observaciones nuevas"):
        validar_seleccion(salida_seleccion(), {"RF-01", "RF-02"}, ARQUITECTURAS, True)
    respondida = salida_seleccion(respuesta_observaciones="Se mantiene ARQ-01 porque RF-01…")
    assert validar_seleccion(respondida, {"RF-01", "RF-02"}, ARQUITECTURAS, True)


def test_registro_cambia_las_etiquetas_por_la_referencia_del_fragmento():
    salida = validar_seleccion(
        salida_seleccion(justificacion="RF-01 tiene lógica moderada (F1), según los criterios."),
        {"RF-01", "RF-02"},
        ARQUITECTURAS,
    )
    criterios = FragmentoContexto(
        documento_id="arq-003",
        version_documento="1.0",
        titulo="Criterios de selección › Paso 2",
        contenido="x",
        similitud=0.7,
    )
    registro = registro_de_decision(salida, TITULOS, date(2026, 10, 9), {"F1": criterios})
    assert "(arq-003 v1.0 · Criterios de selección › Paso 2)" in registro
    assert "(F1)" not in registro


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
        "capacidades_no_cubiertas": [],
        "recorridos": [
            recorrido("RF-01", "ESC-01", "calcular_avaluo"),
            recorrido("RF-01", "ESC-02", "calcular_avaluo"),
            recorrido("RF-02", "ESC-01", "liquidar"),
            recorrido("RF-02", "ESC-02", "liquidar"),
        ],
    }
    return SalidaEspecificacion.model_validate(base | cambios)


def recorrido(
    rf: str,
    esc: str,
    ejecutar: str,
    observar: list[str] | None = None,
    preparar: list[str] | None = None,
) -> dict:
    return {
        "id_requerimiento": rf,
        "id_escenario": esc,
        "preparar": preparar or [],
        "ejecutar": ejecutar,
        "observar": [ejecutar] if observar is None else observar,
    }


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


def test_las_capacidades_no_cubiertas_llegan_al_diseno(cliente_falso, completar_respuesta):
    # Regla 4 de arq-004: lo que el catálogo no cubre se registra, no se esconde ni se inventa.
    hueco = "RF-01 pide firmar documentos: el catálogo no tiene una librería de firma"
    cliente = cliente_falso(
        completar_respuesta(salida_seleccion(), modelo="gpt-5-2025-08-07"),
        completar_respuesta(
            salida_especificacion(capacidades_no_cubiertas=[f"  {hueco} ", " "]),
            modelo="gpt-5-2025-08-07",
        ),
    )
    diseno = agente(cliente).disenar(APROBADOS, contexto_recuperado(), Arquitectura())
    assert diseno.capacidades_no_cubiertas == (hueco,)
    assert "capacidades_no_cubiertas" not in diseno.especificacion.model_dump()


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
    respuesta = "Se mantiene ARQ-01: RF-01 y RF-02 no tienen adaptadores que aislar."
    cliente = cliente_falso(
        completar_respuesta(
            salida_seleccion(respuesta_observaciones=respuesta), modelo="gpt-5-2025-08-07"
        ),
        completar_respuesta(salida_especificacion(), modelo="gpt-5-2025-08-07"),
    )
    agente(cliente).disenar(APROBADOS, contexto_recuperado(), previa)
    assert len(cliente.llamadas) == 2
    datos = json.loads(cliente.llamadas[0]["messages"][2]["content"])
    assert datos["observaciones_revisor"] == ["Usar arquitectura hexagonal"]
    assert datos["observaciones_nuevas"] == ["Usar arquitectura hexagonal"]
    assert datos["registro_previo"] == "# Registro previo"


def test_el_rediseno_por_observaciones_registra_la_revision(cliente_falso, completar_respuesta):
    observacion = "Falta consultar el avalúo ya calculado"
    previa = diseno_previo(observaciones_revisor=(observacion,))
    respuesta = "Se mantiene ARQ-01 y el dominio expone la consulta del avalúo."
    con_consulta = salida_especificacion()
    con_consulta.modulos[0].interfaces_publicas.append(
        InterfazModelo(
            nombre="consultar_avaluo",
            tipo="funcion",
            firma="consultar_avaluo(numero_predial: str) -> Decimal",
            descripcion="Consulta el avalúo calculado",
            excepciones=[],
        )
    )
    cliente = cliente_falso(
        completar_respuesta(
            salida_seleccion(respuesta_observaciones=respuesta), modelo="gpt-5-2025-08-07"
        ),
        completar_respuesta(con_consulta, modelo="gpt-5-2025-08-07"),
    )
    diseno = agente(cliente).disenar(APROBADOS, contexto_recuperado(), previa)
    (revision,) = diseno.revisiones
    assert revision.startswith("### Revisión 1 · especificación 0.2\n")
    assert f"- «{observacion}»" in revision
    assert f"Respuesta: {respuesta}" in revision
    assert (
        "- Interfaz nueva en dominio.avaluo: `consultar_avaluo(numero_predial: str) -> Decimal`"
        in revision
    )
    assert diseno.registro_decision.endswith(f"\n## Revisiones\n\n{revision}")
    # La parametrización ve la revisión en curso con la respuesta, pero aún sin los cambios.
    datos = json.loads(cliente.llamadas[1]["messages"][2]["content"])
    assert datos["observaciones_nuevas"] == [observacion]
    assert f"Respuesta: {respuesta}" in datos["registro_decision"]
    assert "Cambios en la especificación" not in datos["registro_decision"]

    # Una corrección posterior por errores de N9 conserva el registro con su revisión.
    corregida = previa.model_copy(
        update={
            "registro_decision": diseno.registro_decision,
            "especificacion": diseno.especificacion,
            "recorridos": diseno.recorridos,
            "revisiones": diseno.revisiones,
            "observaciones_atendidas": 1,
            "disenos": 2,
            "errores_validacion": ("Validación 3 · catálogo: requests no pertenece",),
        }
    )
    cliente.pendientes.append(completar_respuesta(con_consulta, modelo="gpt-5-2025-08-07"))
    siguiente = agente(cliente).disenar(APROBADOS, contexto_recuperado(), corregida)
    assert siguiente.revisiones == diseno.revisiones
    assert siguiente.registro_decision == diseno.registro_decision
    correccion = json.loads(cliente.llamadas[2]["messages"][2]["content"])["correccion"]
    assert " · Escenarios: " not in json.dumps(correccion["especificacion_previa"])
    assert len(correccion["recorridos_previos"]) == 4


def test_con_revisiones_reemplaza_la_seccion_anterior():
    registro = "# Registro\n\nTexto.\n"
    con_una = con_revisiones(registro, ("### Revisión 1",))
    assert con_una == "# Registro\n\nTexto.\n\n## Revisiones\n\n### Revisión 1\n"
    assert con_revisiones(con_una, ("### Revisión 1",)) == con_una
    assert con_revisiones(con_una, ()) == registro


def test_validar_aplica_el_anexo_b_y_los_recorridos(cliente_falso):
    salida = salida_especificacion()
    especificacion = especificacion_desde_salida(salida, APROBADOS, "ARQ-01", "0.1")
    recorridos = recorridos_desde_salida(salida.recorridos)
    arquitecto = agente(cliente_falso())
    assert arquitecto.validar(especificacion, APROBADOS, recorridos) == []
    solo_rf1 = Requerimientos(requerimientos=(RF1, requerimiento("RF-03", "consultar el avalúo")))
    errores = arquitecto.validar(especificacion, solo_rf1, recorridos)
    assert "Validación 2 · cobertura: RF-03 no está asignado a ningún módulo" in errores
    assert any(e.startswith("Escenarios ejecutables: RF-03 ESC-01 no tiene") for e in errores)
    assert any("el recorrido de RF-02 ESC-01 no corresponde" in e for e in errores)


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
    assert avance.pausa.datos["capacidades_no_cubiertas"] == []
    assert "Registro de decisión" in avance.pausa.datos["registro_decision"]

    assert len(avance.pausa.datos["recorridos"]) == 4

    # Un rechazo humano vuelve a seleccionar y parametrizar con la observación.
    respondida = salida_seleccion(respuesta_observaciones="La liquidación ya tiene su módulo.")
    cliente.pendientes += [
        completar_respuesta(respondida, modelo="gpt-5-2025-08-07"),
        completar_respuesta(salida_especificacion(), modelo="gpt-5-2025-08-07"),
    ]
    avance = avanzar(app, id_sesion, rechazar("Separar la liquidación en su propio módulo"))
    assert avance.pausa.punto == "especificacion"
    arquitectura = app.get_state(configuracion_hilo(id_sesion)).values["arquitectura"]
    assert (arquitectura.disenos, arquitectura.observaciones_atendidas) == (2, 1)
    assert Nodo.N8 in avance.nodos
    assert len(cliente.llamadas) == 4
    (revision,) = arquitectura.revisiones
    assert "- Ninguno." in revision
    assert avance.pausa.datos["registro_decision"].endswith(f"## Revisiones\n\n{revision}")


# Recorridos de los escenarios -------------------------------------------------------------------


def especificacion_base(salida: SalidaEspecificacion | None = None):
    return especificacion_desde_salida(
        salida or salida_especificacion(), APROBADOS, "ARQ-01", "0.1"
    )


def errores_con(recorridos: list[dict], salida: SalidaEspecificacion | None = None) -> list[str]:
    salida = salida or salida_especificacion()
    return errores_de_recorridos(
        especificacion_base(salida),
        APROBADOS,
        recorridos_desde_salida(salida_especificacion(recorridos=recorridos).recorridos),
    )


def test_recorridos_completos_no_tienen_errores():
    salida = salida_especificacion()
    recorridos = recorridos_desde_salida(salida.recorridos)
    assert errores_de_recorridos(especificacion_base(salida), APROBADOS, recorridos) == []


def test_cada_escenario_aprobado_tiene_exactamente_un_recorrido():
    errores = errores_con(
        [
            recorrido("RF-01", "ESC-01", "calcular_avaluo"),
            recorrido("RF-01", "ESC-01", "calcular_avaluo"),
            recorrido("rf-01", " esc-02 ", "calcular_avaluo"),
            recorrido("RF-02", "ESC-01", "liquidar"),
            recorrido("RF-09", "ESC-01", "liquidar"),
        ]
    )
    assert errores[0] == "Escenarios ejecutables: RF-01 ESC-01 tiene 2 recorridos"
    assert errores[1].startswith("Escenarios ejecutables: RF-02 ESC-02 no tiene recorrido;")
    assert errores[2] == (
        "Escenarios ejecutables: el recorrido de RF-09 ESC-01 no corresponde a un escenario "
        "aprobado"
    )
    assert len(errores) == 3


def test_cada_nombre_es_una_interfaz_declarada():
    errores = errores_con(
        [
            # Al preparar vale una entidad del modelo de datos, que la prueba construye.
            recorrido("RF-01", "ESC-01", "`calcular_avaluo(numero_predial)`", preparar=["Predio"]),
            recorrido("RF-01", "ESC-02", "calcular_avaluo", observar=["Predio"]),
            recorrido("RF-02", "ESC-01", "liquidar_impuesto", observar=["liquidar"]),
            recorrido("RF-02", "ESC-02", "aplicacion.liquidacion.liquidar"),
        ]
    )
    assert errores == [
        "Escenarios ejecutables: RF-01 ESC-02: en observar, «Predio» es una entidad del modelo "
        "de datos, no una interfaz; nombra la interfaz que la entrega: la de ejecutar, si es lo "
        "que devuelve, o una de consulta",
        "Escenarios ejecutables: RF-02 ESC-01: en ejecutar, «liquidar_impuesto» no es una "
        "interfaz declarada; usa el nombre exacto de una interfaz pública de la especificación "
        "o declárala",
    ]


def test_un_nombre_repetido_en_dos_modulos_se_califica():
    salida = salida_especificacion()
    salida.modulos[0].interfaces_publicas.append(
        InterfazModelo(
            nombre="liquidar",
            tipo="funcion",
            firma="liquidar(numero_predial: str) -> Decimal",
            descripcion="Liquida en el dominio",
            excepciones=[],
        )
    )
    errores = errores_con(
        [
            recorrido("RF-01", "ESC-01", "calcular_avaluo"),
            recorrido("RF-01", "ESC-02", "calcular_avaluo"),
            recorrido("RF-02", "ESC-01", "liquidar"),
            recorrido("RF-02", "ESC-02", "aplicacion.liquidacion.liquidar"),
        ],
        salida,
    )
    assert errores == [
        "Escenarios ejecutables: RF-02 ESC-01: en ejecutar, «liquidar» está declarada en "
        "aplicacion.liquidacion, dominio.avaluo; califícala con su módulo (modulo.interfaz)",
        "Escenarios ejecutables: RF-02 ESC-01: en observar, «liquidar» está declarada en "
        "aplicacion.liquidacion, dominio.avaluo; califícala con su módulo (modulo.interfaz)",
    ]


def test_el_entonces_debe_poder_observarse():
    salida = salida_especificacion()
    salida.modulos[1].interfaces_publicas += [
        InterfazModelo(
            nombre="registrar_pago",
            tipo="funcion",
            firma="registrar_pago(numero_predial: str, valor: Decimal) -> None",
            descripcion="Registra el pago del impuesto",
            excepciones=[],
        ),
        InterfazModelo(
            nombre="consultar_pagos",
            tipo="funcion",
            firma="consultar_pagos(numero_predial: str) -> list[Decimal]",
            descripcion="Consulta los pagos registrados",
            excepciones=[],
        ),
    ]
    base = [
        recorrido("RF-01", "ESC-01", "calcular_avaluo"),
        recorrido("RF-01", "ESC-02", "calcular_avaluo"),
        recorrido("RF-02", "ESC-01", "liquidar"),
    ]
    assert errores_con([*base, recorrido("RF-02", "ESC-02", "registrar_pago")], salida) == [
        "Escenarios ejecutables: RF-02 ESC-02: solo observa con «registrar_pago», que no "
        "devuelve nada ni declara excepciones; nombra la interfaz de consulta que muestra el "
        "efecto del «entonces»"
    ]
    observado = recorrido("RF-02", "ESC-02", "registrar_pago", observar=["consultar_pagos"])
    assert errores_con([*base, observado], salida) == []


def test_los_nombres_se_limpian_de_argumentos_y_comillas():
    assert nombre_limpio(" `Bus().publicar(aviso)` ") == "Bus.publicar"
    assert nombre_limpio("registrar(f(x), y)") == "registrar"
    assert nombre_limpio("dominio.avaluo.calcular_avaluo.") == "dominio.avaluo.calcular_avaluo"


def test_las_interfaces_quedan_anotadas_con_sus_escenarios():
    salida = salida_especificacion(
        recorridos=[
            recorrido("RF-01", "ESC-01", "calcular_avaluo"),
            recorrido("RF-01", "ESC-02", "calcular_avaluo"),
            recorrido(
                "RF-02",
                "ESC-01",
                "liquidar",
                preparar=["Predio"],
                observar=["liquidar", "calcular_avaluo"],
            ),
            recorrido("RF-02", "ESC-02", "liquidar", observar=["calcular_avaluo"]),
        ]
    )
    especificacion = especificacion_base(salida)
    recorridos = recorridos_desde_salida(salida.recorridos)
    anotada = anotar_escenarios(especificacion, recorridos)
    descripciones = [i.descripcion for m in anotada.modulos for i in m.interfaces_publicas]
    assert descripciones == [
        "Calcula el avalúo total · Escenarios: RF-01 ESC-01 (ejecuta; observa su resultado), "
        "RF-01 ESC-02 (ejecuta; observa su resultado), RF-02 ESC-01 (observa), "
        "RF-02 ESC-02 (observa)",
        "Liquida el impuesto del periodo · Escenarios: RF-02 ESC-01 (ejecuta; prepara con "
        "Predio; observa su resultado y con calcular_avaluo), RF-02 ESC-02 (ejecuta; observa "
        "con calcular_avaluo)",
    ]
    assert anotar_escenarios(anotada, recorridos) == anotada
    assert sin_anotaciones(anotada) == especificacion


def test_sin_recorridos_completos_la_parametrizacion_se_reintenta(
    cliente_falso, completar_respuesta
):
    incompleta = salida_especificacion(recorridos=[recorrido("RF-01", "ESC-01", "calcular_avaluo")])
    cliente = cliente_falso(
        completar_respuesta(salida_seleccion(), modelo="gpt-5-2025-08-07"),
        completar_respuesta(incompleta, modelo="gpt-5-2025-08-07"),
        completar_respuesta(salida_especificacion(), modelo="gpt-5-2025-08-07"),
    )
    diseno = agente(cliente).disenar(APROBADOS, contexto_recuperado(), Arquitectura())
    assert len(cliente.llamadas) == 3
    problemas = json.loads(cliente.llamadas[2]["messages"][-1]["content"])
    assert any(
        p.startswith("Escenarios ejecutables: RF-02 ESC-01 no tiene recorrido")
        for p in problemas["problemas_intento_anterior"]
    )
    assert len(diseno.recorridos) == 4
    assert "recorridos" not in diseno.especificacion.model_dump()
    assert (
        diseno.especificacion.modulos[0]
        .interfaces_publicas[0]
        .descripcion.endswith(
            " · Escenarios: RF-01 ESC-01 (ejecuta; observa su resultado), "
            "RF-01 ESC-02 (ejecuta; observa su resultado)"
        )
    )


def salida_con_registro() -> SalidaEspecificacion:
    salida = salida_especificacion()
    salida.modulos[0].interfaces_publicas += [
        InterfazModelo(
            nombre="RegistroValores",
            tipo="clase",
            firma="RegistroValores()",
            descripcion="Valores unitarios registrados",
            excepciones=[],
        ),
        InterfazModelo(
            nombre="RegistroValores.registrar",
            tipo="funcion",
            firma="registrar(self, numero_predial: str, valor: Decimal) -> None",
            descripcion="Registra el valor unitario de un predio",
            excepciones=[],
        ),
        InterfazModelo(
            nombre="RegistroValores.consultar",
            tipo="funcion",
            firma="consultar(self, numero_predial: str) -> Decimal",
            descripcion="Consulta el valor unitario de un predio",
            excepciones=[],
        ),
    ]
    return salida


def test_los_recorridos_nombran_metodos():
    salida = salida_con_registro()
    recorridos = [
        recorrido(
            "RF-01",
            "ESC-01",
            "calcular_avaluo",
            preparar=["RegistroValores", "RegistroValores.registrar"],
        ),
        recorrido(
            "RF-01",
            "ESC-02",
            "calcular_avaluo",
            observar=["calcular_avaluo", "dominio.avaluo.RegistroValores.consultar"],
        ),
        # El nombre corto de un método vale si no es ambiguo.
        recorrido("RF-02", "ESC-01", "liquidar", preparar=["registrar"]),
        recorrido("RF-02", "ESC-02", "liquidar"),
    ]
    assert errores_con(recorridos, salida) == []
    anotada = anotar_escenarios(
        especificacion_base(salida),
        recorridos_desde_salida(salida_especificacion(recorridos=recorridos).recorridos),
    )
    registrar = next(
        i for i in anotada.modulos[0].interfaces_publicas if i.nombre == "RegistroValores.registrar"
    )
    assert registrar.descripcion.endswith(
        "· Escenarios: RF-01 ESC-01 (prepara), RF-02 ESC-01 (prepara)"
    )


def test_un_metodo_de_otra_clase_no_vale():
    errores = errores_con(
        [
            recorrido("RF-01", "ESC-01", "calcular_avaluo", preparar=["Predio.registrar"]),
            recorrido("RF-01", "ESC-02", "calcular_avaluo"),
            recorrido("RF-02", "ESC-01", "liquidar"),
            recorrido("RF-02", "ESC-02", "liquidar"),
        ],
        salida_con_registro(),
    )
    assert errores == [
        "Escenarios ejecutables: RF-01 ESC-01: en preparar, «Predio.registrar» no es una "
        "interfaz declarada ni una entidad del modelo de datos; usa el nombre exacto de una "
        "interfaz pública de la especificación o declárala"
    ]
