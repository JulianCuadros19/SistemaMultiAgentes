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

## Estructura

```
src/multiagente/     código del sistema
prompts/             prompts de sistema versionados, uno por agente
knowledge_base/      corpus de las cuatro colecciones de conocimiento
config/              configuración de estilo aplicada al código generado
docker/              imagen del entorno aislado de ejecución
db/                  migraciones de la base de datos
tests/               pruebas del sistema
evaluacion/          casos de referencia y resultados del objetivo 4
docs/                requerimientos, arquitectura, plan y decisiones
```

## Operar el sistema

Desde Ubuntu, con el entorno virtual activo (`source .venv/bin/activate`), los servicios arriba
(`docker compose up -d --wait`), la imagen del entorno aislado
(`docker compose --profile sandbox build sandbox`), el corpus ingerido
(`python scripts/ingestar_conocimiento.py`) y el archivo `.env`:

```
multiagente web                  # interfaz web en http://127.0.0.1:8000/
multiagente nueva                # sesión nueva por consola
multiagente sesiones             # sesiones guardadas
multiagente continuar ID         # retoma una sesión en pausa o detenida
multiagente ver ID               # trazabilidad de la sesión
multiagente exportar ID CARPETA  # entregables del módulo validado
```

En la web, el equipo opera desde el panel y el cliente conversa en su propia vista
(`/conversacion/ID`). La web solo responde en la máquina local.

## Documentación

- [Requerimientos](docs/requerimientos.md)
- [Arquitectura](docs/arquitectura.md)
- [Plan de trabajo](docs/plan_de_trabajo.md)

## Estado

En desarrollo. Ver la sección «Estado actual» de `CLAUDE.md`.
