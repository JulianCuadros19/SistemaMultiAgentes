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
  no saber algo. La respuesta a un caso límite o a la pregunta por algo más no agrega preguntas
  abiertas: el cliente no tiene por qué conocer cada situación especial;
- el resumen solo queda confirmado con una respuesta nueva del cliente, con el registro completo
  y sin cambios respecto del resumen que se le presentó;
- lo que el cliente no sabe no se pregunta sin fin: tras `INTENTOS_SIN_RESPUESTA` respuestas en
  que dice no saber el atributo que se le preguntaba, queda sin respuesta (RF-02);
- hay pregunta si y solo si queda algo por preguntar, y es una sola, en lenguaje de negocio
  (RNF-08);
- con los atributos completos, antes del resumen, se pregunta por casos límite, una categoría de
  dom-007 por pregunta y sin repetirla, hasta `MAX_PREGUNTAS_CASOS_LIMITE`, y después, una vez,
  si hay algo importante que no se preguntó (ADR-0015);
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
    dice_no_saber,
    raices,
    raices_del_cliente,
    respaldado,
)
from multiagente.core.esquemas.comunes import Prioridad
from multiagente.core.esquemas.requerimiento import DatoEntrada, DatoSalida
from multiagente.llm.invocador import ErrorValidacionSalida, InvocadorNodo
from multiagente.orquestador.estado import (
    CategoriaCasoLimite,
    Contexto,
    Conversacion,
    Emisor,
    RegistroCaptura,
)
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
    CONDICIONES = "condiciones"
    CASOS_LIMITE = "casos_limite"
    EJEMPLOS = "ejemplos"


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
    condiciones: list[str] | None
    casos_limite: list[str] | None
    ejemplos: list[str] | None
    prioridad: Prioridad | None
    retirar: list[RetiroModelo]
    supuestos: list[str]
    preguntas_abiertas: list[str]
    confirma_resumen: bool


class SalidaPregunta(BaseModel):
    """Salida de la pregunta de N3.

    En la fase de casos límite, `categoria_caso_limite` es el patrón de dom-007 por el que se
    pregunta, y `sin_mas_casos_limite` indica que ninguna categoría que falte aplica a la
    necesidad: entonces no hay pregunta y sigue el resumen.
    """

    model_config = ConfigDict(extra="forbid")

    siguiente_pregunta: str
    categoria_caso_limite: CategoriaCasoLimite | None
    sin_mas_casos_limite: bool


D = TypeVar("D", DatoEntrada, DatoSalida)

PREGUNTA_CIERRE = "¿Es correcto? Si falta algo o hay algo que corregir, dígamelo todo de una vez."
"""Pregunta con que cierra el resumen que el cliente confirma.

Pide todas las correcciones en una respuesta: de a una, el resumen se repite hasta agotar los
turnos (ADR-0015).
"""

ENCABEZADO_RESUMEN = "Le resumo lo que entendí:"
"""Primera línea del resumen que confirma el cliente."""

PREGUNTA_ALGO_MAS = (
    "Antes de resumir, ¿hay algo importante que no le haya preguntado, como la prioridad, los "
    "mensajes exactos de error, el formato de los valores o un ejemplo con cifras para verificar?"
)
"""Pregunta de cierre de eli-006 antes del resumen: reúne en un turno lo que nadie preguntó."""

AVISO_SISTEMAS = "los sistemas o procesos que lo usan aparecen en «Condiciones ya definidas»"
"""Aviso del resumen junto al rol: dónde quedan los sistemas o procesos que usan lo pedido."""

MIN_PREGUNTAS_CASOS_LIMITE = 1
"""Preguntas por casos límite antes de que el modelo pueda dar la fase por terminada."""

COBERTURA_MINIMA = 2 / 3
"""Fracción de las raíces de una entrada que un texto debe repetir para hablar de ella.

Con la mitad, dos palabras frecuentes del dominio bastaban: una respuesta sobre los valores por
defecto «hablaba» de «un archivo modificado hoy nunca se comprime» (casos 06 y 15, ADR-0015).
"""

