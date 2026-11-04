"""Interfaz web con TestClient, servicios simulados y un entorno aislado falso, sin costo."""

import io
import threading
import time
import zipfile

from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver

from multiagente.core.configuracion import ConfiguracionOrquestador
from multiagente.interfaces.operacion import Operador
from multiagente.interfaces.web.aplicacion import PARA_EL_CLIENTE, crear_aplicacion
from multiagente.interfaces.web.tareas import EjecutorDeTareas
from multiagente.orquestador.estado import Decision, Destino, Fase, PuntoControl, ResultadoPrueba
from multiagente.orquestador.grafo import construir_grafo
from multiagente.orquestador.simulacion import PREGUNTAS, ServiciosSimulados, guion_completo
from multiagente.persistencia.puntos_control import serializador


def web(simulacion: ServiciosSimulados, entorno, tareas=None) -> tuple[TestClient, Operador]:
    app = construir_grafo(
        simulacion.como_servicios(), ConfiguracionOrquestador(_env_file=None)
    ).compile(checkpointer=InMemorySaver(serde=serializador()))
    operador = Operador(app, entorno)
    aplicacion = crear_aplicacion(operador, tareas or EjecutorDeTareas(sincronico=True))
    return TestClient(aplicacion), operador


def abrir(cliente: TestClient, necesidad: str = "Registrar mutaciones") -> str:
    datos = {"cliente": "Oficina de catastro", "proyecto": "Gestión catastral"}
    respuesta = cliente.post(
        "/sesiones", data=datos | {"necesidad": necesidad}, follow_redirects=False
    )
    assert respuesta.status_code == 303
    return respuesta.headers["location"].rsplit("/", 1)[1]


def decidir(cliente: TestClient, id_sesion: str, decision: str, **datos: str) -> str:
    respuesta = cliente.post(f"/sesiones/{id_sesion}/decision", data={"decision": decision} | datos)
    assert respuesta.status_code == 200
    return respuesta.text


