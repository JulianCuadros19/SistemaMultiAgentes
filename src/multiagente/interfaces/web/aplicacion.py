"""Aplicación web: panel de operación del equipo y conversación del cliente (paso 12).

Rutas:
- `/`: sesiones guardadas y formulario de sesión nueva;
- `/sesiones/{id}`: estado de la sesión y la pausa pendiente con su formulario: diálogo, N6, N9
  o N17, con las pruebas propias de la persona (RF-38); en N17, el módulo se aprueba o se devuelve
  al desarrollador o al arquitecto;
- `/sesiones/{id}/cerrar`: cierra sin módulo validado una sesión en pausa o detenida;
- `/conversacion/{id}`: la vista del cliente, solo el diálogo y un estado en lenguaje de negocio;
- `/sesiones/{id}/trazabilidad` y `/sesiones/{id}/exportar.zip` (RF-33, RF-35);
- `/sesiones/{id}/estado.json`, que la página consulta mientras procesa.

Todo pasa por el `Operador`, como en la consola. Las plantillas escapan el contenido, incluido el
código generado. Sin recursos externos: funciona sin conexión (RF-37).
"""

import io
import uuid
import zipfile
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from multiagente.core.esquemas.especificacion_diseno import EspecificacionDiseno
from multiagente.core.esquemas.requerimiento import HistoriaUsuario, RequerimientoFormal
from multiagente.interfaces.documentos import ErrorExportacion, resumen_pruebas_propias
from multiagente.interfaces.operacion import (
    ACUSE_CONFIRMACION,
    NOMBRES_DE_NODO,
    ErrorOperacion,
    Operador,
    SesionEnCurso,
    VistaSesion,
    detalle_de_prueba,
    detalle_de_recoleccion,
    observaciones_de_pruebas,
)
from multiagente.interfaces.web.tareas import EjecutorDeTareas
from multiagente.orquestador.estado import Decision, Destino, Fase, PruebasPropias

CARPETA = Path(__file__).parent

REVISORES = {"requerimientos": "Analista", "especificacion": "Arquitecto", "final": "Revisor"}

PROCESOS = {
    ("requerimientos", Decision.APROBADO): "Diseñando la arquitectura (N7 y N8); tarda 1 o 2 min",
    ("requerimientos", Decision.RECHAZADO): "Volviendo al diálogo con sus observaciones",
    ("especificacion", Decision.APROBADO): (
        "Generando el módulo y validándolo (N10 a N14); puede tardar varios minutos"
    ),
    ("especificacion", Decision.RECHAZADO): "Rediseñando la arquitectura con sus observaciones",
    ("final", Decision.APROBADO): "Cerrando la sesión con el módulo validado",
    ("final", Decision.RECHAZADO): "Corrigiendo el módulo con sus observaciones y validándolo",
    ("final", Destino.ARQUITECTO): (
        "Rediseñando la arquitectura con sus observaciones (N8); después la revisa en N9"
    ),
}
"""Lo que hace el sistema tras cada decisión, para mostrarlo mientras procesa."""

PARA_EL_CLIENTE = {
    Fase.ELICITACION: "Gracias. El equipo está revisando los requerimientos que redactamos.",
    Fase.DISENO: "El equipo está diseñando la solución.",
    Fase.DESARROLLO: "El módulo está en construcción y validación.",
    Fase.APROBACION_FINAL: "El equipo está revisando el módulo terminado.",
    Fase.VALIDADO: "El módulo quedó validado. ¡Gracias por su tiempo!",
    Fase.REQUIERE_INTERVENCION: "El equipo revisará su caso personalmente.",
    Fase.CERRADA: "El equipo cerró esta sesión. Gracias por su tiempo.",
}
"""Estado de la sesión en el lenguaje del cliente, cuando no le toca responder (RNF-08)."""


def _redirigir(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=303)


def _ruta_de_prueba(nombre: str) -> str:
    nombre = Path(nombre.strip() or "propias.py").name
    if not nombre.endswith(".py"):
        nombre += ".py"
    return f"tests/{nombre if nombre.startswith('test_') else 'test_' + nombre}"


