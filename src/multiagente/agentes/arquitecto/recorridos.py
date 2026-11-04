"""Recorridos de los escenarios: cómo se ejecuta cada uno con las interfaces del diseño (N8 y N9).

Por cada escenario aprobado, el arquitecto declara las interfaces que preparan su «dado que», la
que ejecuta su «cuando» y las que observan su «entonces». Los recorridos no son un campo del
Anexo B. El código verifica que nombren interfaces declaradas y anota en la descripción de cada
interfaz los escenarios en que participa, de modo que el desarrollador los recibe dentro de la
especificación (ADR-0015).
"""

import ast
import re
from collections import Counter, defaultdict

from pydantic import BaseModel, ConfigDict, ValidationError

from multiagente.core.esquemas.especificacion_diseno import (
    EspecificacionDiseno,
    InterfazPublica,
    TipoInterfaz,
    firma_como_funcion,
)
from multiagente.llm.invocador import ErrorValidacionSalida
from multiagente.orquestador.estado import RecorridoEscenario, Requerimientos

ESCENARIOS = "Escenarios ejecutables"
SEPARADOR = " · Escenarios: "
"""Separa la descripción que escribió el arquitecto de la anotación que agrega el código."""

PARENTESIS = re.compile(r"\([^()]*\)")


class RecorridoModelo(BaseModel):
    """RecorridoEscenario de un escenario, tal como lo devuelve el modelo."""

    model_config = ConfigDict(extra="forbid")

    id_requerimiento: str
    id_escenario: str
    preparar: list[str]
    ejecutar: str
    observar: list[str]


def nombre_limpio(nombre: str) -> str:
    """Quita del nombre de una interfaz las comillas invertidas y los argumentos que traiga.

    Args:
        nombre: Nombre tal como lo escribió el modelo, p. ej. ``Bus().publicar(aviso)``.

    Returns:
        El nombre en notación de puntos, p. ej. ``Bus.publicar``.
    """
    limpio = nombre.replace("`", "").strip()
    while (sin_argumentos := PARENTESIS.sub("", limpio)) != limpio:
        limpio = sin_argumentos
    return limpio.strip().strip(".")


def recorridos_desde_salida(salida: list[RecorridoModelo]) -> tuple[RecorridoEscenario, ...]:
    """Normaliza los recorridos del modelo y los valida contra el esquema.

    Args:
        salida: Recorridos tal como los devolvió el modelo.

    Returns:
        Los recorridos con identificadores en mayúsculas y nombres limpios.

    Raises:
        ErrorValidacionSalida: Si algún recorrido incumple el esquema.
    """
    problemas: list[str] = []
    recorridos: list[RecorridoEscenario] = []
    for posicion, recorrido in enumerate(salida):
        try:
            recorridos.append(
                RecorridoEscenario(
                    id_requerimiento=recorrido.id_requerimiento.strip().upper(),
                    id_escenario=recorrido.id_escenario.strip().upper(),
                    preparar=tuple(n for n in map(nombre_limpio, recorrido.preparar) if n),
                    ejecutar=nombre_limpio(recorrido.ejecutar),
                    observar=tuple(n for n in map(nombre_limpio, recorrido.observar) if n),
                )
            )
        except ValidationError as error:
            problemas.extend(
                f"recorridos.{posicion}.{'.'.join(str(p) for p in detalle['loc'])}: "
                f"{detalle['msg']}"
                for detalle in error.errors()
            )
    if problemas:
        raise ErrorValidacionSalida(problemas)
    return tuple(recorridos)


def _declaradas(
    nombre: str, especificacion: EspecificacionDiseno
) -> list[tuple[str, InterfazPublica]]:
    """Interfaces que nombra el texto: la última parte del nombre, en el módulo si lo califica."""
    prefijo, _, ultimo = nombre.rpartition(".")
    candidatas = [
        (modulo.nombre, interfaz)
        for modulo in especificacion.modulos
        for interfaz in modulo.interfaces_publicas
        if interfaz.nombre == ultimo
    ]
    calificadores = [
        modulo.nombre
        for modulo in especificacion.modulos
        if prefijo == modulo.nombre or prefijo.startswith(f"{modulo.nombre}.")
    ]
    if calificadores:
        modulo = max(calificadores, key=len)
        candidatas = [(m, interfaz) for m, interfaz in candidatas if m == modulo]
    return candidatas


def _es_entidad(nombre: str, especificacion: EspecificacionDiseno) -> bool:
    return nombre.rpartition(".")[2] in {e.nombre for e in especificacion.modelo_datos}


