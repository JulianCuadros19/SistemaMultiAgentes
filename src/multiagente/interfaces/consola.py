"""Presentación en consola de lo que la persona revisa en los tres puntos de control humano.

Cada función recibe los datos de la pausa (`Pausa.datos`), tal como los entrega el nodo: N6 los
requerimientos, N9 la especificación de diseño y N17 el módulo con su reporte de validación.
"""

from typing import Any


def mostrar_requerimientos(datos: dict[str, Any]) -> None:
    """Imprime los artefactos que la persona revisa en N6."""
    print("\n=== Punto de control N6: requerimientos ===")
    for historia in datos["historias"]:
        enunciado = historia["enunciado"]
        print(
            f"\n{historia['id']} · Como {enunciado['como']}, quiero {enunciado['quiero']}, "
            f"para {enunciado['para']} (prioridad {historia['prioridad']})"
        )
        for supuesto in historia["supuestos"]:
            print(f"  Supuesto: {supuesto}")
        for pregunta in historia["preguntas_abiertas"]:
            print(f"  Pregunta abierta: {pregunta}")
    for requerimiento in datos["requerimientos"]:
        descripcion = requerimiento["descripcion"]
        print(
            f"\n{requerimiento['id_requerimiento']} v{requerimiento['version']} · "
            f"módulo {requerimiento['modulo']} · impacto {requerimiento['impacto']}"
        )
        print(f"  Precondición: {descripcion['precondicion']}")
        print(f"  Regla de negocio: {descripcion['regla_negocio']}")
        for dato in descripcion["datos_entrada"]:
            obligatorio = "obligatorio" if dato["obligatorio"] else "opcional"
            restriccion = f", {dato['restriccion']}" if dato["restriccion"] else ""
            print(f"  Entrada: {dato['nombre']} ({dato['tipo']}, {obligatorio}{restriccion})")
        for dato in descripcion["datos_salida"]:
            formato = f", {dato['formato']}" if dato["formato"] else ""
            print(f"  Salida: {dato['nombre']} ({dato['tipo']}{formato})")
        for escenario in requerimiento["criterios_aceptacion"]:
            print(
                f"  {escenario['id']} · {escenario['nombre']}: DADO QUE {escenario['dado_que']}, "
                f"CUANDO {escenario['cuando']}, ENTONCES {escenario['entonces']}"
            )
        for referencia in datos["referencias"].get(requerimiento["id_requerimiento"], []):
            print(f"  Fuente: {referencia}")
    if datos["defectos"]:
        print("\nDefectos de calidad sin corregir (escalados al analista):")
        for defecto in datos["defectos"]:
            print(f"  - {defecto}")
    else:
        print("\nVerificación de calidad (RF-07): sin defectos.")


def mostrar_especificacion(datos: dict[str, Any]) -> None:
    """Imprime lo que la persona revisa en N9."""
    print("\n=== Punto de control N9: especificación de diseño ===\n")
    print(datos["registro_decision"])
    especificacion = datos["especificacion"]
    cubiertos = especificacion["requerimientos_cubiertos"]
    print(
        f"{especificacion['id_especificacion']} v{especificacion['version']} · "
        f"{especificacion['arquitectura_base']} · cubre {cubiertos}"
    )
    for modulo in especificacion["modulos"]:
        dependencias = ", ".join(modulo["dependencias_permitidas"]) or "ninguna"
        print(
            f"\n  {modulo['nombre']} ({modulo['ruta']}, capa {modulo['capa']}) · "
            f"{modulo['requerimientos']} · importa: {dependencias}"
        )
        print(f"    {modulo['responsabilidad']}")
        for interfaz in modulo["interfaces_publicas"]:
            excepciones = f" · lanza {interfaz['excepciones']}" if interfaz["excepciones"] else ""
            print(f"    {interfaz['tipo']} {interfaz['firma']}{excepciones}")
    for entidad in especificacion["modelo_datos"]:
        campos = ", ".join(f"{c['nombre']}: {c['tipo']}" for c in entidad["campos"])
        print(f"\n  Entidad {entidad['nombre']}({campos})")
    paquetes = ", ".join(d["paquete"] for d in especificacion["dependencias_externas"])
    print(f"\n  Dependencias externas: {paquetes or 'ninguna'}")
    for regla in especificacion["reglas_de_dependencia"]:
        print(f"  Regla: {regla}")
    if datos["errores"]:
        print("\nErrores de validación (Anexo B); solo se admite el rechazo:")
        for error in datos["errores"]:
            print(f"  - {error}")
    else:
        print("\nValidaciones del Anexo B: sin errores.")


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
