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

## Documentación

- [Requerimientos](docs/requerimientos.md)
- [Arquitectura](docs/arquitectura.md)
- [Plan de trabajo](docs/plan_de_trabajo.md)

## Estado

En desarrollo. Ver la sección «Estado actual» de `CLAUDE.md`.
