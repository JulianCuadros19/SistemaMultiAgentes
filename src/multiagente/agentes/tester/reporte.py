"""Reporte de validación en Markdown, legible por la persona y por el desarrollador (RF-24).

Reúne lo que la persona revisa en la aprobación final (N17): el veredicto, el dictamen de cada
caso con su evidencia, la conformidad de cada módulo, los hallazgos por severidad, la ejecución
y las reglas que no se evaluaron.
"""

from collections import Counter

from multiagente.orquestador.estado import (
    CasoPrueba,
    ConformidadModulo,
    EjecucionPruebas,
    Hallazgo,
    Severidad,
    Veredicto,
    VeredictoCaso,
)


def _celda(texto: str) -> str:
    return texto.replace("|", "\\|").replace("\n", " ")


def reporte_validacion(
    numero_version: int,
    veredicto: Veredicto,
    plan: tuple[CasoPrueba, ...],
    veredictos: tuple[VeredictoCaso, ...],
    hallazgos: tuple[Hallazgo, ...],
    conformidad: tuple[ConformidadModulo, ...],
    no_evaluadas: tuple[str, ...],
    ejecucion: EjecucionPruebas,
    umbral_media: int,
) -> str:
    """Arma el reporte de validación de una versión.

    Args:
        numero_version: Versión del módulo.
        veredicto: Veredicto único.
        plan: Casos del plan de pruebas de aceptación.
        veredictos: Dictamen de cada caso.
        hallazgos: Hallazgos ordenados por severidad.
        conformidad: Conformidad de cada módulo declarado.
        no_evaluadas: Reglas sin comprobación automática.
        ejecucion: Resultado de la ejecución en el entorno aislado.
        umbral_media: Hallazgos de severidad media que se toleran.

    Returns:
        El reporte en Markdown.
    """
    por_severidad = Counter(h.severidad for h in hallazgos)
    cumplidos = sum(v.cumple for v in veredictos)
    lineas = [
        f"# Reporte de validación · versión {numero_version}",
        "",
        f"**Veredicto: {veredicto.value.upper()}** · {cumplidos} de {len(plan)} casos cumplen · "
        f"hallazgos: {por_severidad[Severidad.ALTA]} de severidad alta, "
        f"{por_severidad[Severidad.MEDIA]} media (umbral {umbral_media}) y "
        f"{por_severidad[Severidad.BAJA]} baja.",
        "",
        "## Casos de aceptación",
        "",
        "| Caso | Cumple | Evidencia |",
        "|---|---|---|",
    ]
    lineas += [
        f"| {v.id_caso} | {'sí' if v.cumple else 'no'} | {_celda(v.evidencia)} |"
        for v in veredictos
    ]
    lineas += [
        "",
        "## Conformidad arquitectónica",
        "",
        "| Módulo | Existe | Interfaces conformes | Interfaces divergentes | Dependencias no "
        "autorizadas |",
        "|---|---|---|---|---|",
    ]
    lineas += [
        f"| {c.modulo} | {'sí' if c.existe else 'no'} | {', '.join(c.interfaces_conformes) or '—'}"
        f" | {', '.join(c.interfaces_divergentes) or '—'} | "
        f"{_celda('; '.join(c.dependencias_no_autorizadas)) or '—'} |"
        for c in conformidad
    ]
    lineas += ["", "## Hallazgos", ""]
    if not hallazgos:
        lineas.append("Sin hallazgos.")
    for severidad in (Severidad.ALTA, Severidad.MEDIA, Severidad.BAJA):
        del_nivel = [h for h in hallazgos if h.severidad is severidad]
        if not del_nivel:
            continue
        lineas += [f"### Severidad {severidad.value}", ""]
        lineas += [
            f"- **{h.regla}** · `{h.ubicacion}` · {h.descripcion} *Sugerencia:* {h.sugerencia}"
            for h in del_nivel
        ]
        lineas.append("")
    resultados = Counter(prueba.resultado.value for prueba in ejecucion.pruebas)
    lineas += [
        "",
        "## Ejecución en el entorno aislado",
        "",
        f"- Pruebas: {len(ejecucion.pruebas)} ({dict(resultados) or 'ninguna'}), en "
        f"{ejecucion.duracion_ms} ms.",
        f"- Módulos que no se importan: {sorted(ejecucion.errores_importacion) or 'ninguno'}.",
        f"- Archivos de prueba sin recolectar: {len(ejecucion.errores_recoleccion)}.",
        f"- Tiempo vencido: {'sí' if ejecucion.vencido else 'no'}.",
        "",
        "## Reglas no evaluadas",
        "",
        "Sin comprobación automática; quedan para la revisión humana: "
        f"{', '.join(no_evaluadas) or 'ninguna'}.",
    ]
    return "\n".join(lineas).rstrip() + "\n"