def test_el_equipo_y_el_cliente_operan_el_flujo_completo_por_la_web(entorno_falso):
    cliente, operador = web(ServiciosSimulados(fallos_veredicto=0), entorno_falso)
    assert "Nueva sesión" in cliente.get("/").text
    guion = guion_completo()
    id_sesion = abrir(cliente, guion.necesidad)
    assert PREGUNTAS["rol"] in cliente.get(f"/sesiones/{id_sesion}").text

    # El cliente responde en su vista; al confirmar el resumen, la sesión pasa al equipo.
    for respuesta in guion.respuestas_cliente[:7]:
        pagina = cliente.post(
            f"/sesiones/{id_sesion}/respuesta", data={"texto": respuesta, "origen": "cliente"}
        )
    assert PARA_EL_CLIENTE[Fase.ELICITACION] in pagina.text

    # N6: rechazo con observaciones, dos respuestas más y aprobación.
    assert "N6 · Requerimientos para aprobar" in cliente.get(f"/sesiones/{id_sesion}").text
    decidir(cliente, id_sesion, "rechazado", observaciones="Falta la regla de la fecha")
    for respuesta in guion.respuestas_cliente[7:]:
        cliente.post(f"/sesiones/{id_sesion}/respuesta", data={"texto": respuesta})
    decidir(cliente, id_sesion, "aprobado", revisor="Laura")

    # N9: rechazo y aprobación, con el recorrido de cada escenario a la vista.
    pagina = cliente.get(f"/sesiones/{id_sesion}").text
    assert "N9 · Especificación de diseño" in pagina
    assert "Recorridos de los escenarios" in pagina
    assert "<td>RF-01 ESC-01</td>" in pagina
    decidir(cliente, id_sesion, "rechazado", observaciones="Separar la validación")
    pagina = decidir(cliente, id_sesion, "aprobado")

    # N17: una prueba propia falla, sus observaciones se proponen y la persona rechaza.
    assert "N17 · Aprobación final · versión 1 del módulo" in pagina
    assert "El tester lo aprobó en la iteración 1 de 3" in pagina
    pagina = cliente.post(
        f"/sesiones/{id_sesion}/pruebas",
        data={"nombre": "radicado.py", "contenido": "def test_radicado_falla():\n    assert 0\n"},
    ).text
    assert "Resultado: 0 de 1 pasan" in pagina
    sugeridas = "La prueba propia tests/test_radicado.py::test_radicado_falla no pasa (fallo)"
    assert sugeridas in pagina
    assert "AssertionError: falta el año assert 2025 == 2026" in pagina
    decidir(cliente, id_sesion, "rechazado", observaciones=sugeridas, registrar_pruebas="si")

    # Versión 2: sube su archivo, pasa y aprueba registrando sus pruebas.
    assert "versión 2 del módulo" in cliente.get(f"/sesiones/{id_sesion}").text
    archivo = ("test_radicado.py", b"def test_radicado_con_anio():\n    assert 1\n", "text/plain")
    cliente.post(f"/sesiones/{id_sesion}/pruebas", files={"archivo": archivo})
    pagina = decidir(cliente, id_sesion, "aprobado", revisor="Julián", registrar_pruebas="si")
    assert "Módulo validado" in pagina

    aprobaciones = operador.estado(id_sesion)["sesion"].aprobaciones
    rechazo, aprobacion = [a for a in aprobaciones if a.punto is PuntoControl.FINAL]
    assert rechazo.decision is Decision.RECHAZADO
    assert rechazo.pruebas_propias.ejecucion.pruebas[0].resultado is ResultadoPrueba.FALLO
    assert aprobacion.revisor == "Julián"
    assert set(aprobacion.pruebas_propias.archivos) == {"tests/test_radicado.py"}

    # Consulta, sondeo, trazabilidad y exportación.
    assert cliente.get(f"/sesiones/{id_sesion}/estado.json").json() == {
        "procesando": False,
        "tarea": None,
        "segundos": None,
        "fase": "validado",
        "estado": "Módulo validado",
        "nodo": None,
    }
    assert (
        f"# Trazabilidad de la sesión {id_sesion}"
        in cliente.get(f"/sesiones/{id_sesion}/trazabilidad").text
    )
    paquete = cliente.get(f"/sesiones/{id_sesion}/exportar.zip")
    assert paquete.headers["content-type"] == "application/zip"
    nombres = zipfile.ZipFile(io.BytesIO(paquete.content)).namelist()
    assert f"modulo-{id_sesion[:8]}/requerimientos.json" in nombres
    assert f"modulo-{id_sesion[:8]}/codigo/src/simulado/modulo.py" in nombres
    assert PARA_EL_CLIENTE[Fase.VALIDADO] in cliente.get(f"/conversacion/{id_sesion}").text


def test_el_contenido_se_escapa(entorno_falso):
    cliente, _ = web(ServiciosSimulados(), entorno_falso)
    id_sesion = abrir(cliente)
    pagina = cliente.post(
        f"/sesiones/{id_sesion}/respuesta",
        data={"texto": "<script>alert('x')</script>", "origen": "cliente"},
    ).text
    assert "<script>alert" not in pagina
    assert "&lt;script&gt;alert" in pagina


def test_una_sesion_detenida_por_una_falla_se_reanuda_desde_la_pagina(entorno_falso):
    cliente, operador = web(
        ServiciosSimulados(fallos_veredicto=0, fallos_ejecucion=1), entorno_falso
    )
    guion = guion_completo()
    id_sesion = abrir(cliente, guion.necesidad)
    for respuesta in guion.respuestas_cliente[:7]:
        cliente.post(f"/sesiones/{id_sesion}/respuesta", data={"texto": respuesta})
    decidir(cliente, id_sesion, "aprobado")
    pagina = decidir(cliente, id_sesion, "aprobado")

    assert "La última acción no terminó." in pagina
    assert "ErrorSimulado" in pagina
    assert "Detenida antes de N11 · ejecución en el entorno aislado" in pagina
    assert 'action="/sesiones/' + id_sesion + '/reanudar"' in pagina
    assert 'action="/sesiones/' + id_sesion + '/cerrar"' in pagina

    pagina = cliente.post(f"/sesiones/{id_sesion}/reanudar").text
    assert "N17 · Aprobación final · versión 1 del módulo" in pagina
    assert operador.vista(id_sesion).fase is Fase.APROBACION_FINAL


