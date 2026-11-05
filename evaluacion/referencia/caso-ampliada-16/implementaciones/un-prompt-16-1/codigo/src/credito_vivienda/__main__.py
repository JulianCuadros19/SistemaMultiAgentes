"""Permite ejecutar la herramienta mediante python -m credito_vivienda."""

import sys

from credito_vivienda.cli import main

if __name__ == "__main__":
    sys.exit(main())
