#!/usr/bin/env bash
# Publica la versión de HEAD en la máquina de Azure y levanta el sistema (ADR-0020).
#
# Copia el código con `git archive`, sin credenciales de GitHub en la máquina, y .env por scp.
# Instala Docker si falta. La primera vez crea .env.azure con una contraseña generada, que imprime
# una sola vez. Se puede repetir: reconstruye con el código nuevo y conserva la base y la contraseña.
#
# Uso:
#   scripts/desplegar_azure.sh multiagente-demo.southcentralus.cloudapp.azure.com
#
# Variables opcionales: LLAVE (llave SSH), USUARIO_SSH y USUARIO_WEB.

set -euo pipefail

SITIO="${1:?Indique la dirección de la máquina, como multiagente-demo.southcentralus.cloudapp.azure.com}"
LLAVE="${LLAVE:-$HOME/.ssh/multiagente_azure}"
USUARIO_SSH="${USUARIO_SSH:-azureuser}"
USUARIO_WEB="${USUARIO_WEB:-demo}"
DESTINO="multiagente"
COMPOSICION="-f docker-compose.yml -f docker-compose.azure.yml"

cd "$(git rev-parse --show-toplevel)"
if [[ ! -f .env ]]; then
  echo "Falta .env en la raíz del proyecto." >&2
  exit 1
fi

OPCIONES=(-i "$LLAVE" -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30)
remoto() { ssh "${OPCIONES[@]}" "$USUARIO_SSH@$SITIO" "$@"; }

echo "== Docker en la máquina"
remoto 'command -v docker >/dev/null || { curl -fsSL https://get.docker.com | sudo sh; }; sudo usermod -aG docker "$USER"; sudo docker --version; sudo docker compose version'

echo "== Código de HEAD ($(git rev-parse --short HEAD))"
remoto "mkdir -p $DESTINO"
git archive HEAD | remoto "tar -x -C $DESTINO"

echo "== Secretos"
scp -q "${OPCIONES[@]}" .env "$USUARIO_SSH@$SITIO:$DESTINO/.env"
remoto "chmod 600 $DESTINO/.env"
if ! remoto "test -f $DESTINO/.env.azure"; then
  IMAGEN=$(sed -n 's/^ *image: \(caddy:.*\)$/\1/p' docker-compose.azure.yml)
  CLAVE=$(openssl rand -base64 24 | tr -d '/+=' | cut -c1-20)
  HASH=$(remoto "sudo docker run --rm $IMAGEN caddy hash-password --plaintext '$CLAVE'")
  remoto "umask 077; cat > $DESTINO/.env.azure" <<EOF
SITIO_WEB=$SITIO
WEB_USUARIO=$USUARIO_WEB
WEB_CLAVE_HASH='$HASH'
EOF
  echo "Usuario de la web: $USUARIO_WEB"
  echo "Contraseña de la web (no se vuelve a mostrar): $CLAVE"
fi

echo "== Composición"
remoto "cd $DESTINO && sudo docker compose $COMPOSICION up -d --build --wait"
remoto "cd $DESTINO && sudo docker compose $COMPOSICION ps --format 'table {{.Service}}\t{{.State}}\t{{.Status}}'"

echo "Listo: https://$SITIO/"
