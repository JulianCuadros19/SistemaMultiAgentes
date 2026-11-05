# Imagen de la aplicación: orquestador, agentes, recuperación e interfaces (ADR-0017).
#
# Se construye en la máquina donde corre y no se publica en ningún registro, porque lleva el corpus
# de las bases de conocimiento, que es confidencial. Los secretos llegan al arrancar como variables
# de entorno desde .env, y .dockerignore impide copiarlos a la imagen.
#
# Python 3.14.4 es la versión con que corren las pruebas del sistema. Etiquetas y digests fijados el
# 2026-11-04.
FROM docker:29.8.0-cli@sha256:eccaacfeed644c7de222ff047483568cb988dde95476fbaaf10ea2d04921bb66 AS cli-docker

FROM python:3.14.4-slim-trixie@sha256:2ca02f32b4d9d893863367ce07ec1972819f476dd38d8612f2a9cb6a41cbb727

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/tmp

# La CLI de Docker, de la versión del anfitrión: con ella la aplicación crea el entorno aislado por
# el socket del anfitrión, en N11 y en las pruebas propias de N17.
COPY --from=cli-docker /usr/local/bin/docker /usr/local/bin/docker

# Las dependencias van en su propia capa, con las versiones exactas con que pasan las pruebas como
# restricciones (versiones.txt), para que un cambio del código no las reinstale.
COPY pyproject.toml docker/aplicacion/versiones.txt /tmp/dependencias/
WORKDIR /tmp/dependencias
RUN python -c "import tomllib; print(*tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies'], sep='\n')" \
        > requisitos.txt \
    && pip install -r requisitos.txt -c versiones.txt

WORKDIR /app

# El repositorio completo. Las rutas a los prompts, la configuración, el corpus, las migraciones, la
# imagen del entorno aislado y los casos de evaluación se calculan desde la raíz, por eso la
# instalación es editable.
COPY . .
RUN pip install --no-deps -e . && pip check

# El punto de entrada elige el usuario con que corre el comando (ver entrada.sh).
ENTRYPOINT ["sh", "/app/docker/aplicacion/entrada.sh"]
CMD ["multiagente", "web"]
