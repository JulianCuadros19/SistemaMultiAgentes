"""Punto de entrada para ejecutar el servicio HTTP."""

import argparse

from nit_service.http import crear_servidor


def main() -> None:
    """Ejecute el servidor hasta recibir una interrupción de teclado."""
    parser = argparse.ArgumentParser(description="Servicio de dígito de verificación de NIT")
    parser.add_argument("--host", default="127.0.0.1", help="Interfaz de escucha")
    parser.add_argument("--port", type=int, default=8000, help="Puerto TCP")
    argumentos = parser.parse_args()
    with crear_servidor(argumentos.host, argumentos.port) as servidor:
        try:
            servidor.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
