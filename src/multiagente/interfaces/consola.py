"""Presentación en consola de lo que la persona revisa en los tres puntos de control humano.

Cada función recibe los datos de la pausa (`Pausa.datos`), tal como los entrega el nodo: N6 los
requerimientos, N9 la especificación de diseño y N17 el módulo con su reporte de validación.
"""

from typing import Any

from multiagente.core.esquemas.especificacion_diseno import EspecificacionDiseno
from multiagente.core.esquemas.requerimiento import HistoriaUsuario, RequerimientoFormal
from multiagente.interfaces.documentos import especificacion_md, requerimientos_md


def mostrar_requerimientos(datos: dict[str, Any]) -> None:
    """Imprime los artefactos que la persona revisa en N6, en el formato del Anexo A."""
    print("\n=== Punto de control N6: requerimientos ===\n")
    print(
        requerimientos_md(
            [HistoriaUsuario.model_validate(historia) for historia in datos["historias"]],
            [RequerimientoFormal.model_validate(r) for r in datos["requerimientos"]],
            datos["referencias"],
        )
    )
    if datos["defectos"]:
        print("Defectos de calidad sin corregir (escalados al analista):")
        for defecto in datos["defectos"]:
            print(f"  - {defecto}")
    else:
        print("Verificación de calidad (RF-07): sin defectos.")


def mostrar_especificacion(datos: dict[str, Any]) -> None:
    """Imprime lo que la persona revisa en N9: el registro de decisión y la especificación."""
    print("\n=== Punto de control N9: especificación de diseño ===\n")
    print(datos["registro_decision"])
    print()
    print(especificacion_md(EspecificacionDiseno.model_validate(datos["especificacion"])))
    if datos["errores"]:
        print("Errores de validación (Anexo B); solo se admite el rechazo:")
        for error in datos["errores"]:
            print(f"  - {error}")
    else:
        print("Validaciones del Anexo B: sin errores.")


def mostrar_validacion(datos: dict[str, Any]) -> None:
    """Imprime lo que la persona revisa en N17: los archivos del módulo y su reporte (RF-38).

    El reporte del tester ya reúne el veredicto, el dictamen por caso, la conformidad por
    módulo, los hallazgos por severidad, la ejecución y las reglas no evaluadas.
    """
    print(f"\n=== Punto de control N17: versión {datos['version']} del módulo ===\n")
    for ruta in datos["archivos"]:
        print(f"  {ruta}")
    print()
    print(datos["reporte"] or "(El tester no emitió reporte.)")
    print(
        f"Iteración {datos['iteracion']} de {datos['limite_iteraciones']} del ciclo de "
        "corrección. Si rechaza, el desarrollador corrige y la cuenta sigue; alcanzado el límite, "
        "un rechazo del tester escala la sesión a una persona."
    )
