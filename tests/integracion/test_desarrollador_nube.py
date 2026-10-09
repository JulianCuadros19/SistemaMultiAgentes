"""Condición de terminado del paso 9: el código generado se importa y cubre las interfaces.

Para cada caso de `evaluacion/casos/desarrollo-*.json`, un elicitador y un arquitecto fijos
entregan los requerimientos y la especificación aprobados, y el desarrollador real (Azure OpenAI
en N10) genera el módulo hasta la aprobación final. La primera versión debe:
- pasar la verificación estructural, que exige los archivos declarados y las interfaces con sus
  firmas;
- importar cada módulo declarado sin error en el entorno aislado.

Las pruebas del módulo y el estilo se informan, pero los dictamina el tester (paso 10).

Cuesta dinero y requiere el archivo .env, Docker y la imagen del entorno aislado:
`pytest -m "nube and sandbox" tests/integracion/test_desarrollador_nube.py`.
"""

import logging
from collections import Counter
from decimal import Decimal

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from multiagente.agentes.desarrollador.servicio import crear_agente_desarrollador
from multiagente.agentes.desarrollador.verificacion import verificar_version
from multiagente.core.configuracion import ConfiguracionAzureOpenAI, ConfiguracionOrquestador
from multiagente.core.estilo import hallazgos_de_estilo
from multiagente.interfaces.casos import cargar_caso_desarrollo
from multiagente.interfaces.cliente_simulado import RAIZ_EVALUACION
from multiagente.llm.cliente import crear_cliente
from multiagente.llm.traza import RegistroEnMemoria
from multiagente.orquestador.ejecucion import avanzar, configuracion_hilo, iniciar_sesion
from multiagente.orquestador.grafo import construir_grafo
from multiagente.orquestador.servicios import Servicios
from multiagente.orquestador.simulacion import (
    ArquitectoFijo,
    ElicitadorFijo,
    ServiciosSimulados,
    aprobar,
)
from multiagente.persistencia.puntos_control import serializador

pytestmark = [pytest.mark.nube, pytest.mark.sandbox]

CASOS = sorted((RAIZ_EVALUACION / "casos").glob("desarrollo-*.json"))


@pytest.mark.parametrize("archivo", CASOS, ids=[caso.stem for caso in CASOS])
def test_el_codigo_generado_se_importa_y_cubre_las_interfaces(entorno_aislado, archivo, caplog):
    caplog.set_level(logging.WARNING, logger="multiagente.llm.invocador")
    caso = cargar_caso_desarrollo(archivo)
    registro = RegistroEnMemoria()
    simulados = ServiciosSimulados(fallos_veredicto=0)
    servicios = Servicios(
        elicitador=ElicitadorFijo(caso.sintesis),
        arquitecto=ArquitectoFijo(caso.diseno),
        desarrollador=crear_agente_desarrollador(
            registro, crear_cliente(ConfiguracionAzureOpenAI())
        ),
        tester=simulados,
    )
    app = construir_grafo(servicios, ConfiguracionOrquestador(_env_file=None)).compile(
        checkpointer=InMemorySaver(serde=serializador())
    )
    id_sesion, _ = iniciar_sesion(app, caso.cliente, caso.proyecto, caso.necesidad)
    avanzar(app, id_sesion, aprobar())
    avance = avanzar(app, id_sesion, aprobar())

    estado = app.get_state(configuracion_hilo(id_sesion)).values
    version = estado["codigo"].vigente
    especificacion = caso.especificacion
    modulos = [modulo.nombre for modulo in especificacion.modulos]
    importacion = entorno_aislado.importar(version.archivos, modulos)
    pruebas = entorno_aislado.probar(version.archivos, tiempo_limite_s=120)
    estilo = Counter(hallazgo.codigo for hallazgo in hallazgos_de_estilo(version.archivos))
    for llamada in registro.llamadas:
        print(
            f"\nN10 {llamada.latencia_ms / 1000:6.1f} s · entrada {llamada.consumo.entrada} · "
            f"salida {llamada.consumo.salida} (razonamiento {llamada.consumo.razonamiento}) · "
            f"USD {llamada.costo_usd:.4f}{' · ' + llamada.error if llamada.error else ''}"
        )
    for rechazo in caplog.messages:
        print(f"Reintento: {rechazo[:600]}")
    costo = sum((llamada.costo_usd for llamada in registro.llamadas), Decimal(0))
    resumen_pruebas = dict(Counter(prueba.resultado for prueba in pruebas.pruebas))
    print(
        f"{caso.id}: {len(modulos)} módulos · {len(version.archivos)} archivos · "
        f"{len(registro.llamadas)} llamadas · USD {costo:.4f} · pruebas: {resumen_pruebas} · "
        f"estilo: {sum(estilo.values())} {dict(estilo)}"
    )

    # Llega a la aprobación final con la primera versión.
    assert avance.pausa is not None and avance.pausa.punto == "final"
    assert version.numero == 1

    # Cubre las interfaces de la especificación: archivos, firmas, dependencias y pruebas.
    assert verificar_version(version.archivos, especificacion, estado["requerimientos"]) == []

    # Se importa sin error, en el entorno aislado (RNF-03).
    assert importacion.errores == {}, importacion.errores
    assert importacion.exito