def crear_aplicacion(operador: Operador, tareas: EjecutorDeTareas | None = None) -> FastAPI:
    """Crea la aplicación web sobre un operador abierto.

    Args:
        operador: Operador del sistema.
        tareas: Ejecutor de los avances largos; si se omite, uno en segundo plano.

    Returns:
        La aplicación, lista para servirla con uvicorn.
    """
    tareas = tareas or EjecutorDeTareas()
    pruebas_por_sesion: dict[str, PruebasPropias] = {}
    aplicacion = FastAPI(
        title="Sistema multiagente · Realtix", docs_url=None, redoc_url=None, openapi_url=None
    )
    aplicacion.mount("/estaticos", StaticFiles(directory=CARPETA / "estaticos"), name="estaticos")
    plantillas = Jinja2Templates(directory=CARPETA / "plantillas")
    plantillas.env.globals["NOMBRES_DE_NODO"] = NOMBRES_DE_NODO
    plantillas.env.globals["resumen_pruebas_propias"] = resumen_pruebas_propias
    plantillas.env.globals["detalle_de_prueba"] = detalle_de_prueba
    plantillas.env.globals["detalle_de_recoleccion"] = detalle_de_recoleccion

    def pagina(
        request: Request, plantilla: str, estado: int = 200, **datos: object
    ) -> HTMLResponse:
        return plantillas.TemplateResponse(request, plantilla, datos, status_code=estado)

    @aplicacion.exception_handler(ErrorOperacion)
    def operacion_invalida(request: Request, error: ErrorOperacion) -> HTMLResponse:
        return pagina(request, "mensaje.html", 404, titulo="No se pudo", mensaje=str(error))

    @aplicacion.exception_handler(SesionEnCurso)
    def sesion_en_curso(request: Request, error: SesionEnCurso) -> HTMLResponse:
        return pagina(request, "mensaje.html", 409, titulo="Sesión en curso", mensaje=str(error))

    @aplicacion.exception_handler(ErrorExportacion)
    def exportacion_invalida(request: Request, error: ErrorExportacion) -> HTMLResponse:
        return pagina(
            request, "mensaje.html", 409, titulo="Sin módulo validado", mensaje=str(error)
        )

    # Panel de operación ---------------------------------------------------------------------

    def panel_con(request: Request, estado: int = 200, error: str | None = None) -> HTMLResponse:
        sesiones = operador.sesiones()
        en_curso = {vista.id_sesion: tareas.en_curso(vista.id_sesion) for vista in sesiones}
        return pagina(
            request, "panel.html", estado, sesiones=sesiones, en_curso=en_curso, error=error
        )

    @aplicacion.get("/", response_class=HTMLResponse)
    def panel(request: Request) -> HTMLResponse:
        """Sesiones guardadas y formulario de sesión nueva."""
        return panel_con(request)

    @aplicacion.post("/sesiones", response_model=None)
    def nueva_sesion(
        request: Request,
        cliente: Annotated[str, Form()] = "",
        proyecto: Annotated[str, Form()] = "",
        necesidad: Annotated[str, Form()] = "",
    ) -> HTMLResponse | RedirectResponse:
        """Abre una sesión con la necesidad del cliente; la primera pregunta se prepara aparte."""
        if not all(texto.strip() for texto in (cliente, proyecto, necesidad)):
            return panel_con(
                request, 400, "El cliente, el proyecto y la necesidad son obligatorios."
            )
        id_sesion = str(uuid.uuid4())
        tareas.lanzar(
            id_sesion,
            "Abriendo la sesión y preparando la primera pregunta",
            lambda: operador.iniciar(cliente, proyecto, necesidad, id_sesion),
        )
        return _redirigir(f"/sesiones/{id_sesion}")

    # Sesión ---------------------------------------------------------------------------------

    def datos_de_la_pausa(vista: VistaSesion) -> dict[str, Any]:
        pausa = vista.pausa
        if pausa is None:
            return {}
        datos = pausa.datos
        if pausa.punto == "requerimientos":
            return {
                "historias": [HistoriaUsuario.model_validate(h) for h in datos["historias"]],
                "requerimientos": [
                    RequerimientoFormal.model_validate(r) for r in datos["requerimientos"]
                ],
                "referencias": datos["referencias"],
                "defectos": datos["defectos"],
            }
        if pausa.punto == "especificacion":
            return {
                "registro_decision": datos["registro_decision"],
                "especificacion": (
                    EspecificacionDiseno.model_validate(datos["especificacion"])
                    if datos["especificacion"]
                    else None
                ),
                "errores": datos["errores"],
                "capacidades": datos.get("capacidades_no_cubiertas", []),
            }
        if pausa.punto == "final":
            estado = operador.estado(vista.id_sesion)
            pruebas = pruebas_por_sesion.get(vista.id_sesion)
            return {
                "escalado": datos.get("escalado", False),
                "version": estado["codigo"].vigente,
                "validacion": estado["validacion"],
                "pruebas": pruebas,
                "sugeridas": observaciones_de_pruebas(pruebas) if pruebas else "",
            }
        return {}

    @aplicacion.get("/sesiones/{id_sesion}", response_class=HTMLResponse)
    def sesion(request: Request, id_sesion: str) -> HTMLResponse:
        """Estado de la sesión y la pausa pendiente con su formulario."""
        tarea = tareas.en_curso(id_sesion)
        error = tareas.retirar_error(id_sesion)
        try:
            vista = operador.vista(id_sesion)
        except ErrorOperacion:
            if tarea is None and error is None:
                raise
            vista = None
        return pagina(
            request,
            "sesion.html",
            id_sesion=id_sesion,
            vista=vista,
            tarea=tarea,
            error=error,
            conversacion=operador.estado(id_sesion)["conversacion"] if vista else None,
            revisor=REVISORES.get(vista.pausa.punto, "") if vista and vista.pausa else "",
            **(datos_de_la_pausa(vista) if vista and tarea is None else {}),
        )

    @aplicacion.get("/conversacion/{id_sesion}", response_class=HTMLResponse)
    def conversacion(request: Request, id_sesion: str) -> HTMLResponse:
        """La vista del cliente: solo el diálogo y un estado en su lenguaje."""
        tarea = tareas.en_curso(id_sesion)
        error = tareas.retirar_error(id_sesion)
        vista = operador.vista(id_sesion)
        return pagina(
            request,
            "conversacion.html",
            id_sesion=id_sesion,
            vista=vista,
            tarea=tarea,
            error=error,
            turnos=operador.estado(id_sesion)["conversacion"].turnos,
            mensaje=PARA_EL_CLIENTE[vista.fase],
        )

    @aplicacion.get("/sesiones/{id_sesion}/estado.json")
    def estado_json(id_sesion: str) -> dict[str, Any]:
        """Estado breve de la sesión, que la página consulta mientras procesa."""
        tarea = tareas.en_curso(id_sesion)
        respuesta: dict[str, Any] = {
            "procesando": tarea is not None,
            "tarea": tarea.descripcion if tarea else None,
            "segundos": tarea.segundos if tarea else None,
        }
        try:
            vista = operador.vista(id_sesion)
        except ErrorOperacion:
            return respuesta | {"fase": None, "estado": None, "nodo": None}
        nodo = vista.pendientes[0] if vista.pendientes else None
        return respuesta | {
            "procesando": respuesta["procesando"] or vista.en_curso,
            "fase": vista.fase.value,
            "estado": vista.describir(),
            "nodo": NOMBRES_DE_NODO.get(nodo, nodo) if nodo else None,
        }

    # Acciones -------------------------------------------------------------------------------

    def vista_libre(id_sesion: str) -> VistaSesion:
        """Vista de la sesión para actuar sobre ella; rechaza la acción si está en curso."""
        vista = operador.vista(id_sesion)
        if vista.en_curso:
            raise SesionEnCurso(
                f"La sesión {id_sesion} está en curso: espere a que termine para actuar sobre ella."
            )
        return vista

    def volver(id_sesion: str, origen: str) -> RedirectResponse:
        if origen == "cliente":
            return _redirigir(f"/conversacion/{id_sesion}")
        return _redirigir(f"/sesiones/{id_sesion}")

    @aplicacion.post("/sesiones/{id_sesion}/respuesta")
    def responder(
        id_sesion: str,
        texto: Annotated[str, Form()] = "",
        origen: Annotated[str, Form()] = "operacion",
    ) -> RedirectResponse:
        """Entrega la respuesta del cliente; si confirma el resumen, lo acusa (RNF-08)."""
        vista = vista_libre(id_sesion)
        if texto.strip():
            descripcion = (
                ACUSE_CONFIRMACION
                if vista.confirma_resumen
                else "Procesando la respuesta y preparando la siguiente pregunta"
            )
            tareas.lanzar(id_sesion, descripcion, lambda: operador.responder(id_sesion, texto))
        return volver(id_sesion, origen)

    @aplicacion.post("/sesiones/{id_sesion}/decision")
    def decidir(
        id_sesion: str,
        decision: Annotated[Decision | None, Form()] = None,
        destino: Annotated[Destino | None, Form()] = None,
        revisor: Annotated[str, Form()] = "",
        observaciones: Annotated[str, Form()] = "",
        registrar_pruebas: Annotated[str, Form()] = "",
    ) -> RedirectResponse:
        """Registra la decisión del punto de control pendiente, con las pruebas propias en N17.

        En N17, devolver el módulo a un agente es rechazarlo con ese destino.
        """
        vista = vista_libre(id_sesion)
        punto = vista.pausa.punto if vista.pausa else ""
        if destino is not None:
            decision = Decision.RECHAZADO
        if decision is None:
            raise ErrorOperacion("Elija una decisión: aprobar o rechazar.")
        pruebas = (
            pruebas_por_sesion.get(id_sesion) if registrar_pruebas and punto == "final" else None
        )

        def accion() -> None:
            operador.decidir(
                id_sesion,
                decision,
                revisor.strip() or REVISORES.get(punto, "Revisor"),
                observaciones or None,
                pruebas,
                destino,
            )
            pruebas_por_sesion.pop(id_sesion, None)

        proceso = PROCESOS.get(
            (punto, destino if destino is Destino.ARQUITECTO else decision),
            "Procesando la decisión",
        )
        tareas.lanzar(id_sesion, proceso, accion)
        return volver(id_sesion, "operacion")

    @aplicacion.post("/sesiones/{id_sesion}/cerrar")
    def cerrar(
        id_sesion: str,
        motivo: Annotated[str, Form()] = "",
        revisor: Annotated[str, Form()] = "",
        confirmo: Annotated[str, Form()] = "",
    ) -> RedirectResponse:
        """Cierra sin módulo validado una sesión en pausa o detenida; queda en la trazabilidad."""
        vista = vista_libre(id_sesion)
        if vista.terminada:
            raise ErrorOperacion(f"La sesión {id_sesion} ya terminó: {vista.describir().lower()}.")
        if not motivo.strip() or not confirmo:
            raise ErrorOperacion("Para cerrar la sesión, escriba el motivo y confirme el cierre.")
        punto = vista.pausa.punto if vista.pausa else ""

        def accion() -> None:
            operador.cerrar(id_sesion, revisor.strip() or REVISORES.get(punto, "Analista"), motivo)
            pruebas_por_sesion.pop(id_sesion, None)

        tareas.lanzar(id_sesion, "Cerrando la sesión", accion)
        return volver(id_sesion, "operacion")

    @aplicacion.post("/sesiones/{id_sesion}/pruebas")
    def probar(
        id_sesion: str,
        nombre: Annotated[str, Form()] = "",
        contenido: Annotated[str, Form()] = "",
        archivo: Annotated[UploadFile | None, File()] = None,
    ) -> RedirectResponse:
        """Ejecuta las pruebas propias de la persona contra la versión vigente (RF-38)."""
        if archivo is not None and archivo.filename:
            nombre, contenido = archivo.filename, archivo.file.read().decode("utf-8")
        ruta = _ruta_de_prueba(nombre)

        def accion() -> None:
            pruebas_por_sesion[id_sesion] = operador.probar_propias(id_sesion, {ruta: contenido})

        if contenido.strip():
            tareas.lanzar(id_sesion, "Ejecutando sus pruebas en el entorno aislado", accion)
        return volver(id_sesion, "operacion")

    @aplicacion.post("/sesiones/{id_sesion}/reanudar")
    def reanudar(id_sesion: str) -> RedirectResponse:
        """Reanuda una sesión detenida desde su último punto de control (RF-28)."""
        vista_libre(id_sesion)
        tareas.lanzar(
            id_sesion,
            "Reanudando desde el último punto de control",
            lambda: operador.reanudar(id_sesion),
        )
        return volver(id_sesion, "operacion")

    # Consulta y exportación -----------------------------------------------------------------

    @aplicacion.get("/sesiones/{id_sesion}/trazabilidad", response_class=HTMLResponse)
    def trazabilidad(request: Request, id_sesion: str) -> HTMLResponse:
        """Cadena completa de artefactos de la sesión (RF-33)."""
        return pagina(
            request,
            "trazabilidad.html",
            id_sesion=id_sesion,
            documento=operador.trazabilidad(id_sesion),
        )

    @aplicacion.get("/sesiones/{id_sesion}/exportar.zip")
    def exportar(id_sesion: str) -> Response:
        """Paquete del módulo validado en un .zip (RF-35)."""
        paquete = operador.exportar(id_sesion)
        carpeta = f"modulo-{id_sesion[:8]}"
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as comprimido:
            for ruta, contenido in paquete.items():
                comprimido.writestr(f"{carpeta}/{ruta}", contenido)
        return Response(
            buffer.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{carpeta}.zip"'},
        )

    return aplicacion