def _sin_resultado(interfaz: InterfazPublica) -> bool:
    """Si la interfaz es una función que no devuelve nada ni declara excepciones."""
    if interfaz.tipo is not TipoInterfaz.FUNCION or interfaz.excepciones:
        return False
    try:
        retorno = firma_como_funcion(interfaz).returns
    except SyntaxError:
        return False
    return retorno is not None and ast.unparse(retorno) == "None"


def _errores_de_nombre(
    donde: str, papel: str, nombre: str, especificacion: EspecificacionDiseno
) -> list[str]:
    candidatas = _declaradas(nombre, especificacion)
    if len(candidatas) > 1:
        modulos = ", ".join(sorted(modulo for modulo, _ in candidatas))
        return [
            f"{donde}: en {papel}, «{nombre}» está declarada en {modulos}; califícala con su "
            "módulo (modulo.interfaz)"
        ]
    if candidatas:
        return []
    if _es_entidad(nombre, especificacion):
        if papel == "preparar":
            return []
        accion = (
            "la interfaz que realiza la acción del «cuando»"
            if papel == "ejecutar"
            else "la interfaz que la entrega: la de ejecutar, si es lo que devuelve, o una de "
            "consulta"
        )
        return [
            f"{donde}: en {papel}, «{nombre}» es una entidad del modelo de datos, no una "
            f"interfaz; nombra {accion}"
        ]
    entidad = " ni una entidad del modelo de datos" if papel == "preparar" else ""
    return [
        f"{donde}: en {papel}, «{nombre}» no es una interfaz declarada{entidad}; usa el nombre "
        "exacto de una interfaz pública de la especificación o declárala"
    ]


def _errores_del_recorrido(
    recorrido: RecorridoEscenario, especificacion: EspecificacionDiseno
) -> list[str]:
    donde = f"{ESCENARIOS}: {recorrido.id_requerimiento} {recorrido.id_escenario}"
    errores: list[str] = []
    for papel, nombres in (
        ("preparar", recorrido.preparar),
        ("ejecutar", (recorrido.ejecutar,)),
        ("observar", recorrido.observar),
    ):
        for nombre in nombres:
            errores.extend(_errores_de_nombre(donde, papel, nombre, especificacion))
    ejecutada = _declaradas(recorrido.ejecutar, especificacion)
    observadas = {
        (modulo, interfaz.nombre)
        for nombre in recorrido.observar
        for modulo, interfaz in _declaradas(nombre, especificacion)
    }
    if (
        len(ejecutada) == 1
        and observadas == {(ejecutada[0][0], ejecutada[0][1].nombre)}
        and _sin_resultado(ejecutada[0][1])
    ):
        errores.append(
            f"{donde}: solo observa con «{recorrido.ejecutar}», que no devuelve nada ni declara "
            "excepciones; nombra la interfaz de consulta que muestra el efecto del «entonces»"
        )
    return errores


def errores_de_recorridos(
    especificacion: EspecificacionDiseno,
    requerimientos: Requerimientos,
    recorridos: tuple[RecorridoEscenario, ...],
) -> list[str]:
    """Verifica que cada escenario aprobado se pueda ejecutar con las interfaces declaradas.

    Cada escenario debe tener exactamente un recorrido, y cada nombre del recorrido debe ser una
    interfaz pública de la especificación. Al preparar también vale una entidad del modelo de
    datos, que la prueba construye. Además, el «entonces» debe poder observarse: no basta con
    una función que no devuelve nada ni declara excepciones.

    Args:
        especificacion: Especificación del diseño.
        requerimientos: Requerimientos aprobados, con sus escenarios.
        recorridos: Recorridos declarados por el arquitecto.

    Returns:
        Errores encontrados, cada uno con el escenario y lo que hay que cambiar.
    """
    escenarios = [
        (requerimiento.id_requerimiento, escenario.id)
        for requerimiento in requerimientos.requerimientos
        for escenario in requerimiento.criterios_aceptacion
    ]
    conteo = Counter((r.id_requerimiento, r.id_escenario) for r in recorridos)
    errores: list[str] = []
    for rf, esc in escenarios:
        if conteo[rf, esc] == 0:
            errores.append(
                f"{ESCENARIOS}: {rf} {esc} no tiene recorrido; declara con qué interfaces se "
                "prepara su «dado que», se ejecuta su «cuando» y se observa su «entonces»"
            )
        elif conteo[rf, esc] > 1:
            errores.append(f"{ESCENARIOS}: {rf} {esc} tiene {conteo[rf, esc]} recorridos")
    errores.extend(
        f"{ESCENARIOS}: el recorrido de {rf} {esc} no corresponde a un escenario aprobado"
        for rf, esc in sorted(set(conteo) - set(escenarios))
    )
    for recorrido in recorridos:
        if (recorrido.id_requerimiento, recorrido.id_escenario) in escenarios:
            errores.extend(_errores_del_recorrido(recorrido, especificacion))
    return errores