def test_una_sesion_en_curso_en_otro_proceso_no_se_reanuda_desde_la_pagina(entorno_falso):
    cliente, operador = web(
        ServiciosSimulados(fallos_veredicto=0, fallos_ejecucion=1), entorno_falso
    )
    guion = guion_completo()
    id_sesion = abrir(cliente, guion.necesidad)
    for respuesta in guion.respuestas_cliente[:7]:
        cliente.post(f"/sesiones/{id_sesion}/respuesta", data={"texto": respuesta})
    decidir(cliente, id_sesion, "aprobado")
    decidir(cliente, id_sesion, "aprobado")

    with operador.bloqueos.exclusivo(id_sesion):
        pagina = cliente.get(f"/sesiones/{id_sesion}").text
        assert "En curso: N11 · ejecución en el entorno aislado" in pagina
        assert "Otro proceso la está avanzando" in pagina
        assert f'data-sesion="{id_sesion}"' in pagina
        assert 'action="/sesiones/' + id_sesion + '/reanudar"' not in pagina
        assert 'action="/sesiones/' + id_sesion + '/cerrar"' not in pagina
        assert cliente.get(f"/sesiones/{id_sesion}/estado.json").json()["procesando"]
        respuesta = cliente.post(f"/sesiones/{id_sesion}/reanudar")
        assert respuesta.status_code == 409
        assert "está en curso: espere a que termine" in respuesta.text

    assert not cliente.get(f"/sesiones/{id_sesion}/estado.json").json()["procesando"]
    assert operador.vista(id_sesion).detenida


def hasta_la_aprobacion_final(cliente: TestClient) -> str:
    guion = guion_completo()
    id_sesion = abrir(cliente, guion.necesidad)
    for respuesta in guion.respuestas_cliente[:7]:
        cliente.post(f"/sesiones/{id_sesion}/respuesta", data={"texto": respuesta})
    decidir(cliente, id_sesion, "aprobado")
    decidir(cliente, id_sesion, "aprobado")
    return id_sesion


def test_una_sesion_escalada_se_devuelve_al_arquitecto(entorno_falso):
    # El tester rechaza las tres versiones del ciclo: la sesión escala a N17.
    cliente, operador = web(ServiciosSimulados(fallos_veredicto=3), entorno_falso)
    id_sesion = hasta_la_aprobacion_final(cliente)
    pagina = cliente.get(f"/sesiones/{id_sesion}").text
    assert "La sesión escaló: tras 3 iteraciones" in pagina
    assert "El tester no aprobó el módulo y no puede aprobarse" in pagina
    assert 'value="aprobado"' not in pagina
    assert 'name="destino" value="arquitecto"' in pagina
    assert "Escalada: el tester no aprobó el módulo" in cliente.get("/").text
    assert (
        PARA_EL_CLIENTE[Fase.REQUIERE_INTERVENCION]
        in cliente.get(f"/conversacion/{id_sesion}").text
    )

    pagina = cliente.post(
        f"/sesiones/{id_sesion}/decision",
        data={"destino": "arquitecto", "observaciones": "Usar una arquitectura más simple"},
    ).text
    assert "N9 · Especificación de diseño" in pagina
    pagina = decidir(cliente, id_sesion, "aprobado")
    assert "El tester lo aprobó en la iteración 1 de 3" in pagina
    decidir(cliente, id_sesion, "aprobado")

    assert operador.vista(id_sesion).fase is Fase.VALIDADO
    finales = [
        (a.decision, a.destino)
        for a in operador.estado(id_sesion)["sesion"].aprobaciones
        if a.punto is PuntoControl.FINAL
    ]
    assert finales == [(Decision.RECHAZADO, Destino.ARQUITECTO), (Decision.APROBADO, None)]


