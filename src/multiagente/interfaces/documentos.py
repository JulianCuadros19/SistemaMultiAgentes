"""Documentos legibles de los artefactos de una sesión, en Markdown (RF-33, RF-35).

Son funciones puras sobre los modelos del estado: la consola las imprime y la exportación las
escribe junto con los mismos artefactos en JSON validado contra esquema (requerimientos, §6).
"""

import json
from collections import Counter
from collections.abc import Mapping, Sequence

from multiagente.core.esquemas.especificacion_diseno import EspecificacionDiseno
from multiagente.core.esquemas.requerimiento import HistoriaUsuario, RequerimientoFormal
from multiagente.orquestador.estado import (
    Emisor,
    EstadoGrafo,
    Fase,
    PruebasPropias,
    ResultadoPrueba,
    Severidad,
    Validacion,
    VersionCodigo,
)


class ErrorExportacion(ValueError):
    """La sesión no tiene un módulo validado que exportar."""


def _celda(texto: str | None) -> str:
    return (texto or "—").replace("|", "\\|").replace("\n", " ")


def _enunciado(como: str, quiero: str, para: str) -> str:
    return f"Como {como}, quiero {quiero}, para {para}."


def requerimientos_md(
    historias: Sequence[HistoriaUsuario],
    requerimientos: Sequence[RequerimientoFormal],
    referencias: Mapping[str, Sequence[str]] | None = None,
) -> str:
    """Documento de las historias y los requerimientos formales en el formato del Anexo A.

    Args:
        historias: Backlog de historias de usuario (Tabla 27).
        requerimientos: Requerimientos formales (Tabla 28).
        referencias: Fragmentos de contexto que sustentan cada requerimiento (RF-04).

    Returns:
        El documento en Markdown.
    """
    lineas = [
        "# Requerimientos",
        "",
        "## Backlog de historias de usuario",
        "",
        "| No. | COMO | QUIERO | PARA | Prioridad |",
        "|---|---|---|---|---|",
    ]
    for historia in historias:
        enunciado = historia.enunciado
        lineas.append(
            f"| {historia.id} | {_celda(enunciado.como)} | {_celda(enunciado.quiero)} | "
            f"{_celda(enunciado.para)} | {_celda(historia.prioridad)} |"
        )
    notas = [
        f"- {historia.id} · {tipo}: {texto}"
        for historia in historias
        for tipo, textos in (
            ("Supuesto", historia.supuestos),
            ("Pregunta abierta", historia.preguntas_abiertas),
        )
        for texto in textos
    ]
    if notas:
        lineas += ["", *notas]
    for requerimiento in requerimientos:
        descripcion = requerimiento.descripcion
        titulo = requerimiento.titulo
        entradas = "; ".join(
            f"{dato.nombre} ({dato.tipo}, {'obligatorio' if dato.obligatorio else 'opcional'}"
            f"{f', {dato.restriccion}' if dato.restriccion else ''})"
            for dato in descripcion.datos_entrada
        )
        salidas = "; ".join(
            f"{dato.nombre} ({dato.tipo}{f', {dato.formato}' if dato.formato else ''})"
            for dato in descripcion.datos_salida
        )
        lineas += [
            "",
            f"## {requerimiento.id_requerimiento} · versión {requerimiento.version}",
            "",
            "| Campo | Contenido |",
            "|---|---|",
            f"| Proyecto | {_celda(requerimiento.proyecto)} |",
            f"| Tipo de solicitud | {requerimiento.tipo_solicitud} |",
            f"| Impacto de la solicitud | {requerimiento.impacto} |",
            f"| Módulo | {_celda(requerimiento.modulo)} |",
            f"| Riesgo | {_celda(requerimiento.riesgo)} |",
            f"| Autor | {_celda(requerimiento.autor)} |",
            f"| Área funcional | {_celda(requerimiento.area_funcional)} |",
            f"| Funcional responsable | {_celda(requerimiento.funcional_responsable)} |",
            f"| Título | {_celda(_enunciado(titulo.como, titulo.quiero, titulo.para))} |",
            f"| Precondición | {_celda(descripcion.precondicion)} |",
            f"| Regla de negocio | {_celda(descripcion.regla_negocio)} |",
            f"| Datos de entrada | {_celda(entradas)} |",
            f"| Datos de salida | {_celda(salidas)} |",
        ]
        lineas += [
            f"| {escenario.id}{f' · {escenario.nombre}' if escenario.nombre else ''} | "
            f"{_celda(f'DADO QUE {escenario.dado_que}, CUANDO {escenario.cuando}, ')}"
            f"{_celda(f'ENTONCES {escenario.entonces}')} |"
            for escenario in requerimiento.criterios_aceptacion
        ]
        relacionados = ", ".join(requerimiento.requerimientos_relacionados)
        lineas += [
            f"| Prioridad | {requerimiento.prioridad} |",
            f"| Requerimiento relacionado | {_celda(relacionados)} |",
        ]
        fuentes = (referencias or {}).get(requerimiento.id_requerimiento, ())
        if fuentes:
            lineas += ["", "Fuentes del contexto recuperado:", *(f"- {f}" for f in fuentes)]
    return "\n".join(lineas) + "\n"


