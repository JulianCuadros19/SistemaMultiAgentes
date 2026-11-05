# Sistema multiagente de IA para Realtix

Sistema de cuatro agentes especializados que automatiza la cadena de producción de software,
desde la conversación con el cliente hasta el código Python validado.

Trabajo de grado · Programa de Ingeniería de Sistemas y Computación · Universidad Católica de
Colombia · Semillero MAilab.

## Agentes

| Agente | Responsabilidad |
|---|---|
| Elicitador | Conversa con el cliente y produce historias de usuario y requerimientos formales |
| Arquitecto | Selecciona y parametriza la arquitectura del módulo |
| Desarrollador | Genera el código Python con su documentación y sus pruebas |
| Tester | Valida el código contra requerimientos, diseño y criterios de calidad |

Los modelos de lenguaje son los desplegados en Azure OpenAI. El modelo de embeddings, BGE-M3,
corre dentro de la composición, de modo que las bases de conocimiento no salen de la máquina.

## Estructura

```
src/multiagente/     código del sistema
prompts/             prompts de sistema versionados, uno por agente
knowledge_base/      corpus de las cuatro colecciones de conocimiento
config/              configuración de estilo del código generado y tarifas de los modelos
docker/              imágenes de la aplicación y del entorno aislado, y descarga de BGE-M3
db/                  inicialización y migraciones de la base de datos
scripts/             ingesta, operación guionizada y evaluación
tests/               pruebas del sistema
evaluacion/          casos de referencia y resultados del objetivo 4
docs/                requerimientos, arquitectura, plan y decisiones
```

## Puesta en marcha

### Requisitos

- **Docker con Compose** (`docker compose`). En Windows, Docker Desktop con la integración WSL2,
  y los comandos se ejecutan desde Ubuntu.
- **Recursos:** unos 4 GB de memoria libres y 5 GB de disco. El modelo de embeddings ocupa
  2,29 GB.
- **Un recurso de Azure OpenAI con cinco despliegues,** uno por nodo con modelo. Cada variable de
  `.env` lleva el nombre del despliegue:

  | Variable | Nodo | Modelo y versión |
  |---|---|---|
  | `MODELO_N3_DIALOGO` | N3 · diálogo de elicitación | `gpt-5.4-mini` 2026-03-17 |
  | `MODELO_N5_SINTESIS` | N5 · síntesis de los requerimientos | `gpt-5.4-mini` 2026-03-17 |
  | `MODELO_N8_ARQUITECTURA` | N8 · selección y parametrización | `gpt-5` 2025-08-07 |
  | `MODELO_N10_GENERACION` | N10 · generación del módulo | `gpt-6.1-sol` 2026-09-29 |
  | `MODELO_N14_VEREDICTO` | N14 · veredicto del tester | `gpt-6-luna` 2026-09-22 |

  - **Tipo de despliegue:** en el desarrollo se usó Global Standard. Con datos reales de Realtix
    conviene un despliegue de zona de datos de EE. UU., porque un despliegue global puede procesar
    los datos en cualquier región.
  - **Tarifas:** están en `config/tarifas_modelos.toml` y rigen el costo y el presupuesto. Un
    modelo sin tarifa registrada hace fallar la llamada. Con zona de datos, cada tarifa sube un
    10 %.
  - **Lo que no se habilita:** la búsqueda web de Foundry.

### Primer arranque

```bash
cp .env.example .env
```

En `.env` se completan el endpoint y la clave de Azure OpenAI, los cinco despliegues y el usuario y
la clave de PostgreSQL. Después:

```bash
docker compose up -d --build --wait
```

La primera vez, el comando:
1. descarga y verifica el modelo de embeddings;
2. construye las imágenes de la aplicación y del entorno aislado;
3. migra la base de datos e indexa las bases de conocimiento.

La web queda en `http://127.0.0.1:8000/` y solo responde en esa máquina. Las imágenes se
construyen localmente y no se publican en ningún registro, porque llevan el corpus.

La construcción descarga las dependencias de PyPI. Con una red lenta puede tardar más de media hora
o fallar; en ese caso basta repetir el comando, que retoma desde la última capa construida.

### Operar el sistema

En la web, el equipo opera desde el panel y el cliente conversa en su propia vista
(`/conversacion/ID`):
- **Panel:** agrupa las sesiones según quién debe actuar: las que esperan al equipo, las que
  avanzan o esperan al cliente y las terminadas.
- **Página de cada sesión:** la línea del flujo muestra sus cinco etapas y los tres puntos de
  control, N6, N9 y N17. Se abre la etapa que espera, y cada etapa conserva lo ya aprobado.
- **Vista del cliente:** muestra su avance en cuatro pasos de su lenguaje.

La consola corre en otro contenedor de la misma imagen:

