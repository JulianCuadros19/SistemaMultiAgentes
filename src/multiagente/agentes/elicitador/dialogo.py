"""Diálogo de elicitación (N3): extrae lo que dijo el cliente y formula la siguiente pregunta.

N3 hace dos llamadas con propósitos distintos, para que el modelo no mezcle lo que dijo el
cliente con lo que sabe del dominio:

1. La extracción ve solo el registro, la pregunta anterior y la respuesta nueva, sin contexto
   de dominio. Devuelve solo los atributos que la respuesta aporta o corrige, cada uno con su
   valor completo y vigente, y `null` en los demás. Aparte, devuelve lo que la respuesta
   rechaza sin decir con qué reemplazarlo.
2. La pregunta ve el contexto recuperado en N2 (RF-04), el registro y las observaciones del
   revisor. No se pide cuando el cliente acaba de completar todo: entonces el sistema muestra el
   resumen con la pregunta de cierre.

El código, no el prompt, garantiza las reglas que deben cumplirse siempre:

- lo ya capturado no se pierde por omisión del modelo: solo sale lo que el cliente rechaza y
  menciona en su respuesta;
- solo entra al registro lo que está respaldado por lo que dijo el cliente
  (`multiagente.agentes.elicitador.fidelidad`), y solo hay preguntas abiertas si el cliente dijo
  no saber algo;
- el resumen solo queda confirmado con una respuesta nueva del cliente, con el registro completo
  y sin cambios respecto del resumen que se le presentó;
- hay pregunta si y solo si falta algo, y es una sola, en lenguaje de negocio (RNF-08);
- el resumen que el cliente confirma se arma con el registro, de modo que confirma exactamente
  lo que se va a sintetizar.
"""

import json
import re
from enum import StrEnum
from typing import TypeVar

from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, ConfigDict

from multiagente.agentes.contexto import json_texto
from multiagente.agentes.elicitador.calidad import normalizar
from multiagente.agentes.elicitador.contexto import mensaje_contexto
from multiagente.agentes.elicitador.fidelidad import (
    desconoce_algo,
    raices,
    raices_del_cliente,
    respaldado,
)
from multiagente.core.esquemas.requerimiento import DatoEntrada, DatoSalida
from multiagente.llm.invocador import ErrorValidacionSalida, InvocadorNodo
from multiagente.orquestador.estado import Contexto, Conversacion, Emisor, RegistroCaptura
from multiagente.orquestador.servicios import Dialogo


class DatoEntradaModelo(BaseModel):
    """Dato de entrada tal como lo devuelve el modelo."""

    model_config = ConfigDict(extra="forbid")

    nombre: str
    tipo: str
    obligatorio: bool
    restriccion: str | None


class DatoSalidaModelo(BaseModel):
    """Dato de salida tal como lo devuelve el modelo."""

    model_config = ConfigDict(extra="forbid")

    nombre: str
    tipo: str
    formato: str | None


class ListaDelRegistro(StrEnum):
    """Listas del registro de las que la respuesta del cliente puede retirar entradas."""

    REGLAS_NEGOCIO = "reglas_negocio"
    DATOS_ENTRADA = "datos_entrada"
    DATOS_SALIDA = "datos_salida"
    EXCEPCIONES = "excepciones"


class RetiroModelo(BaseModel):
    """Entrada que la respuesta rechaza, como figura en el registro; de un dato, su nombre."""

    model_config = ConfigDict(extra="forbid")

    lista: ListaDelRegistro
    entrada: str


class SalidaExtraccion(BaseModel):
    """Salida de la extracción de N3: cambios al registro que aporta la respuesta nueva.

    En los atributos capturados, `null` significa «sin cambios». Los supuestos y las preguntas
    abiertas se devuelven siempre completos, porque el modelo los resuelve turno a turno.
    `retirar` trae lo que la respuesta rechaza sin decir el reemplazo (`retirar_rechazados`).
    """

    model_config = ConfigDict(extra="forbid")

    rol: str | None
    funcionalidad: str | None
    beneficio: str | None
    reglas_negocio: list[str] | None
    datos_entrada: list[DatoEntradaModelo] | None
    datos_salida: list[DatoSalidaModelo] | None
    excepciones: list[str] | None
    retirar: list[RetiroModelo]
    supuestos: list[str]
    preguntas_abiertas: list[str]
    confirma_resumen: bool