TERMINOS_TECNICOS = re.compile(
    r"\b(?:endpoint|api|esquema|entidad(?:es)?|base de datos|json|backend|frontend"
    r"|microservicio|servidor|framework|sql|\w+_\w+)\b"
)
"""Términos técnicos e identificadores que no se usan con el cliente (eli-006, regla 2)."""

PIDE_CONFIRMAR = re.compile(r"\bresumen\b")
"""Señal de que la pregunta pide confirmar el resumen; confirmar un dato puntual sí se admite."""


CONTROL_DEL_REGISTRO = frozenset(
    {
        "no_sabe",
        "categorias_casos_limite",
        "caso_limite_preguntado",
        "casos_limite_cerrados",
        "algo_mas_preguntado",
    }
)
"""Campos del registro que lleva el código para conducir el diálogo, no lo que dijo el cliente."""


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
        "registro": conversacion.registro.model_dump(mode="json", exclude=CONTROL_DEL_REGISTRO),
        "transcripcion": _transcripcion(conversacion),
        "pregunta_anterior": anteriores[-1] if anteriores else None,
        "caso_limite_preguntado": conversacion.registro.caso_limite_preguntado,
        "respuesta_nueva": conversacion.respuesta_nueva,
    }
    return [{"role": "user", "content": json_texto(datos)}]