def _enumerar(nombres: list[str]) -> str:
    return nombres[0] if len(nombres) == 1 else f"{', '.join(nombres[:-1])} y {nombres[-1]}"


def descripcion_base(descripcion: str) -> str:
    """Devuelve la descripción sin la anotación de escenarios que agrega el código.

    Args:
        descripcion: Descripción de una interfaz, anotada o no.

    Returns:
        La descripción tal como la escribió el arquitecto.
    """
    return descripcion.split(SEPARADOR, 1)[0].rstrip()


def _con_descripciones(
    especificacion: EspecificacionDiseno, descripciones: dict[tuple[str, str], str]
) -> EspecificacionDiseno:
    modulos = [
        modulo.model_copy(
            update={
                "interfaces_publicas": [
                    interfaz.model_copy(
                        update={"descripcion": descripciones[modulo.nombre, interfaz.nombre]}
                    )
                    for interfaz in modulo.interfaces_publicas
                ]
            }
        )
        for modulo in especificacion.modulos
    ]
    return especificacion.model_copy(update={"modulos": modulos})


def sin_anotaciones(especificacion: EspecificacionDiseno) -> EspecificacionDiseno:
    """Quita de las descripciones de las interfaces la anotación de escenarios.

    Args:
        especificacion: Especificación, anotada o no.

    Returns:
        La especificación tal como la declaró el arquitecto.
    """
    return _con_descripciones(
        especificacion,
        {
            (modulo.nombre, interfaz.nombre): descripcion_base(interfaz.descripcion)
            for modulo in especificacion.modulos
            for interfaz in modulo.interfaces_publicas
        },
    )


def anotar_escenarios(
    especificacion: EspecificacionDiseno, recorridos: tuple[RecorridoEscenario, ...]
) -> EspecificacionDiseno:
    """Anota en la descripción de cada interfaz los escenarios en que participa.

    La interfaz que ejecuta un escenario recibe el recorrido completo; las que lo preparan o lo
    observan, su papel. Anotar dos veces da el mismo resultado: la anotación previa se reemplaza.

    Args:
        especificacion: Especificación del diseño.
        recorridos: Recorridos de sus escenarios, ya verificados.

    Returns:
        La especificación con las descripciones anotadas.
    """
    papeles: dict[tuple[str, str], dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    detalles: dict[tuple[tuple[str, str], str], str] = {}
    for recorrido in recorridos:
        escenario = f"{recorrido.id_requerimiento} {recorrido.id_escenario}"
        ejecutada = _declaradas(recorrido.ejecutar, especificacion)
        for papel, nombres in (
            ("prepara", recorrido.preparar),
            ("ejecuta", (recorrido.ejecutar,)),
            ("observa", recorrido.observar),
        ):
            for nombre in nombres:
                for modulo, interfaz in _declaradas(nombre, especificacion):
                    roles = papeles[modulo, interfaz.nombre][escenario]
                    if papel not in roles:
                        roles.append(papel)
        if len(ejecutada) == 1:
            clave = (ejecutada[0][0], ejecutada[0][1].nombre)
            partes = []
            if recorrido.preparar:
                partes.append(f"prepara con {_enumerar(list(recorrido.preparar))}")
            otras = [n for n in recorrido.observar if _declaradas(n, especificacion) != ejecutada]
            propio = len(otras) < len(recorrido.observar)
            if propio and otras:
                partes.append(f"observa su resultado y con {_enumerar(otras)}")
            elif propio:
                partes.append("observa su resultado")
            else:
                partes.append(f"observa con {_enumerar(otras)}")
            detalles[clave, escenario] = "; ".join(["ejecuta", *partes])
    descripciones: dict[tuple[str, str], str] = {}
    for modulo in especificacion.modulos:
        for interfaz in modulo.interfaces_publicas:
            clave = (modulo.nombre, interfaz.nombre)
            base = descripcion_base(interfaz.descripcion)
            notas = [
                f"{escenario} ({detalles.get((clave, escenario)) or ', '.join(roles)})"
                for escenario, roles in papeles.get(clave, {}).items()
            ]
            descripciones[clave] = f"{base}{SEPARADOR}{', '.join(notas)}" if notas else base
    return _con_descripciones(especificacion, descripciones)