class SalidaPregunta(BaseModel):
    """Salida de la pregunta de N3."""

    model_config = ConfigDict(extra="forbid")

    siguiente_pregunta: str


D = TypeVar("D", DatoEntrada, DatoSalida)

PREGUNTA_CIERRE = "¿Es correcto o falta algo?"

ENCABEZADO_RESUMEN = "Le resumo lo que entendí:"
"""Primera línea del resumen que confirma el cliente."""

PREGUNTA_QUE_FALTA = "¿Qué falta o qué debo corregir del resumen?"
"""Pregunta cuando el cliente no confirma el resumen, pero tampoco dice qué cambiar."""
"""Pregunta con que cierra el resumen que el cliente confirma."""

TERMINOS_TECNICOS = re.compile(
    r"\b(?:endpoint|api|esquema|entidad(?:es)?|base de datos|json|backend|frontend"
    r"|microservicio|servidor|framework|sql|\w+_\w+)\b"
)
"""Términos técnicos e identificadores que no se usan con el cliente (eli-006, regla 2)."""

PIDE_CONFIRMAR = re.compile(r"\bresumen\b")
"""Señal de que la pregunta pide confirmar el resumen; confirmar un dato puntual sí se admite."""


def _transcripcion(conversacion: Conversacion) -> list[dict[str, str]]:
    return [{"emisor": turno.emisor.value, "texto": turno.texto} for turno in conversacion.turnos]


def mensajes_extraccion(conversacion: Conversacion) -> list[ChatCompletionMessageParam]:
    """Arma el mensaje de datos de la extracción: sin contexto de dominio.

    Args:
        conversacion: Conversación con la respuesta nueva del cliente.

    Returns:
        Un mensaje de datos que acompaña al prompt de extracción.
    """
    anteriores = [
        turno.texto
        for turno in conversacion.turnos[: conversacion.turnos_procesados]
        if turno.emisor is Emisor.ELICITADOR
    ]
    datos = {
        "registro": conversacion.registro.model_dump(mode="json"),
        "transcripcion": _transcripcion(conversacion),
        "pregunta_anterior": anteriores[-1] if anteriores else None,
        "respuesta_nueva": conversacion.respuesta_nueva,
    }
    return [{"role": "user", "content": json_texto(datos)}]


def mensajes_pregunta(
    conversacion: Conversacion, registro: RegistroCaptura, contexto: Contexto
) -> list[ChatCompletionMessageParam]:
    """Arma los mensajes de datos de la pregunta: el contexto etiquetado y el estado del diálogo.

    Args:
        conversacion: Conversación hasta la respuesta nueva.
        registro: Registro ya actualizado por la extracción.
        contexto: Contexto recuperado en N2.

    Returns:
        Dos mensajes de datos que acompañan al prompt de la pregunta.
    """
    estado = {
        "pendientes": registro.pendientes,
        "registro": registro.model_dump(mode="json"),
        "transcripcion": _transcripcion(conversacion),
        "observaciones_revisor": list(conversacion.observaciones_revisor),
    }
    return [mensaje_contexto(contexto), {"role": "user", "content": json_texto(estado)}]


def _texto(valor: str | None) -> str | None:
    limpio = valor.strip() if valor else ""
    return limpio or None


def _textos(valores: list[str] | None) -> tuple[str, ...]:
    return tuple(dict.fromkeys(limpio for valor in valores or () if (limpio := valor.strip())))


class _Filtro:
    """Acepta un texto si ya estaba en el registro o si lo respalda lo que dijo el cliente."""

    def __init__(self, fuente: set[str], previos: set[str]) -> None:
        self.fuente = fuente
        self.previos = {normalizar(texto) for texto in previos}

    def acepta(self, texto: str) -> bool:
        return normalizar(texto) in self.previos or respaldado(texto, self.fuente)


