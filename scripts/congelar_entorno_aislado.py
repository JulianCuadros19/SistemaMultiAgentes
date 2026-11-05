"""Copia a docker/sandbox/ las versiones instaladas y los cierres de la imagen del entorno aislado.

La imagen restringe sus dependencias transitivas a `docker/sandbox/versiones.txt` (ADR-0014).
Cuando cambia `docker/sandbox/requisitos.txt`, las dependencias nuevas se resuelven al construir
la imagen; este guion deja versionado lo que quedó instalado y el cierre de cada librería, para
que el paquete exportado de un módulo fije las mismas versiones con que se probó.

Uso, desde la raíz del proyecto:
    docker compose build sandbox
    python scripts/congelar_entorno_aislado.py
"""

import subprocess

from multiagente.core.configuracion import ConfiguracionSandbox
from multiagente.sandbox.requisitos import CARPETA_IMAGEN

ENCABEZADO = (
    "# Versiones exactas de la imagen del entorno aislado, también las transitivas (ADR-0014).\n"
    "# Son las versiones con que el tester probó los módulos; la imagen las usa como\n"
    "# restricciones al construirse. Si cambia requisitos.txt, se regeneran con\n"
    "# scripts/congelar_entorno_aislado.py.\n"
)


def leer_de_la_imagen(imagen: str, ruta: str) -> str:
    """Contenido de un archivo de la imagen, en un contenedor efímero sin red."""
    resultado = subprocess.run(
        ["docker", "run", "--rm", "--network=none", "--entrypoint", "cat", imagen, ruta],
        capture_output=True,
        text=True,
        check=True,
    )
    return resultado.stdout


def main() -> None:
    """Copia el freeze y los cierres de la imagen a la carpeta versionada."""
    imagen = ConfiguracionSandbox().imagen
    instaladas = leer_de_la_imagen(imagen, "/opt/sandbox/instaladas.txt")
    (CARPETA_IMAGEN / "versiones.txt").write_text(ENCABEZADO + instaladas, encoding="utf-8")
    cierres = leer_de_la_imagen(imagen, "/opt/sandbox/cierres.json")
    (CARPETA_IMAGEN / "cierres.json").write_text(cierres, encoding="utf-8")
    print(f"Versionados versiones.txt y cierres.json desde {imagen}.")


if __name__ == "__main__":
    main()
