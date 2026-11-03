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

COPY requisitos.txt versiones.txt cierres.py /opt/sandbox/

# Las dependencias transitivas se restringen a las versiones de versiones.txt, con que se probaron
# los módulos, así la imagen se reconstruye igual (ADR-0014). La imagen guarda lo que quedó
# instalado y el cierre de dependencias de cada requisito: una prueba con Docker los compara con
# los versionados, y scripts/congelar_entorno_aislado.py los copia cuando cambia requisitos.txt.
RUN pip install --no-cache-dir -r /opt/sandbox/requisitos.txt -c /opt/sandbox/versiones.txt \
    && pip check \
    && pip freeze > /opt/sandbox/instaladas.txt \
    && python /opt/sandbox/cierres.py /opt/sandbox/requisitos.txt > /opt/sandbox/cierres.json \
    && useradd --uid 10001 --user-group --no-create-home --shell /usr/sbin/nologin sandbox

USER 10001:10001
WORKDIR /tmp
