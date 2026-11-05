"""Servicio HTTP JSON implementado con la biblioteca estándar."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from nit_service.dominio import _normalizar, calcular, validar


def procesar(ruta: str, cuerpo: bytes) -> tuple[int, dict[str, object]]:
    """Procese una consulta POST según el contrato documentado.

    Args:
        ruta: Ruta HTTP exacta, sin parámetros de consulta.
        cuerpo: Documento JSON codificado en UTF-8.

    Returns:
        Estado HTTP y objeto de respuesta serializable como JSON.
    """
    if ruta not in ("/calcular", "/validar"):
        return 404, {"error": "Ruta no encontrada"}
    try:
        datos = json.loads(cuerpo.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return 400, {"error": "El cuerpo debe ser JSON válido en UTF-8"}
    if not isinstance(datos, dict) or set(datos) != {"nit"}:
        return 400, {"error": "El cuerpo debe contener únicamente el campo nit"}
    nit = datos["nit"]
    try:
        if ruta == "/calcular":
            digito = calcular(nit)
            return 200, {"nit": _normalizar(nit), "digito": digito}
        return 200, {**validar(nit)}
    except ValueError as error:
        return 400, {"error": str(error)}


class ManejadorHTTP(BaseHTTPRequestHandler):
    """Atienda consultas de cálculo y validación sin registrar datos del cliente."""

    def _responder(self, estado: int, datos: dict[str, object]) -> None:
        contenido = json.dumps(datos, ensure_ascii=False).encode("utf-8")
        self.send_response(estado)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(contenido)))
        self.end_headers()
        self.wfile.write(contenido)

    def do_POST(self) -> None:  # noqa: N802
        """Procese un cuerpo JSON con longitud explícita."""
        try:
            longitud = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            longitud = -1
        if longitud < 0:
            self._responder(400, {"error": "Se requiere Content-Length válido"})
            return
        if self.headers.get("Transfer-Encoding") is not None:
            self._responder(400, {"error": "Transfer-Encoding no está soportado"})
            return
        cuerpo = self.rfile.read(longitud)
        estado, datos = procesar(self.path, cuerpo)
        self._responder(estado, datos)

    def do_GET(self) -> None:  # noqa: N802
        """Rechace consultas GET: las operaciones requieren POST."""
        self._responder(405, {"error": "Use POST"})

    def log_message(self, formato: str, *argumentos: object) -> None:
        """Evite registrar NIT o datos de las solicitudes."""


def crear_servidor(host: str = "127.0.0.1", puerto: int = 8000) -> ThreadingHTTPServer:
    """Cree un servidor sin iniciarlo.

    Args:
        host: Interfaz de escucha; por defecto, solo la máquina local.
        puerto: Puerto TCP. Cero permite elegir un puerto disponible.

    Returns:
        Servidor listo para ejecutar mediante serve_forever().

    Raises:
        OSError: Si no se puede abrir la dirección solicitada.
    """
    return ThreadingHTTPServer((host, puerto), ManejadorHTTP)
