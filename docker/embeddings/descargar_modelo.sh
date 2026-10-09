#!/bin/sh
# Descarga los pesos ONNX de BGE-M3 al volumen de modelos, en una revisión fijada.
#
# El descargador interno de TEI corta las descargas largas (~60 s) y falla con el archivo de
# 2,27 GB. Este script usa curl con reanudación y verifica cada archivo con su SHA-256. Si los
# archivos ya están completos, termina en segundos. Ver docs/decisiones/0007.
set -eu

MODELO="${MODELO:-BAAI/bge-m3}"
REVISION="${REVISION:-5617a9f61b028005a4858fdac845db406aefb181}"
DESTINO="${DESTINO:-/data/bge-m3}"
SUMAS="${SUMAS:-/config/bge-m3.sha256}"

esperada() {
    awk -v archivo="$1" '!/^#/ && $2 == archivo { print $1 }' "$SUMAS"
}

verificado() {
    [ -f "$DESTINO/$1" ] && [ "$(sha256sum "$DESTINO/$1" | cut -d' ' -f1)" = "$(esperada "$1")" ]
}

for archivo in $(awk '!/^#/ && NF == 2 { print $2 }' "$SUMAS"); do
    if verificado "$archivo"; then
        echo "ya verificado: $archivo"
        continue
    fi
    mkdir -p "$(dirname "$DESTINO/$archivo")"
    url="https://huggingface.co/$MODELO/resolve/$REVISION/$archivo"
    intento=1
    until verificado "$archivo"; do
        if [ "$intento" -gt 20 ]; then
            echo "ERROR: no se pudo descargar $archivo tras 20 intentos" >&2
            exit 1
        fi
        echo "descargando $archivo (intento $intento)"
        # Reanuda desde lo ya descargado; si el archivo quedó corrupto, se descarta.
        if ! curl --fail --location --silent --show-error --continue-at - \
            --output "$DESTINO/$archivo" "$url"; then
            sleep 5
        elif ! verificado "$archivo"; then
            echo "suma SHA-256 incorrecta en $archivo; se descarga de nuevo" >&2
            rm -f "$DESTINO/$archivo"
        fi
        intento=$((intento + 1))
    done
    echo "verificado: $archivo"
done
echo "Modelo $MODELO@$REVISION listo en $DESTINO"