def mensajes_pregunta(
    conversacion: Conversacion,
    registro: RegistroCaptura,
    contexto: Contexto,
    resumen_incompleto: bool = False,
) -> list[ChatCompletionMessageParam]:
    """Arma los mensajes de datos de la pregunta: el contexto etiquetado y el estado del diálogo.

    Args:
        conversacion: Conversación hasta la respuesta nueva.
        registro: Registro ya actualizado por la extracción.
        contexto: Contexto recuperado en N2.
        resumen_incompleto: El cliente acaba de responder al resumen que falta algo o que algo
            no es correcto, sin decir qué.

    Returns:
        Dos mensajes de datos que acompañan al prompt de la pregunta.
    """
    estado = {
        "pendientes": registro.por_preguntar,
        "resumen_incompleto": resumen_incompleto,
        "sin_respuesta": registro.sin_respuesta,
        "categorias_casos_limite_preguntadas": list(registro.categorias_casos_limite),
        "registro": registro.model_dump(mode="json", exclude=CONTROL_DEL_REGISTRO),
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
    respuesta: str | None = None,
) -> RegistroCaptura:
    """Aplica los cambios de la salida al registro, sin perder lo ya capturado.

    Un atributo en `null` o vacío conserva el valor previo: el cliente corrige un dato diciendo
    el nuevo, no callándolo. Una lista parcial tampoco borra lo que omite: los datos se combinan
    por nombre, y una entrada de texto que el modelo no devuelve sigue vigente, salvo que una
    entrada nueva la reformule o que la respuesta hable de ella (ADR-0015). Un valor nuevo que
    no está respaldado por lo que dijo el cliente se descarta, y un dato sin respaldo pierde su
    restricción o su formato; la prioridad también debe decirla el cliente. Los supuestos y las
    preguntas abiertas se toman tal cual, porque son notas del elicitador para el cliente. Lo que
    el cliente no supo responder se conserva.

    Args:
        salida: Salida del modelo.
        previo: Registro antes de este turno.
        fuente: Raíces léxicas de lo que dijo el cliente (`fidelidad.raices_del_cliente`).
        solo_agregar: Las listas conservan lo previo y solo suman lo nuevo respaldado. Se usa
            en la respuesta que confirma el resumen, para que una paráfrasis del modelo no
            cuente como cambio.
        respuesta: Respuesta nueva del cliente; las entradas de las que habla (`_habla_de`)
            pueden cambiar o salir de la lista. Si se omite, la lista que devuelve el modelo es
            la vigente.

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
            *previo.condiciones,
            *previo.casos_limite,
            *previo.ejemplos,
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
        if not nuevos:
            return previos
        if solo_agregar:
            vistos = {normalizar(texto) for texto in previos}
            return (*previos, *(texto for texto in nuevos if normalizar(texto) not in vistos))
        if respuesta is None:
            return nuevos
        # Una entrada que el modelo no devolvió sigue vigente, salvo que una entrada nueva la
        # reformule, que la reemplaza en su lugar, o que la respuesta hable de ella: cambió o
        # salió.
        previas = {normalizar(texto) for texto in previos}
        devueltas = {normalizar(texto) for texto in nuevos}
        agregadas = [texto for texto in nuevos if normalizar(texto) not in previas]
        vigentes: list[str] = []
        for texto in previos:
            if normalizar(texto) in devueltas:
                vigentes.append(texto)
            elif reformulada := next((n for n in agregadas if _habla_de(n, texto)), None):
                if reformulada not in vigentes:
                    vigentes.append(reformulada)
            elif not _habla_de(respuesta, texto):
                vigentes.append(texto)
        return (*vigentes, *(texto for texto in agregadas if texto not in vigentes))

    def datos(nuevos: tuple[D, ...], previos: tuple[D, ...]) -> tuple[D, ...]:
        # Los datos se combinan por nombre: una lista parcial no borra los que no menciona, que
        # solo salen si el cliente los retira (`retirar_rechazados`). Un dato que la respuesta
        # trae reemplaza al previo; al confirmar, solo precisa su restricción o su formato.
        por_nombre = {normalizar(dato.nombre): dato for dato in nuevos}
        actualizados = []
        for previo_dato in previos:
            nuevo = por_nombre.pop(normalizar(previo_dato.nombre), None)
            if nuevo is None:
                actualizados.append(previo_dato)
            elif not solo_agregar:
                actualizados.append(nuevo)
            else:
                precision = {
                    campo: valor
                    for campo in ("restriccion", "formato")
                    if hasattr(previo_dato, campo) and (valor := getattr(nuevo, campo))
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
    prioridad = (
        salida.prioridad if salida.prioridad and respaldado(salida.prioridad, fuente) else None
    )
    return RegistroCaptura(
        rol=escalar(salida.rol) or previo.rol,
        funcionalidad=escalar(salida.funcionalidad) or previo.funcionalidad,
        beneficio=escalar(salida.beneficio) or previo.beneficio,
        reglas_negocio=lista(salida.reglas_negocio, previo.reglas_negocio),
        datos_entrada=datos(datos_entrada, previo.datos_entrada),
        datos_salida=datos(datos_salida, previo.datos_salida),
        excepciones=lista(salida.excepciones, previo.excepciones),
        condiciones=lista(salida.condiciones, previo.condiciones),
        casos_limite=lista(salida.casos_limite, previo.casos_limite),
        ejemplos=lista(salida.ejemplos, previo.ejemplos),
        prioridad=prioridad or previo.prioridad,
        supuestos=_textos(salida.supuestos),
        preguntas_abiertas=_textos(salida.preguntas_abiertas),
        no_sabe=previo.no_sabe,
        # La respuesta ya atendió la pregunta de caso límite, si la había.
        categorias_casos_limite=previo.categorias_casos_limite,
        caso_limite_preguntado=None,
        casos_limite_cerrados=previo.casos_limite_cerrados,
        algo_mas_preguntado=previo.algo_mas_preguntado,
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


def _habla_de(texto: str, entrada: str) -> bool:
    """Indica si un texto habla de una entrada: repite dos tercios de sus raíces, y al menos dos.

    A una entrada de una sola raíz le basta esa. Con más, compartir una no basta: «el tipo solo
    puede ser ESC, CER o PAZ» no habla de «el tipo en minúsculas se corrige a mayúsculas». Una
    entrada sin raíces, como «NIT», cuenta si el texto la dice como palabra.
    """
    propias = raices(entrada)
    if not propias:
        return _menciona(texto, entrada)
    comunes = len(propias & raices(texto))
    return comunes >= max(min(2, len(propias)), COBERTURA_MINIMA * len(propias))


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


def anotar_desconocimiento(
    previo: RegistroCaptura, registro: RegistroCaptura, respuesta: str
) -> RegistroCaptura:
    """Anota que el cliente no supo responder el atributo que se le preguntaba.

    La pregunta apunta al primer atributo que quedaba por preguntar. Si la respuesta dice no
    saber y ese atributo sigue faltando, se anota en `no_sabe`; tras `INTENTOS_SIN_RESPUESTA`
    veces queda sin respuesta y N3 deja de preguntarlo, porque ya está respondido (RF-02).

    Args:
        previo: Registro antes de este turno.
        registro: Registro ya actualizado con la extracción del turno.
        respuesta: Respuesta nueva del cliente.

    Returns:
        Registro con el atributo anotado, o el mismo registro si no hay nada que anotar.
    """
    preguntado = previo.por_preguntar[0] if previo.por_preguntar else "confirmacion"
    if preguntado in ("confirmacion", "casos_limite", "algo_mas") or (
        preguntado not in registro.pendientes
    ):
        return registro
    if not dice_no_saber(respuesta):
        return registro
    return registro.model_copy(update={"no_sabe": (*registro.no_sabe, preguntado)})


SIN_RESPUESTA = "sin respuesta del cliente"
"""Lo que muestra el resumen en un atributo que el cliente no supo responder."""


def resumen_para_confirmar(registro: RegistroCaptura) -> str:
    """Arma el resumen del registro que el cliente confirma antes de cerrar (RNF-08, eli-006).

    Los datos se nombran como quedaron en el registro, que es como los nombró el cliente: si dio
    nombres exactos, como `numero_predial`, debe poder reconocerlos para confirmar.

    Args:
        registro: Registro completo, pendiente solo de confirmación; lo que el cliente no supo
            responder se muestra como tal.

    Returns:
        Resumen en varias líneas, sin pregunta; el modelo aporta la pregunta de cierre.
    """

    def valor(texto: str | None) -> str:
        return texto or SIN_RESPUESTA

    # Cada dato con su tipo: el cliente lo verifica, y sin él pide precisarlo una y otra vez.
    entradas = "; ".join(
        f"{dato.nombre} ({dato.tipo}, {'obligatorio' if dato.obligatorio else 'opcional'}"
        f"{f', {dato.restriccion}' if dato.restriccion else ''})"
        for dato in registro.datos_entrada
    )
    salidas = "; ".join(
        f"{dato.nombre} ({dato.tipo}{f', {dato.formato}' if dato.formato else ''})"
        for dato in registro.datos_salida
    )
    rol = valor(registro.rol)
    if registro.condiciones:
        # El rol es quién obtiene el valor (eli-001); los sistemas que lo usan son condiciones. Sin
        # decírselo, el cliente pide el sistema en esta línea hasta agotar los turnos (ADR-0015).
        rol += f" ({AVISO_SISTEMAS})"
    lineas = [
        ENCABEZADO_RESUMEN,
        f"- A quién le sirve: {rol}",
        f"- Qué necesita: {valor(registro.funcionalidad)}",
        f"- Para qué: {valor(registro.beneficio)}",
        f"- Reglas: {valor('; '.join(registro.reglas_negocio))}",
        f"- Datos que se reciben: {valor(entradas)}",
        f"- Resultados que se entregan: {valor(salidas)}",
        f"- Casos de error: {valor('; '.join(registro.excepciones))}",
    ]
    if registro.condiciones:
        lineas.append(f"- Condiciones ya definidas: {'; '.join(registro.condiciones)}")
    if registro.casos_limite:
        lineas.append(f"- Casos especiales acordados: {'; '.join(registro.casos_limite)}")
    if registro.ejemplos:
        lineas.append(f"- Ejemplos para verificar: {'; '.join(registro.ejemplos)}")
    if registro.prioridad:
        lineas.append(f"- Prioridad: {registro.prioridad}")
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
    excluir = {"resumen_confirmado", "supuestos", "preguntas_abiertas", *CONTROL_DEL_REGISTRO}
    texto = json.dumps(registro.model_dump(mode="json", exclude=excluir), ensure_ascii=False)
    return re.sub(r"\s+", " ", normalizar(texto))


def _respondio_exploracion(conversacion: Conversacion) -> bool:
    """Si la respuesta nueva contesta un caso límite o la pregunta por algo más."""
    if conversacion.respuesta_nueva is None:
        return False
    preguntas = [t.texto for t in conversacion.turnos if t.emisor is Emisor.ELICITADOR]
    return conversacion.registro.caso_limite_preguntado is not None or (
        bool(preguntas) and preguntas[-1] == PREGUNTA_ALGO_MAS
    )


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
        registro = registro_desde_salida(
            salida, previo, raices_del_cliente(conversacion), respuesta=nueva
        )
        if nueva is not None:
            # Lo que rechaza sin reemplazo no se puede corregir diciendo el valor nuevo.
            registro = retirar_rechazados(registro, salida.retirar, nueva)
            registro = anotar_desconocimiento(previo, registro, nueva)
    if registro.preguntas_abiertas and not desconoce_algo(conversacion):
        registro = registro.model_copy(update={"preguntas_abiertas": ()})
    if _respondio_exploracion(conversacion):
        # Lo que el cliente no sabe de una situación especial no bloquea los requerimientos.
        registro = registro.model_copy(update={"preguntas_abiertas": previo.preguntas_abiertas})
    confirmado = (
        salida.confirma_resumen
        and nueva is not None
        and registro.por_preguntar == ["confirmacion"]
        and _huella(registro) == _huella(previo)
    )
    if confirmado:
        registro = RegistroCaptura.model_validate(
            {**registro.model_dump(), "resumen_confirmado": True}
        )
    return registro


def _problemas_de_pregunta(pregunta: str | None, registro: RegistroCaptura) -> list[str]:
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
        faltantes = [p for p in registro.por_preguntar if p != "confirmacion"]
        if faltantes and PIDE_CONFIRMAR.search(normalizar(pregunta)):
            problemas.append(
                f"Aún faltan {faltantes}: pregunta por el primero y no pidas confirmar el resumen."
            )
    return problemas


def validar_pregunta(
    salida: SalidaPregunta, registro: RegistroCaptura, con_resumen: bool = True
) -> str:
    """Verifica la pregunta del modelo y antepone el resumen si solo falta confirmar.

    Args:
        salida: Salida de la pregunta.
        registro: Registro actualizado del turno.
        con_resumen: Si se antepone el resumen cuando solo falta confirmar; no, cuando la
            pregunta pide lo que el cliente dijo que falta en el resumen.

    Returns:
        La pregunta que se muestra al cliente.

    Raises:
        ErrorValidacionSalida: Si la pregunta está vacía, no es una sola o usa términos
            técnicos.
    """
    pregunta = _texto(salida.siguiente_pregunta)
    problemas = _problemas_de_pregunta(pregunta, registro)
    if problemas or pregunta is None:
        raise ErrorValidacionSalida(problemas)
    if con_resumen and registro.por_preguntar == ["confirmacion"]:
        return f"{resumen_para_confirmar(registro)}\n{pregunta}"
    return pregunta


def validar_caso_limite(
    salida: SalidaPregunta, registro: RegistroCaptura
) -> tuple[str, CategoriaCasoLimite] | None:
    """Verifica la pregunta de un caso límite: una sola, con una categoría que no se preguntó.

    Args:
        salida: Salida de la pregunta.
        registro: Registro actualizado del turno, con la fase de casos límite abierta.

    Returns:
        La pregunta y su categoría, o None si el modelo indica que ninguna categoría que falte
        aplica a la necesidad.

    Raises:
        ErrorValidacionSalida: Si la pregunta no cumple las reglas de una pregunta, falta la
            categoría o la categoría ya se preguntó.
    """
    if salida.sin_mas_casos_limite and (
        len(registro.categorias_casos_limite) >= MIN_PREGUNTAS_CASOS_LIMITE
    ):
        return None
    if salida.sin_mas_casos_limite:
        raise ErrorValidacionSalida(
            [
                "Pregunta al menos por un caso límite antes de pasar al resumen: elige la "
                "categoría que más aplique a las reglas del registro."
            ]
        )
    pregunta = _texto(salida.siguiente_pregunta)
    problemas = _problemas_de_pregunta(pregunta, registro)
    categoria = salida.categoria_caso_limite
    if categoria is None:
        problemas.append(
            "Indica en categoria_caso_limite el patrón por el que preguntas, o marca "
            "sin_mas_casos_limite si ninguno aplica."
        )
    elif categoria in registro.categorias_casos_limite:
        preguntadas = ", ".join(registro.categorias_casos_limite)
        problemas.append(
            f"Ya preguntaste por la categoría «{categoria}» ({preguntadas}): elige otra o marca "
            "sin_mas_casos_limite."
        )
    if problemas or pregunta is None or categoria is None:
        raise ErrorValidacionSalida(problemas)
    return pregunta, categoria


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
    if registro.explora_casos_limite:
        caso = pregunta.invocar_validado(
            mensajes_pregunta(conversacion, registro, contexto),
            SalidaPregunta,
            lambda salida: validar_caso_limite(salida, registro),
        )
        if caso is not None:
            texto, categoria = caso
            registro = registro.model_copy(
                update={
                    "categorias_casos_limite": (*registro.categorias_casos_limite, categoria),
                    "caso_limite_preguntado": categoria,
                }
            )
            return Dialogo(registro=registro, siguiente_pregunta=texto)
        registro = registro.model_copy(update={"casos_limite_cerrados": True})
    if registro.por_preguntar[:1] == ["algo_mas"]:
        registro = registro.model_copy(update={"algo_mas_preguntado": True})
        return Dialogo(registro=registro, siguiente_pregunta=PREGUNTA_ALGO_MAS)
    if not registro.por_preguntar:
        return Dialogo(registro=registro, siguiente_pregunta=None)
    if registro.por_preguntar == ["confirmacion"] and nueva is not None:
        preguntas = [t.texto for t in conversacion.turnos if t.emisor is Emisor.ELICITADOR]
        anterior = preguntas[-1] if preguntas else ""
        if anterior.startswith(ENCABEZADO_RESUMEN) and _huella(registro) == _huella(
            conversacion.registro
        ):
            # «Falta algo» sin darlo: repetir el mismo resumen no ayuda. El modelo pregunta
            # específicamente por lo que el cliente dijo que falta.
            especifica = pregunta.invocar_validado(
                mensajes_pregunta(conversacion, registro, contexto, resumen_incompleto=True),
                SalidaPregunta,
                lambda salida: validar_pregunta(salida, registro, con_resumen=False),
            )
            return Dialogo(registro=registro, siguiente_pregunta=especifica)
        resumen = f"{resumen_para_confirmar(registro)}\n{PREGUNTA_CIERRE}"
        return Dialogo(registro=registro, siguiente_pregunta=resumen)
    siguiente = pregunta.invocar_validado(
        mensajes_pregunta(conversacion, registro, contexto),
        SalidaPregunta,
        lambda salida: validar_pregunta(salida, registro),
    )
    return Dialogo(registro=registro, siguiente_pregunta=siguiente)
