"""Validaciones de la especificación de diseño antes de habilitar la generación de código (N9).

Aplica las tres validaciones del Anexo B, de forma determinística:

1. Conformidad con el esquema y ausencia de dependencias circulares, más las reglas de la
   plantilla arq-002 que el código necesita para verificar la conformidad en N12: firmas
   completas con tipos, rutas coherentes con la capa y con el nombre del módulo, y paquetes que
   no tapen un módulo de la biblioteca estándar ni una dependencia (un paquete `io` rompería
   `import io`).
2. Cobertura: todo requerimiento aprobado queda asignado al menos a un módulo.
3. Catálogo tecnológico: toda dependencia externa pertenece al catálogo autorizado (arq-004) y
   la arquitectura base es una del catálogo de referencia.

Además, el dinero y los avalúos usan `Decimal` (decisión 10 de `CLAUDE.md`, regla 1 de arq-004).
"""

import ast
import re
import sys

from pydantic import ValidationError

from multiagente.agentes.arquitecto.catalogo import CatalogoTecnologico
from multiagente.core.esquemas.especificacion_diseno import (
    EspecificacionDiseno,
    InterfazPublica,
    TipoInterfaz,
    firma_como_funcion,
)
from multiagente.orquestador.estado import Requerimientos

ESQUEMA = "Validación 1 · esquema"
COBERTURA = "Validación 2 · cobertura"
CATALOGO = "Validación 3 · catálogo"
DINERO = "Dinero en Decimal"

MONETARIO = re.compile(
    r"(?:avaluo|valor|monto|tarifa|impuesto|precio|pago|saldo|deuda|liquidacion|costo|interes"
    r"|descuento|recargo|multa|cuota)"
)
"""Raíces de los nombres de campos y parámetros que representan dinero o avalúos."""


def _errores_de_firma(modulo: str, interfaz: InterfazPublica) -> list[str]:
    ubicacion = f"{modulo}.{interfaz.nombre}"
    try:
        funcion = firma_como_funcion(interfaz)
    except SyntaxError:
        return [f"{ESQUEMA}: la firma de {ubicacion} no es una firma de Python válida"]
    errores = []
    if funcion.name != interfaz.nombre:
        errores.append(f"{ESQUEMA}: la firma de {ubicacion} declara el nombre {funcion.name}")
    argumentos = funcion.args
    todos = [*argumentos.posonlyargs, *argumentos.args, *argumentos.kwonlyargs]
    todos += [a for a in (argumentos.vararg, argumentos.kwarg) if a is not None]
    sin_tipo = [a.arg for a in todos if a.annotation is None and a.arg not in ("self", "cls")]
    if sin_tipo:
        errores.append(f"{ESQUEMA}: la firma de {ubicacion} no declara el tipo de {sin_tipo}")
    if interfaz.tipo is TipoInterfaz.FUNCION and funcion.returns is None:
        errores.append(f"{ESQUEMA}: la firma de {ubicacion} no declara el tipo de retorno")
    for argumento in todos:
        if (
            argumento.annotation is not None
            and ast.unparse(argumento.annotation) == "float"
            and MONETARIO.search(argumento.arg.lower())
        ):
            errores.append(
                f"{DINERO}: el parámetro {argumento.arg} de {ubicacion} es monetario y usa float"
            )
    return errores


def _errores_de_ruta(nombre: str, ruta: str, capa: str, reservados: frozenset[str]) -> list[str]:
    errores = []
    paquete = nombre.split(".", 1)[0]
    if paquete in reservados:
        errores.append(
            f"{ESQUEMA}: el paquete «{paquete}» de {nombre} tapa un módulo de la biblioteca "
            "estándar o una dependencia; usa otro nombre"
        )
    relativa = ruta.removeprefix("./").removeprefix("src/").removesuffix(".py")
    if relativa.replace("/", ".") != nombre:
        errores.append(f"{ESQUEMA}: la ruta {ruta} no corresponde al módulo {nombre}")
    raiz_capa = capa.lower()[: min(len(capa), 5)]
    if not any(parte.lower().startswith(raiz_capa) for parte in ruta.split("/")[:-1]):
        errores.append(f"{ESQUEMA}: la ruta {ruta} no está en una carpeta de la capa «{capa}»")
    return errores


def validar_especificacion(
    especificacion: EspecificacionDiseno,
    requerimientos: Requerimientos,
    catalogo: CatalogoTecnologico,
    arquitecturas: frozenset[str],
) -> list[str]:
    """Aplica las tres validaciones del Anexo B y la regla del dinero en Decimal.

    Args:
        especificacion: Especificación producida por N8.
        requerimientos: Requerimientos aprobados en N6.
        catalogo: Catálogo tecnológico autorizado.
        arquitecturas: Identificadores del catálogo cerrado de arquitecturas.

    Returns:
        Errores encontrados, cada uno con la validación que incumple; vacía si la especificación
        puede someterse a aprobación humana.
    """
    errores: list[str] = []
    try:
        EspecificacionDiseno.model_validate(especificacion.model_dump())
    except ValidationError as error:
        errores.extend(f"{ESQUEMA}: {detalle['msg']}" for detalle in error.errors())

    reservados = frozenset(sys.stdlib_module_names) | catalogo.autorizadas
    for modulo in especificacion.modulos:
        errores.extend(_errores_de_ruta(modulo.nombre, modulo.ruta, modulo.capa, reservados))
        for interfaz in modulo.interfaces_publicas:
            errores.extend(_errores_de_firma(modulo.nombre, interfaz))

    aprobados = {r.id_requerimiento for r in requerimientos.requerimientos}
    asignados = {rf for modulo in especificacion.modulos for rf in modulo.requerimientos}
    errores.extend(
        f"{COBERTURA}: {rf} no está asignado a ningún módulo"
        for rf in sorted(aprobados - asignados)
    )
    errores.extend(
        f"{COBERTURA}: {rf} no es un requerimiento aprobado"
        for rf in sorted(set(especificacion.requerimientos_cubiertos) - aprobados)
    )

    if especificacion.arquitectura_base not in arquitecturas:
        errores.append(
            f"{CATALOGO}: {especificacion.arquitectura_base} no pertenece al catálogo de "
            f"arquitecturas de referencia {sorted(arquitecturas)}"
        )
    for dependencia in especificacion.dependencias_externas:
        paquete = dependencia.paquete.strip().lower()
        if paquete in catalogo.estandar:
            errores.append(
                f"{CATALOGO}: {paquete} es de la biblioteca estándar y no se declara como "
                "dependencia externa"
            )
        elif paquete not in catalogo.autorizadas:
            errores.append(
                f"{CATALOGO}: {paquete} no pertenece al catálogo tecnológico autorizado "
                f"{sorted(catalogo.autorizadas)}"
            )

    for entidad in especificacion.modelo_datos:
        for campo in entidad.campos:
            if campo.tipo.strip().lower() == "float" and MONETARIO.search(campo.nombre.lower()):
                errores.append(
                    f"{DINERO}: el campo {entidad.nombre}.{campo.nombre} es monetario y usa float"
                )
    return errores
