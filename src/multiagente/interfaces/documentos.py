"""Documentos legibles de los artefactos de una sesión, en Markdown (RF-33, RF-35).

Son funciones puras sobre los modelos del estado: la consola las imprime y la exportación las
escribe junto con los mismos artefactos en JSON validado contra esquema (requerimientos, §6).
"""

import json
from collections import Counter
from collections.abc import Mapping, Sequence

from multiagente.agentes.desarrollador.uso import PYTHON, componer_uso
from multiagente.core.conformidad import RUTA_USO
from multiagente.core.esquemas.especificacion_diseno import EspecificacionDiseno
from multiagente.core.esquemas.requerimiento import HistoriaUsuario, RequerimientoFormal
from multiagente.orquestador.estado import (
    Emisor,
    Enmienda,
    EstadoGrafo,
    Fase,
    PruebasPropias,
    RecorridoEscenario,
    ResultadoPrueba,
    Severidad,
    Validacion,
    VersionCodigo,
)
from multiagente.sandbox.requisitos import VersionesProbadas, nombre_canonico


class ErrorExportacion(ValueError):
    """La sesión no tiene un módulo validado que exportar."""


def _celda(texto: str | None) -> str:
    return (texto or "—").replace("|", "\\|").replace("\n", " ")


def _enunciado(como: str, quiero: str, para: str) -> str:
    return f"Como {como}, quiero {quiero}, para {para}."


def _linea(texto: str) -> str:
    return " ".join(texto.split())


def origen_de_enmienda(enmienda: Enmienda, id_requerimiento: str) -> str:
    """Origen de un requerimiento enmendado desde N17, en una línea (ADR-0015).

    Args:
        enmienda: Enmienda que cambió el requerimiento.
        id_requerimiento: Requerimiento enmendado.

    Returns:
        `v0.2 · enmendado desde N17 por … el … UTC: texto de la enmienda`.
    """
    return (
        f"v{enmienda.requerimientos[id_requerimiento]} · enmendado desde N17 por "
        f"{enmienda.revisor} el {enmienda.fecha:%Y-%m-%d %H:%M} UTC: {_linea(enmienda.texto)}"
    )


def requerimientos_md(
    historias: Sequence[HistoriaUsuario],
    requerimientos: Sequence[RequerimientoFormal],
    referencias: Mapping[str, Sequence[str]] | None = None,
    enmiendas: Sequence[Enmienda] = (),
) -> str:
    """Documento de las historias y los requerimientos formales en el formato del Anexo A.

    Args:
        historias: Backlog de historias de usuario (Tabla 27).
        requerimientos: Requerimientos formales (Tabla 28).
        referencias: Fragmentos de contexto que sustentan cada requerimiento (RF-04).
        enmiendas: Enmiendas desde N17; cada requerimiento que cambiaron lleva su origen.

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
        lineas += ["", f"## {requerimiento.id_requerimiento} · versión {requerimiento.version}"]
        origenes = [
            origen_de_enmienda(enmienda, requerimiento.id_requerimiento)
            for enmienda in enmiendas
            if requerimiento.id_requerimiento in enmienda.requerimientos
        ]
        if origenes:
            lineas += ["", *(f"- {origen}" for origen in origenes)]
        lineas += [
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


def recorridos_md(recorridos: Sequence[RecorridoEscenario]) -> str:
    """Tabla de los recorridos de los escenarios: con qué interfaces se ejecuta cada uno.

    Args:
        recorridos: Recorridos que declaró el arquitecto.

    Returns:
        La sección en Markdown, o un aviso si el diseño no los declaró.
    """
    lineas = ["## Recorridos de los escenarios", ""]
    if not recorridos:
        return "\n".join([*lineas, "El diseño no declara recorridos."]) + "\n"
    lineas += ["| Escenario | Prepara | Ejecuta | Observa |", "|---|---|---|---|"]
    lineas += [
        f"| {r.id_requerimiento} {r.id_escenario} | {_celda(', '.join(r.preparar)) or '—'} | "
        f"{_celda(r.ejecutar)} | {_celda(', '.join(r.observar))} |"
        for r in recorridos
    ]
    return "\n".join(lineas) + "\n"


def especificacion_md(
    especificacion: EspecificacionDiseno, recorridos: Sequence[RecorridoEscenario] = ()
) -> str:
    """Documento de la especificación de diseño en el formato del Anexo B.

    Los recorridos de los escenarios no son parte del Anexo B: si los hay, van al final, como
    anexo de la especificación.

    Args:
        especificacion: Especificación de diseño.
        recorridos: Recorridos de sus escenarios.

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
    if recorridos:
        lineas += ["", recorridos_md(recorridos).rstrip("\n")]
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
    lineas += ["", "## Enmiendas", ""]
    enmiendas = [(enmienda, "aprobada") for enmienda in requerimientos.enmiendas]
    if requerimientos.enmienda is not None:
        enmiendas.append((requerimientos.enmienda, "en curso"))
    for enmienda, situacion in enmiendas:
        enmendados = ", ".join(
            f"{id_requerimiento} v{version}"
            for id_requerimiento, version in enmienda.requerimientos.items()
        )
        lineas.append(
            f"- {enmienda.fecha:%Y-%m-%d %H:%M} UTC · {_linea(enmienda.revisor)} · {situacion} · "
            f"enmienda {enmendados or 'ningún requerimiento'}: {_linea(enmienda.texto)}"
        )
        lineas += [
            f"  - Observación del analista: {_linea(observacion)}"
            for observacion in enmienda.observaciones_analista
        ]
    if not enmiendas:
        lineas.append("Ninguna: los requerimientos no se enmendaron desde la aprobación final.")
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