def especificacion_md(especificacion: EspecificacionDiseno) -> str:
    """Documento de la especificación de diseño en el formato del Anexo B.

    Args:
        especificacion: Especificación de diseño.

    Returns:
        El documento en Markdown.
    """
    lineas = [
        f"# Especificación de diseño {especificacion.id_especificacion} · versión "
        f"{especificacion.version}",
        "",
        f"- Arquitectura base: {especificacion.arquitectura_base}",
        f"- Requerimientos cubiertos: {', '.join(especificacion.requerimientos_cubiertos)}",
        "",
        "## Módulos",
    ]
    for modulo in especificacion.modulos:
        dependencias = ", ".join(modulo.dependencias_permitidas) or "ninguna"
        lineas += [
            "",
            f"### {modulo.nombre}",
            "",
            f"- Ruta: `{modulo.ruta}` · capa {modulo.capa}",
            f"- Responsabilidad: {modulo.responsabilidad}",
            f"- Requerimientos: {', '.join(modulo.requerimientos)}",
            f"- Puede importar: {dependencias}",
            "",
            "| Interfaz | Tipo | Firma | Descripción | Excepciones |",
            "|---|---|---|---|---|",
        ]
        lineas += [
            f"| {interfaz.nombre} | {interfaz.tipo} | `{_celda(interfaz.firma)}` | "
            f"{_celda(interfaz.descripcion)} | {_celda(', '.join(interfaz.excepciones))} |"
            for interfaz in modulo.interfaces_publicas
        ]
    lineas += ["", "## Modelo de datos"]
    for entidad in especificacion.modelo_datos:
        lineas += [
            "",
            f"### {entidad.nombre}",
            "",
            "| Campo | Tipo | Obligatorio | Restricción |",
            "|---|---|---|---|",
        ]
        lineas += [
            f"| {campo.nombre} | `{_celda(campo.tipo)}` | {'sí' if campo.obligatorio else 'no'} | "
            f"{_celda(campo.restriccion)} |"
            for campo in entidad.campos
        ]
    lineas += ["", "## Dependencias externas", ""]
    lineas += [
        f"- {dependencia.paquete}: {dependencia.proposito}"
        for dependencia in especificacion.dependencias_externas
    ] or ["Ninguna."]
    lineas += ["", "## Reglas de dependencia", ""]
    lineas += [f"- {regla}" for regla in especificacion.reglas_de_dependencia] or ["Ninguna."]
    return "\n".join(lineas) + "\n"