```
docker compose run --rm aplicacion multiagente nueva       # sesión nueva por consola
docker compose run --rm aplicacion multiagente sesiones    # sesiones guardadas
docker compose run --rm aplicacion multiagente continuar ID   # retoma una sesión en pausa
docker compose run --rm aplicacion multiagente cerrar ID   # cierra una sesión con su motivo
docker compose run --rm aplicacion multiagente ver ID      # trazabilidad de la sesión
docker compose run --rm aplicacion multiagente traza ID    # traza por nodo: prompts, costo
docker compose run --rm aplicacion multiagente exportar ID data/local/exportaciones/ID
```

- **Comprobación previa:** cada `run` comprueba antes el modelo, el corpus y el entorno aislado,
  en unos 10 s. Con el sistema ya arriba, `--no-deps` la omite.
- **Archivos:** la aplicación lee y escribe en `data/local/`, la carpeta compartida con la máquina:
  - la consola deja allí el código de cada versión;
  - allí van la exportación de un módulo y las pruebas propias de N17 que se indiquen por ruta;
  - la web recibe esas pruebas como archivo adjunto y exporta el módulo como `.zip`.

En la aprobación final (N17), el módulo se aprueba o se devuelve con observaciones a uno de tres
destinos:
- el desarrollador;
- el arquitecto;
- el elicitador, como una enmienda de los requerimientos.

Si el tester no lo aprueba tras el límite de iteraciones, la sesión escala a N17 sin poder
aprobarse. Cada sesión tiene un presupuesto de 1,50 USD (`PRESUPUESTO_MAXIMO_POR_MODULO_USD`). Al
alcanzarlo se detiene hasta que una persona lo amplía o la cierra. Cualquier sesión en pausa o
detenida se puede cerrar.

El paquete exportado trae:
- el código con su `USO.md`;
- un `requirements.txt` con las versiones con que se probó;
- en `LEEME.md`, los pasos para ponerlo en marcha.

### Mantenimiento

```
docker compose up -d --build --wait   # tras actualizar el repositorio: reconstruye y reindexa
docker compose stop                   # detiene el sistema; los datos se conservan
docker compose down -v                # borra contenedores, sesiones, base y modelo descargado
```

### Seguridad

- **Docker del anfitrión:** el contenedor de la aplicación lo usa por su socket, para crear el
  entorno aislado.
- **Código generado:** solo corre en ese entorno, un contenedor efímero sin red, de solo lectura y
  sin root.
- **Web:** no tiene autenticación, por eso solo se publica en `127.0.0.1`.
- **Más detalle:** `docs/decisiones/0017-entrega-en-contenedores-con-azure-openai.md`.

### Despliegue de demostración en Azure

Para un enlace público, solo con datos sintéticos, hay una máquina virtual con un proxy que agrega TLS
y contraseña (ADR-0020). La composición base no cambia. Requiere una máquina Ubuntu con 16 GB de memoria,
los puertos 80 y 443 abiertos, una etiqueta DNS y la llave SSH en `~/.ssh/multiagente_azure`:

```bash
scripts/desplegar_azure.sh multiagente-demo.centralus.cloudapp.azure.com
```

El comando publica la versión de `HEAD`. La primera vez instala Docker y genera la contraseña, que
imprime una sola vez. Las instrucciones de uso están en `docs/manual-de-uso.md`.

## Desarrollo

Desde Ubuntu, con Python 3.11 o superior:

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
```

```bash
docker compose up -d --wait db embeddings
```

Con eso, `multiagente …` corre desde el `.venv`. La web del contenedor usa el mismo puerto: se
detiene con `docker compose stop aplicacion`.

Pruebas sin costo:

```
pytest
pytest -m "integracion and not nube"
pytest -m "embeddings and not nube"
pytest -m "sandbox and not nube"
```

- **Pruebas con costo:** las marcadas `nube` llaman a Azure OpenAI.
- **Revisar la web sin costo:** `python scripts/web_demostracion.py` la levanta en
  `http://127.0.0.1:8010/` con agentes simulados y nueve sesiones sintéticas, una por estado. No
  llama a Azure ni usa PostgreSQL.
- **Al cambiar una dependencia:** `python scripts/congelar_aplicacion.py` actualiza las versiones
  de la imagen.

## Documentación

- [Requerimientos](docs/requerimientos.md)
- [Arquitectura](docs/arquitectura.md)
- [Plan de trabajo](docs/plan_de_trabajo.md)
- [Registros de decisión](docs/decisiones/)
- [Manual de uso](docs/manual-de-uso.md)
- [Informe de evaluación](docs/evaluacion/informe-objetivo-4.md)

## Estado

Pasos 0 a 15 del plan cerrados. El historial está en la sección «Estado actual» de `CLAUDE.md`.
