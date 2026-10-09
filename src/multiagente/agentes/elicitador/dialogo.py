"""Diálogo de elicitación (N3): extrae lo que dijo el cliente y formula la siguiente pregunta.

El modelo devuelve el registro completo actualizado y la siguiente pregunta. El código, no el
prompt, garantiza las reglas que deben cumplirse siempre:

- lo ya capturado no se pierde por omisión del modelo;
- el resumen solo queda confirmado con una respuesta nueva del cliente, con el registro completo
  y sin cambios respecto del resumen que se le presentó;
- hay pregunta si y solo si falta algo, y es una sola, en lenguaje de negocio (RNF-08).
"""

import json
import re

from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, ConfigDict

from multiagente.agentes.elicitador.calidad import normalizar
from multiagente.agentes.elicitador.contexto import json_texto, mensaje_contexto
from multiagente.core.esquemas.requerimiento import DatoEntrada, DatoSalida
from multiagente.llm.invocador import ErrorValidacionSalida
from multiagente.orquestador.estado import Contexto, Conversacion, RegistroCaptura
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


class SalidaDialogo(BaseModel):
    """Salida estructurada de N3: registro completo actualizado y siguiente pregunta."""

    model_config = ConfigDict(extra="forbid")

    rol: str | None
    funcionalidad: str | None
    beneficio: str | None
    reglas_negocio: list[str]
    datos_entrada: list[DatoEntradaModelo]
    datos_salida: list[DatoSalidaModelo]
    excepciones: list[str]
    supuestos: list[str]
    preguntas_abiertas: list[str]
    confirma_resumen: bool
    siguiente_pregunta: str | None


TERMINOS_TECNICOS = re.compile(
    r"\b(?:endpoint|api|esquema|entidad(?:es)?|base de datos|json|backend|frontend"
    r"|microservicio|servidor|framework|sql)\b"
)
"""Términos técnicos que no se usan con el cliente (eli-006, regla 2)."""


def mensajes_dialogo(
    conversacion: Conversacion, contexto: Contexto
) -> list[ChatCompletionMessageParam]:
    """Arma los mensajes de datos de N3: el contexto etiquetado y el estado del diálogo.

    Args:
        conversacion: Conversación con la respuesta nueva del cliente, si la hay.
        contexto: Contexto recuperado en N2.

    Returns:
        Dos mensajes de datos que acompañan al prompt de sistema.
    """
    estado = {
        "pendientes": conversacion.registro.pendientes,
        "registro": conversacion.registro.model_dump(mode="json"),
        "transcripcion": [
            {"emisor": turno.emisor.value, "texto": turno.texto} for turno in conversacion.turnos
        ],
        "respuesta_nueva": conversacion.respuesta_nueva,
        "observaciones_revisor": list(conversacion.observaciones_revisor),
    }
    return [mensaje_contexto(contexto), {"role": "user", "content": json_texto(estado)}]


def _texto(valor: str | None) -> str | None:
    limpio = valor.strip() if valor else ""
    return limpio or None


def _textos(valores: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(limpio for valor in valores if (limpio := valor.strip())))


