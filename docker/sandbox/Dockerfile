# Imagen del entorno aislado donde se ejecuta el código generado (RF-20, RNF-03).
# La aplicación crea un contenedor efímero por ejecución, sin red, de solo lectura y sin root, y
# le entrega el código por la entrada estándar: no se monta ninguna carpeta del anfitrión.
# Ver docs/decisiones/0011-agente-desarrollador.md.
#
# Python 3.11 es la versión mínima del catálogo tecnológico (arq-004): el código generado debe
# funcionar en ella. Etiqueta y digest fijados el 2026-10-09.
FROM python:3.11.17-slim-trixie@sha256:0dd364ba7e10242f07755449e3a3d0e35f9efd987952737b90def6709ab0c5ce

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requisitos.txt /opt/sandbox/requisitos.txt

# Las versiones resueltas, también las transitivas, quedan en la imagen para la traza.
RUN pip install --no-cache-dir -r /opt/sandbox/requisitos.txt \
    && pip freeze > /opt/sandbox/versiones.txt \
    && useradd --uid 10001 --user-group --no-create-home --shell /usr/sbin/nologin sandbox

USER 10001:10001
WORKDIR /tmp
