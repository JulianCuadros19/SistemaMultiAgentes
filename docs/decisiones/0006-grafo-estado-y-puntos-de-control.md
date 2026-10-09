---
estado: aceptada
fecha: 2026-10-08
decisores: [Julián Andrés Cuadros Muñoz, Laura Catalina Riveros Flórez]
---

# ADR-0006 · Grafo de 17 nodos: estado tipado, servicios inyectables y puntos de control

## Contexto y planteamiento del problema

El paso 5 exige que una sesión recorra los 17 nodos, cierre los ciclos conversacional y de
corrección, ejercite los retornos de los tres puntos de control humano (ADR-0004) y se reanude
tras interrumpirla. Es el esqueleto sobre el que se conectarán los agentes reales en los pasos
6 a 10. Hay que definir cómo se representa el estado, cómo se separa la orquestación del trabajo
de cada agente, cómo se implementan las pausas humanas y cómo se persiste. La decisión afecta a
`src/multiagente/orquestador/` y `src/multiagente/persistencia/`.

## Factores de decisión

- RF-26 a RF-28 y RF-38: grafo con ciclos y transiciones condicionales, límite de iteraciones,
  reanudación sin pérdida y aprobación humana final.
- RNF-02: reanudar cualquier ejecución interrumpida desde el último punto de control.
- RNF-05: cambiar el prompt, el modelo o la base de conocimiento de un agente sin alterar el
  resto del código.
- Decisión 4 de `CLAUDE.md`: los agentes se comunican solo a través del estado tipado.
- Comportamiento verificado de LangGraph 1.2.12, langgraph-checkpoint 4.2.0 y
  langgraph-checkpoint-postgres 3.1.2.

## Opciones consideradas

- A. Estado con particiones Pydantic inmutables, nodos reales que delegan el trabajo en
  servicios por agente, pausas con `interrupt` y persistencia con `PostgresSaver`.
- B. Estado como diccionarios sin tipar y nodos que implementan directamente el trabajo de cada
  agente.

## Resultado de la decisión

Opción elegida: «A», porque hace explícito qué escribe cada nodo, permite verificar el flujo
completo antes de tener agentes reales y deja a cada agente reemplazable por separado.

1. **Estado tipado.** `EstadoGrafo` reúne las ocho particiones de la arquitectura (Tabla 4) y la
   entrada `cliente`. Cada partición es un modelo Pydantic inmutable: los nodos devuelven
   particiones nuevas con `model_copy`. N1 inicializa todas las particiones y copia en `control`
   los límites configurados, para que una sesión reanudada conserve los límites con que empezó.
2. **Serialización con lista blanca.** LangGraph bloqueará la deserialización de tipos no
   registrados. Con una lista blanca explícita ya los bloquea hoy, incluidas las enumeraciones
   anidadas. `tipos_permitidos()` registra las particiones y todas las enumeraciones de los
   módulos del estado. Una prueba recorre las ocho particiones y falla si LangGraph reporta un
   tipo bloqueado.
3. **Orquestación real, trabajo inyectado.** Aristas, enrutadores y nodos determinísticos son la
   implementación definitiva: N1, N4, N15, N16 y los puntos de control N6, N9 y N17. El trabajo de
   modelos de lenguaje, recuperación y ejecución llega por un `Protocol` por agente
   (`ServiciosElicitador`, `ServiciosArquitecto`, `ServiciosDesarrollador`, `ServiciosTester`).
   El desarrollador no recibe contexto recuperado (decisión 1). `ServiciosSimulados` produce
   artefactos válidos según los esquemas del paso 4.
4. **Pausas humanas.** El diálogo (N3) y los tres puntos de control usan `interrupt`. En N3 la
   espera va al inicio del nodo, porque LangGraph repite el nodo al reanudar: así la llamada al
   modelo se ejecuta una vez por respuesta. Tras un rechazo en N6, las observaciones del revisor
   viajan en la siguiente pausa de diálogo. Las respuestas humanas se validan con
   `RespuestaHumana`: un rechazo exige observaciones. Cada decisión queda en
   `sesion.aprobaciones` con su punto y su fecha.