def registro_desde_salida(salida: SalidaDialogo, previo: RegistroCaptura) -> RegistroCaptura:
    """Construye el registro sin confirmar a partir de la salida, sin perder lo ya capturado.

    Un atributo que el modelo deja vacío conserva el valor previo: el cliente corrige un dato
    diciendo el nuevo, no callándolo. Los supuestos y las preguntas abiertas se toman tal cual,
    porque el modelo los resuelve a medida que el cliente responde.

    Args:
        salida: Salida del modelo.
        previo: Registro antes de este turno.

    Returns:
        Registro actualizado, con `resumen_confirmado` en False.
    """
    datos_entrada = tuple(
        DatoEntrada(
            nombre=dato.nombre,
            tipo=dato.tipo,
            obligatorio=dato.obligatorio,
            restriccion=_texto(dato.restriccion),
        )
        for dato in salida.datos_entrada
        if dato.nombre.strip() and dato.tipo.strip()
    )
    datos_salida = tuple(
        DatoSalida(nombre=dato.nombre, tipo=dato.tipo, formato=_texto(dato.formato))
        for dato in salida.datos_salida
        if dato.nombre.strip() and dato.tipo.strip()
    )
    return RegistroCaptura(
        rol=_texto(salida.rol) or previo.rol,
        funcionalidad=_texto(salida.funcionalidad) or previo.funcionalidad,
        beneficio=_texto(salida.beneficio) or previo.beneficio,
        reglas_negocio=_textos(salida.reglas_negocio) or previo.reglas_negocio,
        datos_entrada=datos_entrada or previo.datos_entrada,
        datos_salida=datos_salida or previo.datos_salida,
        excepciones=_textos(salida.excepciones) or previo.excepciones,
        supuestos=_textos(salida.supuestos),
        preguntas_abiertas=_textos(salida.preguntas_abiertas),
    )


def _huella(registro: RegistroCaptura) -> str:
    """Información capturada del registro, sin mayúsculas, tildes ni espacios de sobra.

    Excluye la confirmación, los supuestos y las preguntas abiertas: al confirmar, el modelo
    puede dar por resueltos los supuestos que el cliente acaba de aceptar.
    """
    excluir = {"resumen_confirmado", "supuestos", "preguntas_abiertas"}
    texto = json.dumps(registro.model_dump(mode="json", exclude=excluir), ensure_ascii=False)
    return re.sub(r"\s+", " ", normalizar(texto))


def validar_dialogo(salida: SalidaDialogo, conversacion: Conversacion) -> Dialogo:
    """Aplica las reglas del diálogo a la salida del modelo.

    Args:
        salida: Salida del modelo.
        conversacion: Conversación con la que se invocó al modelo.

    Returns:
        Registro actualizado y siguiente pregunta.

    Raises:
        ErrorValidacionSalida: Si falta la pregunta cuando quedan pendientes, si la pregunta no
            es una sola o si usa términos técnicos.
    """
    previo = conversacion.registro
    registro = registro_desde_salida(salida, previo)
    solo_falta_confirmar = registro.pendientes == ["confirmacion"]
    sin_cambios = _huella(registro) == _huella(previo)
    hay_respuesta = conversacion.respuesta_nueva is not None
    confirmado = salida.confirma_resumen and hay_respuesta and solo_falta_confirmar and sin_cambios
    if confirmado:
        registro = RegistroCaptura.model_validate(
            {**registro.model_dump(), "resumen_confirmado": True}
        )

    problemas: list[str] = []
    pregunta = _texto(salida.siguiente_pregunta)
    if not registro.pendientes:
        pregunta = None
    elif pregunta is None:
        motivo = f"Quedan pendientes {registro.pendientes} y no formulaste la siguiente pregunta."
        if salida.confirma_resumen and not confirmado:
            if not hay_respuesta:
                motivo += " La confirmación exige una respuesta nueva del cliente."
            elif not solo_falta_confirmar:
                motivo += " No se puede confirmar un resumen con atributos faltantes."
            else:
                motivo += (
                    " El registro cambió respecto del resumen presentado: presenta el resumen "
                    "actualizado y pide de nuevo la confirmación."
                )
        problemas.append(motivo)
    else:
        if pregunta.count("?") != 1:
            problemas.append(
                "La siguiente pregunta debe ser una sola, con un único signo de interrogación."
            )
        if tecnicos := sorted(set(TERMINOS_TECNICOS.findall(normalizar(pregunta)))):
            problemas.append(f"La pregunta usa términos técnicos con el cliente: {tecnicos}.")
    if problemas:
        raise ErrorValidacionSalida(problemas)
    return Dialogo(registro=registro, siguiente_pregunta=pregunta)
