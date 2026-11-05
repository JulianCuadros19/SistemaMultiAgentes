#!/bin/sh
# Punto de entrada de la imagen de la aplicación (ADR-0017).
#
# Arranca como root solo para elegir con qué usuario corre el comando:
# - el dueño de data/local, la carpeta montada del anfitrión, para que la traza, las carpetas de
#   trabajo y las exportaciones queden a nombre de la persona;
# - con el grupo del socket de Docker, para crear el entorno aislado sin ser root.
# Los identificadores se leen al arrancar, porque cambian de una máquina a otra. Si data/local es de
# root, o si el contenedor ya arrancó sin root, el comando corre tal cual.
set -eu

if [ "$(id -u)" != 0 ]; then
    exec "$@"
fi

datos=/app/data/local
mkdir -p "$datos"
usuario=$(stat -c %u "$datos")
grupo=$(stat -c %g "$datos")
if [ "$usuario" = 0 ]; then
    exec "$@"
fi

grupos=$grupo
if [ -S /var/run/docker.sock ]; then
    grupos="$grupos,$(stat -c %g /var/run/docker.sock)"
fi
exec setpriv --reuid="$usuario" --regid="$grupo" --groups="$grupos" -- "$@"