def requirements_del_modulo(
    especificacion: EspecificacionDiseno, probadas: VersionesProbadas
) -> str:
    """`requirements.txt` del módulo: sus dependencias declaradas, las de ellas y pytest.

    Todas llevan la versión con que el tester probó el módulo en el entorno aislado, también las
    transitivas, para que `pip install -r requirements.txt` reproduzca ese entorno.

    Args:
        especificacion: Especificación aprobada, con las dependencias externas.
        probadas: Versiones del entorno aislado (`sandbox.versiones_probadas`).

    Returns:
        El contenido del archivo. Una librería fuera del entorno aislado queda sin fijar.
    """
    declaradas = list(
        dict.fromkeys(nombre_canonico(d.paquete) for d in especificacion.dependencias_externas)
    )
    transitivas = sorted(
        {dependencia for nombre in declaradas for dependencia in probadas.cierres.get(nombre, ())}
        - set(declaradas)
    )
    de_pytest = [
        dependencia
        for dependencia in probadas.cierres.get("pytest", ())
        if dependencia not in {*declaradas, *transitivas}
    ]

    def fijada(nombre: str) -> str:
        return probadas.requisitos.get(nombre) or probadas.versiones.get(nombre, nombre)

    lineas = [
        "# Dependencias del módulo y las de ellas, con las versiones con que el tester lo probó",
        f"# en el entorno aislado (Python {PYTHON} en Linux). Se instalan con:",
        "# pip install -r requirements.txt",
        *(fijada(nombre) for nombre in [*declaradas, *transitivas]),
    ]
    if "pytest" not in declaradas:
        lineas += ["# Para las pruebas.", fijada("pytest"), *(fijada(n) for n in de_pytest)]
    return "\n".join(lineas) + "\n"


def paquete_del_modulo(
    estado: EstadoGrafo,
    historial: Sequence[tuple[VersionCodigo, Validacion]],
    probadas: VersionesProbadas | None = None,
) -> dict[str, str]:
    """Entregables de un módulo validado, por ruta relativa (RF-35).

    Args:
        estado: Estado de una sesión en fase `validado`.
        historial: Cada versión del módulo con su validación.
        probadas: Versiones del entorno aislado (`sandbox.versiones_probadas`), para el
            `requirements.txt`; sin ellas, las dependencias quedan sin versión fija.

    Returns:
        Contenido de cada archivo del paquete: requerimientos y especificación en JSON y en
        Markdown, registro de decisión, código con su documentación y su `requirements.txt`,
        reporte y trazabilidad, y un `LEEME.md` que dice cómo ponerlo en marcha.

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
    if (uso := version.archivos.get(RUTA_USO)) is not None:
        # Las versiones de antes de componer el documento traen las secciones que redactó el modelo.
        paquetes = [dependencia.paquete for dependencia in especificacion.dependencias_externas]
        archivos[f"codigo/{RUTA_USO}"] = componer_uso(uso, paquetes)
    archivos["codigo/requirements.txt"] = requirements_del_modulo(
        especificacion, probadas or VersionesProbadas()
    )
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
            "- `codigo/`: módulos, pruebas, `USO.md` y `requirements.txt`.",
            "- `validacion.md`: reporte de validación del tester.",
            "- `trazabilidad.md`: conversación, decisiones humanas, enmiendas y versiones.",
            "",
            "## Cómo ponerlo en marcha",
            "",
            f"Desde la carpeta `codigo/`, con Python {PYTHON} o superior (el módulo se probó con "
            f"Python {PYTHON}):",
            "",
            "1. Cree y active un entorno: `python3 -m venv .venv && source .venv/bin/activate`",
            "   (en Windows, `.venv\\Scripts\\activate`).",
            "2. Instale las dependencias: `pip install -r requirements.txt`.",
            "3. Prepare la configuración y ejecútelo como indican las secciones «Configuración» y",
            "   «Ejecución» de `USO.md`.",
            "4. Compruebe que funciona con sus pruebas: `PYTHONPATH=src python -m pytest tests`.",
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
            requerimientos.historias,
            requerimientos.requerimientos,
            requerimientos.referencias,
            requerimientos.enmiendas,
        ),
        "decision_arquitectura.md": _registro_con_preguntas(
            arquitectura.registro_decision, arquitectura.capacidades_no_cubiertas
        ),
        "especificacion.json": a_json(especificacion.model_dump(mode="json")),
        "especificacion.md": especificacion_md(especificacion, arquitectura.recorridos),
        "validacion.md": (estado["validacion"].reporte or "Sin reporte.").rstrip() + "\n",
        "trazabilidad.md": trazabilidad_md(estado, historial),
        **archivos,
    }