def registro_desde_salida(
    salida: SalidaExtraccion,
    previo: RegistroCaptura,
    fuente: set[str],
    solo_agregar: bool = False,
) -> RegistroCaptura:
    """Aplica los cambios de la salida al registro, sin perder lo ya capturado.

    Un atributo en `null` o vacío conserva el valor previo: el cliente corrige un dato diciendo
    el nuevo, no callándolo. Un valor nuevo que no está respaldado por lo que dijo el cliente se
    descarta, y un dato sin respaldo pierde su restricción o su formato. Los supuestos y las
    preguntas abiertas se toman tal cual, porque son notas del elicitador para el cliente.

    Args:
        salida: Salida del modelo.
        previo: Registro antes de este turno.
        fuente: Raíces léxicas de lo que dijo el cliente (`fidelidad.raices_del_cliente`).
        solo_agregar: Las listas conservan lo previo y solo suman lo nuevo respaldado. Se usa
            en la respuesta que confirma el resumen, para que una paráfrasis del modelo no
            cuente como cambio.

    Returns:
        Registro actualizado, con `resumen_confirmado` en False.
    """
    textos_previos = {
        texto
        for texto in (
            previo.rol,
            previo.funcionalidad,
            previo.beneficio,
            *previo.reglas_negocio,
            *previo.excepciones,
            *(dato.nombre for dato in previo.datos_entrada),
            *(dato.nombre for dato in previo.datos_salida),
            *(dato.restriccion for dato in previo.datos_entrada),
            *(dato.formato for dato in previo.datos_salida),
        )
        if texto
    }
    filtro = _Filtro(fuente, textos_previos)

    def escalar(valor: str | None) -> str | None:
        limpio = _texto(valor)
        return limpio if limpio and filtro.acepta(limpio) else None

    def lista(valores: list[str] | None, previos: tuple[str, ...]) -> tuple[str, ...]:
        nuevos = tuple(texto for texto in _textos(valores) if filtro.acepta(texto))
        if not solo_agregar:
            return nuevos or previos
        vistos = {normalizar(texto) for texto in previos}
        return (*previos, *(texto for texto in nuevos if normalizar(texto) not in vistos))

    def datos(nuevos: tuple[D, ...], previos: tuple[D, ...]) -> tuple[D, ...]:
        if not solo_agregar:
            return nuevos or previos
        # Un dato existente conserva todo, salvo la restricción o el formato que la respuesta
        # precise con respaldo; los datos nuevos se agregan al final.
        por_nombre = {normalizar(dato.nombre): dato for dato in nuevos}
        actualizados = []
        for previo_dato in previos:
            nuevo = por_nombre.pop(normalizar(previo_dato.nombre), None)
            precision = {
                campo: valor
                for campo in ("restriccion", "formato")
                if nuevo is not None
                and hasattr(previo_dato, campo)
                and (valor := getattr(nuevo, campo))
            }
            actualizados.append(previo_dato.model_copy(update=precision))
        return (*actualizados, *por_nombre.values())

    datos_entrada = tuple(
        DatoEntrada(
            nombre=dato.nombre,
            tipo=dato.tipo,
            obligatorio=dato.obligatorio,
            restriccion=escalar(dato.restriccion),
        )
        for dato in salida.datos_entrada or ()
        if dato.nombre.strip() and dato.tipo.strip() and filtro.acepta(dato.nombre)
    )
    datos_salida = tuple(
        DatoSalida(nombre=dato.nombre, tipo=dato.tipo, formato=escalar(dato.formato))
        for dato in salida.datos_salida or ()
        if dato.nombre.strip() and dato.tipo.strip() and filtro.acepta(dato.nombre)
    )
    return RegistroCaptura(
        rol=escalar(salida.rol) or previo.rol,
        funcionalidad=escalar(salida.funcionalidad) or previo.funcionalidad,
        beneficio=escalar(salida.beneficio) or previo.beneficio,
        reglas_negocio=lista(salida.reglas_negocio, previo.reglas_negocio),
        datos_entrada=datos(datos_entrada, previo.datos_entrada),
        datos_salida=datos(datos_salida, previo.datos_salida),
        excepciones=lista(salida.excepciones, previo.excepciones),
        supuestos=_textos(salida.supuestos),
        preguntas_abiertas=_textos(salida.preguntas_abiertas),
    )


def _clave(texto: str) -> str:
    """Palabras de un texto sin tildes, mayúsculas ni puntuación, para comparar entradas."""
    return " ".join(re.findall(r"\w+", normalizar(texto)))


def _menciona(respuesta: str, entrada: str) -> bool:
    """Indica si la respuesta habla de la entrada: comparte con ella al menos una raíz.

    Un nombre corto sin raíces, como «NIT», cuenta si la respuesta lo dice como palabra.
    """
    if propias := raices(entrada):
        return bool(propias & raices(respuesta))
    clave = _clave(entrada)
    return bool(clave) and re.search(rf"\b{re.escape(clave)}\b", _clave(respuesta)) is not None