class TareasQueAnotan(EjecutorDeTareas):
    """Ejecutor sincrónico que anota lo que muestra mientras procesa cada decisión."""

    def __init__(self) -> None:
        super().__init__(sincronico=True)
        self.descripciones: list[str] = []

    def lanzar(self, id_sesion, descripcion, accion):
        self.descripciones.append(descripcion)
        return super().lanzar(id_sesion, descripcion, accion)


def test_en_n17_se_piden_enmiendas_que_el_analista_revisa_en_n6(entorno_falso):
    tareas = TareasQueAnotan()
    cliente, operador = web(ServiciosSimulados(fallos_veredicto=0), entorno_falso, tareas)
    id_sesion = hasta_la_aprobacion_final(cliente)
    pagina = cliente.get(f"/sesiones/{id_sesion}").text
    assert 'name="destino" value="requerimientos"' in pagina
    assert "Enmendar los requerimientos" in pagina
    assert "pida una enmienda" in pagina

    regla = "El radicado debe incluir el año <de la solicitud>"
    pagina = cliente.post(
        f"/sesiones/{id_sesion}/decision",
        data={"destino": "requerimientos", "observaciones": regla, "revisor": "Laura"},
    ).text
    assert tareas.descripciones[-1].startswith("Enmendando los requerimientos con su regla (N5)")
    assert "N6 · Requerimientos para aprobar" in pagina
    assert "Enmienda pedida en la aprobación final</strong> por Laura" in pagina
    assert "El radicado debe incluir el año &lt;de la solicitud&gt;" in pagina
    assert "Requerimientos enmendados:\n      RF-01 v0.2." in pagina
    assert "RF-01 · versión 0.2 · enmendado desde N17" in pagina

    pagina = decidir(cliente, id_sesion, "rechazado", observaciones="Falta el año inválido")
    assert tareas.descripciones[-1] == "Rehaciendo la enmienda con sus observaciones (N5)"
    assert "Observación anterior del analista: Falta el año inválido" in pagina
    pagina = decidir(cliente, id_sesion, "aprobado")
    assert tareas.descripciones[-1].startswith("Corrigiendo el módulo con la enmienda")
    assert "N17 · Aprobación final · versión 2 del módulo" in pagina

    trazabilidad = cliente.get(f"/sesiones/{id_sesion}/trazabilidad").text
    assert "Enmiendas" in trazabilidad and "aprobada · enmienda RF-01 v0.3" in trazabilidad
    decidir(cliente, id_sesion, "aprobado")
    exportado = zipfile.ZipFile(
        io.BytesIO(cliente.get(f"/sesiones/{id_sesion}/exportar.zip").content)
    )
    carpeta = f"modulo-{id_sesion[:8]}"
    requerimientos = exportado.read(f"{carpeta}/requerimientos.md").decode("utf-8")
    assert "## RF-01 · versión 0.3\n\n- v0.3 · enmendado desde N17 por Laura el " in requerimientos


def test_la_especificacion_con_errores_no_ofrece_aprobar(entorno_falso):
    cliente, _ = web(ServiciosSimulados(errores_validacion=99), entorno_falso)
    guion = guion_completo()
    id_sesion = abrir(cliente, guion.necesidad)
    for respuesta in guion.respuestas_cliente[:7]:
        cliente.post(f"/sesiones/{id_sesion}/respuesta", data={"texto": respuesta})
    pagina = decidir(cliente, id_sesion, "aprobado")
    assert "N9 · Especificación de diseño" in pagina
    assert "La especificación no pasa las validaciones de N9 y no puede aprobarse" in pagina
    assert 'value="aprobado"' not in pagina


