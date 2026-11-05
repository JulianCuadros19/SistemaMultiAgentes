"""Aplicación WSGI con dos operaciones HTTP y respuestas JSON."""

import json
from typing import BinaryIO, cast
from wsgiref.types import StartResponse, WSGIEnvironment

from nit_service.dominio import NitInvalido, calcular_digito, validar_nit

_RUTAS = {"/calcular", "/validar"}


class _SolicitudInvalida(ValueError):
    """Represente un error de formato en la solicitud HTTP."""


def _leer_json(environ: WSGIEnvironment) -> dict[str, object]:
    contenido_tipo = str(environ.get("CONTENT_TYPE", ""))
    if contenido_tipo.split(";", 1)[0].strip().lower() != "application/json":
        raise _SolicitudInvalida("La solicitud debe usar Content-Type application/json")
    try:
        longitud = int(environ.get("CONTENT_LENGTH") or "0")
    except (TypeError, ValueError) as error:
        raise _SolicitudInvalida("Content-Length inválido") from error
    if longitud < 0:
        raise _SolicitudInvalida("Content-Length inválido")
    entrada = cast(BinaryIO, environ["wsgi.input"])
    cuerpo = entrada.read(longitud)
    try:
        datos = json.loads(cuerpo.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _SolicitudInvalida("El cuerpo debe ser JSON válido en UTF-8") from error
    if not isinstance(datos, dict):
        raise _SolicitudInvalida("El cuerpo debe ser un objeto JSON")
    return cast(dict[str, object], datos)


def _procesar(ruta: str, datos: dict[str, object]) -> dict[str, object]:
    campos = {"nit"} if ruta == "/calcular" else {"nit", "digito"}
    if set(datos) != campos:
        nombres = ", ".join(sorted(campos))
        raise _SolicitudInvalida(f"Campos requeridos y únicos: {nombres}")
    nit = datos["nit"]
    if not isinstance(nit, str):
        raise NitInvalido("El NIT debe ser texto")
    if ruta == "/calcular":
        return {"digito": calcular_digito(nit)}
    digito = datos["digito"]
    if not isinstance(digito, str):
        raise NitInvalido("El dígito de verificación debe ser un único dígito de texto")
    valido, esperado = validar_nit(nit, digito)
    return {"valido": valido, "digito_esperado": esperado}


def _responder(
    start_response: StartResponse,
    estado: str,
    datos: dict[str, object],
    adicionales: list[tuple[str, str]] | None = None,
) -> list[bytes]:
    cuerpo = json.dumps(datos, ensure_ascii=False, allow_nan=False).encode("utf-8")
    cabeceras = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(cuerpo))),
    ]
    if adicionales:
        cabeceras.extend(adicionales)
    start_response(estado, cabeceras)
    return [cuerpo]


def application(environ: WSGIEnvironment, start_response: StartResponse) -> list[bytes]:
    """Atienda una solicitud WSGI de cálculo o validación.

    Args:
        environ: Entorno de solicitud proporcionado por el servidor WSGI.
        start_response: Función del servidor para establecer estado y cabeceras.

    Returns:
        Cuerpo JSON codificado en UTF-8 como iterable de bytes.
    """
    ruta = str(environ.get("PATH_INFO", ""))
    if ruta not in _RUTAS:
        return _responder(start_response, "404 Not Found", {"error": "Ruta no encontrada"})
    if environ.get("REQUEST_METHOD") != "POST":
        return _responder(
            start_response,
            "405 Method Not Allowed",
            {"error": "Método no permitido; use POST"},
            [("Allow", "POST")],
        )
    try:
        resultado = _procesar(ruta, _leer_json(environ))
    except (NitInvalido, _SolicitudInvalida) as error:
        return _responder(start_response, "400 Bad Request", {"error": str(error)})
    return _responder(start_response, "200 OK", resultado)