def retirar_rechazados(
    registro: RegistroCaptura, retiros: list[RetiroModelo], respuesta: str
) -> RegistroCaptura:
    """Quita del registro lo que el cliente rechaza en su respuesta sin decir el reemplazo.

    Una entrada sale solo si figura en la lista indicada, tal como está en el registro, y la
    respuesta la menciona: lo que el modelo omite o retira sin que el cliente hable de ello se
    conserva. Si una lista queda vacía, el atributo vuelve a estar pendiente y N3 pregunta por él.

    Args:
        registro: Registro ya actualizado con la extracción del turno.
        retiros: Entradas que la extracción marcó para retirar.
        respuesta: Respuesta nueva del cliente.

    Returns:
        Registro sin las entradas retiradas.
    """
    quitar: dict[str, set[str]] = {}
    for retiro in retiros:
        if _menciona(respuesta, retiro.entrada):
            quitar.setdefault(retiro.lista.value, set()).add(_clave(retiro.entrada))
    cambios = {
        lista: tuple(
            entrada
            for entrada in getattr(registro, lista)
            if _clave(entrada if isinstance(entrada, str) else entrada.nombre) not in claves
        )
        for lista, claves in quitar.items()
    }
    return registro.model_copy(update=cambios)


def resumen_para_confirmar(registro: RegistroCaptura) -> str:
    """Arma el resumen del registro que el cliente confirma antes de cerrar (RNF-08, eli-006).

    Args:
        registro: Registro completo, pendiente solo de confirmación.

    Returns:
        Resumen en varias líneas, sin pregunta; el modelo aporta la pregunta de cierre.
    """

    def nombre(texto: str) -> str:
        return texto.replace("_", " ")

    entradas = "; ".join(
        f"{nombre(dato.nombre)} ({'obligatorio' if dato.obligatorio else 'opcional'}"
        f"{f', {dato.restriccion}' if dato.restriccion else ''})"
        for dato in registro.datos_entrada
    )
    salidas = "; ".join(
        f"{nombre(dato.nombre)}{f' ({dato.formato})' if dato.formato else ''}"
        for dato in registro.datos_salida
    )
    lineas = [
        ENCABEZADO_RESUMEN,
        f"- Quién lo usa: {registro.rol}",
        f"- Qué necesita: {registro.funcionalidad}",
        f"- Para qué: {registro.beneficio}",
        f"- Reglas: {'; '.join(registro.reglas_negocio)}",
        f"- Datos que se reciben: {entradas}",
        f"- Resultados que se entregan: {salidas}",
        f"- Casos de error: {'; '.join(registro.excepciones)}",
    ]
    if registro.supuestos:
        lineas.append(f"- Supuestos por confirmar: {'; '.join(registro.supuestos)}")
    if registro.preguntas_abiertas:
        lineas.append(f"- Preguntas abiertas: {'; '.join(registro.preguntas_abiertas)}")
    return "\n".join(lineas)


def _huella(registro: RegistroCaptura) -> str:
    """Información capturada del registro, sin mayúsculas, tildes ni espacios de sobra.

    Excluye la confirmación, los supuestos y las preguntas abiertas: al confirmar, el modelo
    puede dar por resueltos los supuestos que el cliente acaba de aceptar.
    """
    excluir = {"resumen_confirmado", "supuestos", "preguntas_abiertas"}
    texto = json.dumps(registro.model_dump(mode="json", exclude=excluir), ensure_ascii=False)
    return re.sub(r"\s+", " ", normalizar(texto))