def resumen_pruebas_propias(pruebas: PruebasPropias) -> str:
    """Una línea con el resultado de las pruebas propias, como `3 de 4 pasan`."""
    resultados = pruebas.ejecucion.pruebas
    pasan = sum(prueba.resultado is ResultadoPrueba.PASO for prueba in resultados)
    errores = len(pruebas.ejecucion.errores_recoleccion)
    return f"{pasan} de {len(resultados)} pasan" + (
        f", {errores} archivos sin recolectar" if errores else ""
    )


def _resumen_validacion(validacion: Validacion) -> str:
    severidades = Counter(hallazgo.severidad for hallazgo in validacion.hallazgos)
    cumplidos = sum(veredicto.cumple for veredicto in validacion.veredictos)
    return (
        f"{validacion.veredicto or 'sin veredicto'} · {cumplidos} de "
        f"{len(validacion.plan_pruebas)} casos · hallazgos alta {severidades[Severidad.ALTA]}, "
        f"media {severidades[Severidad.MEDIA]}, baja {severidades[Severidad.BAJA]}"
    )


def trazabilidad_md(
    estado: EstadoGrafo, historial: Sequence[tuple[VersionCodigo, Validacion]]
) -> str:
    """Cadena completa de artefactos de una sesión (RF-33).

    Args:
        estado: Estado vigente de la sesión.
        historial: Cada versión del módulo con su validación (`ejecucion.validaciones`).

    Returns:
        El documento en Markdown.
    """
    sesion = estado["sesion"]
    control = estado["control"]
    lineas = [
        f"# Trazabilidad de la sesión {sesion.id_sesion}",
        "",
        f"- Cliente: {sesion.cliente} · proyecto: {sesion.proyecto}",
        f"- Abierta el {sesion.creada:%Y-%m-%d %H:%M} UTC · fase: {sesion.fase}",
        f"- Iteraciones del ciclo de corrección: {control.iteracion} de "
        f"{control.limite_iteraciones}",
        *(
            [
                f"- Cerrada por {sesion.cierre.revisor} el {sesion.cierre.fecha:%Y-%m-%d %H:%M} "
                f"UTC ({sesion.cierre.desde}): {sesion.cierre.motivo}"
            ]
            if sesion.cierre
            else []
        ),
        "",
        "## Conversación",
        "",
    ]
    lineas += [
        f"- **{'Cliente' if turno.emisor is Emisor.CLIENTE else 'Elicitador'}:** "
        f"{turno.texto.replace(chr(10), ' ')}"
        for turno in estado["conversacion"].turnos
    ]
    lineas += [
        "",
        "## Decisiones humanas",
        "",
        "| Punto | Decisión | Revisor | Fecha | Observaciones | Pruebas propias |",
        "|---|---|---|---|---|---|",
    ]
    lineas += [
        f"| {a.punto} | {a.decision} | {_celda(a.revisor)} | {a.fecha:%Y-%m-%d %H:%M} | "
        f"{_celda(a.observaciones)} | "
        f"{resumen_pruebas_propias(a.pruebas_propias) if a.pruebas_propias else '—'} |"
        for a in sesion.aprobaciones
    ]
    requerimientos = estado["requerimientos"]
    lineas += ["", "## Requerimientos", ""]
    lineas += [
        f"- {r.id_requerimiento} v{r.version}: "
        f"{_enunciado(r.titulo.como, r.titulo.quiero, r.titulo.para)}"
        for r in requerimientos.requerimientos
    ] or ["Aún no hay requerimientos."]
    especificacion = estado["arquitectura"].especificacion
    lineas += ["", "## Arquitectura", ""]
    lineas.append(
        f"- {especificacion.id_especificacion} v{especificacion.version} · "
        f"{especificacion.arquitectura_base} · {len(especificacion.modulos)} módulos"
        if especificacion
        else "Aún no hay especificación."
    )
    lineas += ["", "## Versiones del módulo", ""]
    for version, validacion in historial:
        lineas.append(
            f"- Versión {version.numero} · {len(version.archivos)} archivos · "
            f"{_resumen_validacion(validacion)}"
        )
        lineas += [f"  - Atiende: {defecto}" for defecto in version.defectos_atendidos]
    if not historial:
        lineas.append("Aún no hay versiones dictaminadas.")
    return "\n".join(lineas) + "\n"


