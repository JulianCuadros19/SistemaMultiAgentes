"""Arranque del servicio HTTP usando el servidor WSGI de la biblioteca estándar."""

import argparse
from wsgiref.simple_server import make_server

from nit_service.http import application


def main() -> None:
    """Lea la dirección de escucha y ejecute el servicio hasta su interrupción."""
    parser = argparse.ArgumentParser(description="Servicio HTTP de dígitos de verificación NIT")
    parser.add_argument("--host", default="127.0.0.1", help="Dirección de escucha")
    parser.add_argument("--port", type=int, default=8000, help="Puerto HTTP")
    argumentos = parser.parse_args()
    with make_server(argumentos.host, argumentos.port, application) as servidor:
        try:
            servidor.serve_forever()
        except KeyboardInterrupt:
            return


if __name__ == "__main__":
    main()