def test_se_cierra_una_sesion_desde_la_pagina(entorno_falso):
    cliente, operador = web(ServiciosSimulados(), entorno_falso)
    id_sesion = abrir(cliente)
    pagina = cliente.get(f"/sesiones/{id_sesion}").text
    assert 'action="/sesiones/' + id_sesion + '/cerrar"' in pagina

    # Sin confirmar, no se cierra.
    respuesta = cliente.post(f"/sesiones/{id_sesion}/cerrar", data={"motivo": "Desistió"})
    assert "confirme el cierre" in respuesta.text
    assert operador.vista(id_sesion).pausa.punto == "dialogo"

    datos = {"motivo": "El cliente desistió", "revisor": "Laura", "confirmo": "si"}
    pagina = cliente.post(f"/sesiones/{id_sesion}/cerrar", data=datos).text
    assert "La sesión se cerró sin módulo validado" in pagina
    assert operador.vista(id_sesion).fase is Fase.CERRADA
    assert operador.estado(id_sesion)["sesion"].cierre.revisor == "Laura"
    assert "Cerrada por Laura" in cliente.get(f"/sesiones/{id_sesion}/trazabilidad").text
    assert PARA_EL_CLIENTE[Fase.CERRADA] in cliente.get(f"/conversacion/{id_sesion}").text
    assert "ya terminó" in cliente.post(f"/sesiones/{id_sesion}/cerrar", data=datos).text


def test_errores_de_operacion_y_de_exportacion(entorno_falso):
    cliente, _ = web(ServiciosSimulados(), entorno_falso)
    assert cliente.get("/sesiones/no-existe").status_code == 404
    respuesta = cliente.post("/sesiones", data={"cliente": "x", "proyecto": "", "necesidad": ""})
    assert respuesta.status_code == 400
    assert "son obligatorios" in respuesta.text
    id_sesion = abrir(cliente)
    respuesta = cliente.get(f"/sesiones/{id_sesion}/exportar.zip")
    assert respuesta.status_code == 409
    assert "Solo se exporta un módulo validado" in respuesta.text
    # Una decisión fuera de un punto de control no avanza la sesión y se informa.
    pagina = decidir(cliente, id_sesion, "aprobado")
    assert "no espera requerimientos" in pagina
    assert PREGUNTAS["rol"] in pagina


def test_muestra_el_proceso_en_curso_y_rechaza_envios_dobles(entorno_falso):
    liberar = threading.Event()
    tareas = EjecutorDeTareas()
    cliente, _ = web(ServiciosSimulados(), entorno_falso, tareas)
    id_sesion = abrir(cliente)
    while tareas.en_curso(id_sesion):
        time.sleep(0.01)

    lanzada = tareas.lanzar(id_sesion, "Generando el módulo", liberar.wait)
    assert lanzada and not tareas.lanzar(id_sesion, "Otra", lambda: None)
    pagina = cliente.get(f"/sesiones/{id_sesion}").text
    assert f'data-sesion="{id_sesion}"' in pagina and "Generando el módulo" in pagina
    estado = cliente.get(f"/sesiones/{id_sesion}/estado.json").json()
    assert estado["procesando"] and estado["tarea"] == "Generando el módulo"

    liberar.set()
    while tareas.en_curso(id_sesion):
        time.sleep(0.01)
    assert not cliente.get(f"/sesiones/{id_sesion}/estado.json").json()["procesando"]


def test_el_ejecutor_guarda_el_error_y_lo_muestra_una_vez():
    tareas = EjecutorDeTareas(sincronico=True)

    def fallar() -> None:
        raise RuntimeError("sin conexión con el modelo")

    assert tareas.lanzar("s", "Generando", fallar)
    assert tareas.en_curso("s") is None
    assert tareas.retirar_error("s") == "RuntimeError: sin conexión con el modelo"
    assert tareas.retirar_error("s") is None