5. **Enrutamiento.**
   - N4: si no quedan atributos pendientes (rol, funcionalidad, beneficio y reglas de negocio,
     RF-02) o se alcanzó `MAX_TURNOS_ELICITACION` (15 por defecto), va a N5.
   - N6: con defectos de calidad (RF-07), va a N5 sin intervención humana.
   - N9: con errores de validación, va a N8 sin intervención humana.
   - N15: si todos los casos del plan de N16 cumplen, va a N17; al alcanzar el límite de
     iteraciones, termina con fase «requiere intervención humana» (RF-27).
   - Un rechazo en N17 devuelve a N10 y el contador de iteraciones continúa, por decisión del
     equipo, para acotar el costo por módulo (RNF-10).
6. **Paralelismo.** Al aprobarse los requerimientos, N6 enruta a N7 y N16 en el mismo paso. N16
   escribe solo `validacion` y N7 solo `contexto`, de modo que no hay escrituras concurrentes
   sobre la misma partición. N16 no tiene arista de salida.
7. **Persistencia.** `abrir_checkpointer()` abre una conexión psycopg con `autocommit`, sin
   sentencias preparadas y con filas como diccionarios, crea `PostgresSaver` con el serializador
   propio y ejecuta `setup()`. Así se crean `checkpoints`, `checkpoint_writes`,
   `checkpoint_blobs` y `checkpoint_migrations` en la base única (decisión 9). El `thread_id` es
   el identificador de la sesión.
8. **Durabilidad síncrona.** Las sesiones se ejecutan con `durability="sync"`: cada paso se guarda
   antes de iniciar el siguiente. El modo por defecto de LangGraph, `"async"`, guarda mientras
   avanza y podría perder el último paso ante una caída.

Pendiente para pasos posteriores: las pruebas propias de la persona en N17 dentro del entorno
aislado requieren el sandbox (paso 10) y la interfaz (paso 12); hoy N17 recibe la decisión y las
observaciones.

### Consecuencias

- Favorable, porque el flujo completo, sus ciclos y sus retornos están verificados antes de
  conectar cualquier modelo, sin costo.
- Favorable, porque los pasos 6 a 10 implementan un `Protocol` en `agentes/<agente>/` y lo
  inyectan, sin tocar el grafo.
- Favorable, porque una sesión sobrevive al cierre del proceso: se reanuda en la pausa pendiente
  o, tras una caída, en el paso que falló, sin repetir los anteriores.
- Desfavorable, porque las particiones inmutables obligan a reconstruir objetos en cada
  actualización, lo que hace más extenso el código de los nodos.
- Desfavorable, porque todo tipo nuevo que entre al estado debe pertenecer a los módulos
  registrados o agregarse a la lista blanca; de lo contrario, no se reconstruirá al reanudar.

### Confirmación

- `pytest tests/unitarias/test_grafo.py` recorre la sesión completa en memoria y verifica:
  - los 17 nodos visitados y ambos ciclos cerrados;
  - los tres retornos y las seis decisiones registradas;
  - el escalamiento por límite de iteraciones;
  - los retornos automáticos por defectos de calidad y por errores de validación;
  - el límite de turnos;
  - la reanudación tras una caída en N11.
- `pytest -m integracion tests/integracion/test_grafo_postgres.py` reanuda con PostgreSQL en un
  proceso nuevo, tanto a mitad de la elicitación como tras una caída.
- `python scripts/simular_sesion.py` imprime el recorrido completo contra PostgreSQL.

## Análisis de las opciones

### Opción A · Estado tipado y servicios inyectables
- Favorable, porque el estado documenta el contrato entre agentes y Pydantic lo valida.
- Desfavorable, porque exige mantener la lista blanca del serializador.

### Opción B · Diccionarios y nodos monolíticos
- Favorable, porque requiere menos código inicial.
- Desfavorable, porque los errores de forma del estado aparecerían tarde y reemplazar un agente
  obligaría a tocar el grafo.