def _registro_con_preguntas(registro: str, capacidades: Sequence[str]) -> str:
    """Registro de decisión con las capacidades no cubiertas como preguntas abiertas (arq-004)."""
    texto = registro.rstrip() + "\n"
    if capacidades:
        texto += "\n## Preguntas abiertas\n\n"
        texto += "\n".join(f"- {capacidad}" for capacidad in capacidades) + "\n"
    return texto


def paquete_del_modulo(
    estado: EstadoGrafo, historial: Sequence[tuple[VersionCodigo, Validacion]]
) -> dict[str, str]:
    """Entregables de un módulo validado, por ruta relativa (RF-35).

    Args:
        estado: Estado de una sesión en fase `validado`.
        historial: Cada versión del módulo con su validación.

    Returns:
        Contenido de cada archivo del paquete: requerimientos y especificación en JSON y en
        Markdown, registro de decisión, código con su documentación, reporte y trazabilidad.

    Raises:
        ErrorExportacion: Si la sesión no terminó con un módulo validado.
    """
    sesion = estado.get("sesion")
    if sesion is None or sesion.fase is not Fase.VALIDADO:
        raise ErrorExportacion("Solo se exporta un módulo validado en la aprobación final.")
    requerimientos = estado["requerimientos"]
    arquitectura = estado["arquitectura"]
    version = estado["codigo"].vigente
    especificacion = arquitectura.especificacion

    def a_json(datos: object) -> str:
        return json.dumps(datos, ensure_ascii=False, indent=2) + "\n"

    archivos = {f"codigo/{ruta}": contenido for ruta, contenido in version.archivos.items()}
    leeme = "\n".join(
        [
            f"# {sesion.proyecto} · módulo validado",
            "",
            f"Sesión {sesion.id_sesion}, cliente {sesion.cliente}. Versión {version.numero} del "
            f"módulo, sobre {especificacion.arquitectura_base}.",
            "",
            "- `requerimientos.md` y `requerimientos.json`: historias y requerimientos (Anexo A).",
            "- `decision_arquitectura.md`: registro de la decisión arquitectónica.",
            "- `especificacion.md` y `especificacion.json`: especificación de diseño (Anexo B).",
            "- `codigo/`: módulos, pruebas y `USO.md`.",
            "- `validacion.md`: reporte de validación del tester.",
            "- `trazabilidad.md`: conversación, decisiones humanas y versiones.",
            "",
            "Las pruebas se ejecutan desde `codigo/` con `PYTHONPATH=src python -m pytest tests`.",
        ]
    )
    return {
        "LEEME.md": leeme + "\n",
        "requerimientos.json": a_json(
            {
                "historias": [h.model_dump(mode="json") for h in requerimientos.historias],
                "requerimientos": [
                    r.model_dump(mode="json") for r in requerimientos.requerimientos
                ],
            }
        ),
        "requerimientos.md": requerimientos_md(
            requerimientos.historias, requerimientos.requerimientos, requerimientos.referencias
        ),
        "decision_arquitectura.md": _registro_con_preguntas(
            arquitectura.registro_decision, arquitectura.capacidades_no_cubiertas
        ),
        "especificacion.json": a_json(especificacion.model_dump(mode="json")),
        "especificacion.md": especificacion_md(especificacion),
        "validacion.md": (estado["validacion"].reporte or "Sin reporte.").rstrip() + "\n",
        "trazabilidad.md": trazabilidad_md(estado, historial),
        **archivos,
    }
