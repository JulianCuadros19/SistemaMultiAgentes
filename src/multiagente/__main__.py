"""Permite `python -m multiagente`, equivalente al comando `multiagente`."""

from multiagente.interfaces.consola import main

if __name__ == "__main__":
    raise SystemExit(main())