def aplicar_extraccion(salida: SalidaExtraccion, conversacion: Conversacion) -> RegistroCaptura:
    """Aplica la extracción al registro con las reglas de fidelidad y de confirmación.

    Args:
        salida: Salida de la extracción.
        conversacion: Conversación con la que se invocó al modelo.

    Returns:
        Registro actualizado; confirmado solo si la respuesta nueva confirma un registro
        completo sin cambiarlo.
    """
    previo = conversacion.registro
    nueva = conversacion.respuesta_nueva
    if salida.confirma_resumen and nueva is not None:
        # Una respuesta que confirma solo aporta lo que dice ella misma.
        registro = registro_desde_salida(salida, previo, raices(nueva), solo_agregar=True)
    else:
        registro = registro_desde_salida(salida, previo, raices_del_cliente(conversacion))
        if nueva is not None:
            # Lo que rechaza sin reemplazo no se puede corregir diciendo el valor nuevo.
            registro = retirar_rechazados(registro, salida.retirar, nueva)
    if registro.preguntas_abiertas and not desconoce_algo(conversacion):
        registro = registro.model_copy(update={"preguntas_abiertas": ()})
    confirmado = (
        salida.confirma_resumen
        and nueva is not None
        and registro.pendientes == ["confirmacion"]
        and _huella(registro) == _huella(previo)
    )
    if confirmado:
        registro = RegistroCaptura.model_validate(
            {**registro.model_dump(), "resumen_confirmado": True}
        )
    return registro


def validar_pregunta(salida: SalidaPregunta, registro: RegistroCaptura) -> str:
    """Verifica la pregunta del modelo y antepone el resumen si solo falta confirmar.

    Args:
        salida: Salida de la pregunta.
        registro: Registro actualizado del turno.

    Returns:
        La pregunta que se muestra al cliente.

    Raises:
        ErrorValidacionSalida: Si la pregunta está vacía, no es una sola o usa términos
            técnicos.
    """
    pregunta = _texto(salida.siguiente_pregunta)
    problemas: list[str] = []
    if pregunta is None:
        problemas.append("Debes formular la siguiente pregunta.")
    else:
        if pregunta.count("?") != 1 or pregunta.count("¿") > 1:
            problemas.append(
                "La siguiente pregunta debe ser una sola, con un único signo de interrogación."
            )
        if tecnicos := sorted(set(TERMINOS_TECNICOS.findall(normalizar(pregunta)))):
            problemas.append(f"La pregunta usa términos técnicos con el cliente: {tecnicos}.")
        faltantes = [p for p in registro.pendientes if p != "confirmacion"]
        if faltantes and PIDE_CONFIRMAR.search(normalizar(pregunta)):
            problemas.append(
                f"Aún faltan {faltantes}: pregunta por el primero y no pidas confirmar el resumen."
            )
    if problemas:
        raise ErrorValidacionSalida(problemas)
    if registro.pendientes == ["confirmacion"]:
        return f"{resumen_para_confirmar(registro)}\n{pregunta}"
    return pregunta


def dialogar(
    extraccion: InvocadorNodo,
    pregunta: InvocadorNodo,
    conversacion: Conversacion,
    contexto: Contexto,
) -> Dialogo:
    """Ejecuta un paso del diálogo: extrae la respuesta nueva y formula la siguiente pregunta.

    Args:
        extraccion: Invocador del prompt de extracción de N3.
        pregunta: Invocador del prompt de pregunta de N3.
        conversacion: Conversación con la respuesta nueva del cliente, si la hay.
        contexto: Contexto recuperado en N2.

    Returns:
        Registro actualizado y siguiente pregunta, o None si la elicitación terminó.
    """
    registro = conversacion.registro
    nueva = conversacion.respuesta_nueva
    if nueva is not None:
        registro = extraccion.invocar_validado(
            mensajes_extraccion(conversacion),
            SalidaExtraccion,
            lambda salida: aplicar_extraccion(salida, conversacion),
        )
    if not registro.pendientes:
        return Dialogo(registro=registro, siguiente_pregunta=None)
    if registro.pendientes == ["confirmacion"] and nueva is not None:
        preguntas = [t.texto for t in conversacion.turnos if t.emisor is Emisor.ELICITADOR]
        anterior = preguntas[-1] if preguntas else ""
        if anterior.startswith(ENCABEZADO_RESUMEN) and _huella(registro) == _huella(
            conversacion.registro
        ):
            # «Falta algo» sin decir qué: repetir el mismo resumen no ayuda al cliente.
            return Dialogo(registro=registro, siguiente_pregunta=PREGUNTA_QUE_FALTA)
        resumen = f"{resumen_para_confirmar(registro)}\n{PREGUNTA_CIERRE}"
        return Dialogo(registro=registro, siguiente_pregunta=resumen)
    siguiente = pregunta.invocar_validado(
        mensajes_pregunta(conversacion, registro, contexto),
        SalidaPregunta,
        lambda salida: validar_pregunta(salida, registro),
    )
    return Dialogo(registro=registro, siguiente_pregunta=siguiente)
