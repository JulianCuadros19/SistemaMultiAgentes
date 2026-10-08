# Plan de trabajo del sistema multiagente

Cada paso tiene una condición de terminado verificable. No se avanza al siguiente sin
cumplirla. Al cerrar un paso, se actualiza la sección «Estado actual» de `CLAUDE.md`.

## Bloque A · Cimientos

| Paso | Qué se hace | Terminado cuando |
|---|---|---|
| 0 | Verificar el entorno | Python 3.11 o superior, Docker y Git responden desde la terminal de Ubuntu |
| 1 | Estructura, repositorio y dependencias | El paquete `multiagente` se importa y el primer commit está en GitHub |
| 2 | Infraestructura en contenedores | PostgreSQL acepta conexiones y la extensión pgvector está activa |
| 3 | Validar Azure OpenAI | Una llamada real responde y su costo queda registrado |
| 4 | Contratos de datos | Los esquemas validan los ejemplos de los Anexos A y B |

## Bloque B · Esqueleto caminante

| Paso | Qué se hace | Terminado cuando |
|---|---|---|
| 5 | Grafo completo con nodos simulados | Una sesión recorre los 17 nodos, cierra ambos ciclos, ejercita los retornos de los tres puntos de control humano y se reanuda tras interrumpirla |

Este es el paso más importante del plan. El riesgo principal de un sistema multiagente está
en el estado, las transiciones y los ciclos, no en los agentes. Si el esqueleto funciona con
respuestas simuladas, cada agente real encaja después sin sorpresas.

## Bloque C · Conocimiento

| Paso | Qué se hace | Terminado cuando |
|---|---|---|
| 6 | Pipeline de las bases de conocimiento | Cada agente recupera únicamente de sus colecciones autorizadas |

## Bloque D · Agentes reales

| Paso | Qué se hace | Terminado cuando |
|---|---|---|
| 7 | Agente elicitador | Una conversación produce un requerimiento que pasa la verificación de calidad |
| 8 | Agente arquitecto | La especificación generada pasa las tres validaciones del Anexo B |
| 9 | Agente desarrollador | El código se importa sin error y cubre las interfaces de la especificación |
| 10 | Agente tester | Detecta defectos inyectados a propósito en código de prueba |
| 11 | Integración de extremo a extremo | Un módulo completo sale aprobado por el tester |

## Bloque E · Producto

| Paso | Qué se hace | Terminado cuando |
|---|---|---|
| 12 | Interfaces de consola y web | Un analista opera el flujo completo sin tocar código |
| 13 | Control de costo y observabilidad | El presupuesto detiene una ejecución que lo supera |
| 14 | Empaquetado y modo local | El sistema corre completo sin credenciales de nube |

## Bloque F · Evaluación del objetivo 4

| Paso | Qué se hace | Terminado cuando |
|---|---|---|
| 15 | Casos de referencia y líneas base | Métricas calculadas contra la implementación manual y contra un modelo único |

## Riesgos que condicionan el orden

- **Cuota de Azure.** El paso 3 va antes que cualquier agente porque la cuota era un riesgo
  bloqueante. Si falla, debe saberse en la primera semana, no en la décima.
- **Alcance de cuatro agentes.** Si el tiempo no alcanza, el catálogo cerrado de
  arquitecturas es el producto mínimo viable del agente arquitecto; el diseño libre se
  difiere a trabajos futuros.
