---
estado: aceptada
fecha: 2026-10-09
decisores: [Julián Andrés Cuadros Muñoz, Laura Catalina Riveros Flórez]
modifica: ADR-0006 (puntos 1, 4 y 5)
---

# ADR-0008 · Agente elicitador: fidelidad al cliente, verificación de calidad y escalamiento

> El ADR-0009 cambia el modelo de N3 y N5 a `gpt-5.4-mini`. Las mediciones de este ADR son con
> `gpt-5-nano`.
> El ADR-0013 (paso 11) hace que la fidelidad equipare los números en letras con sus cifras:
> «cuatro dígitos» respalda «4 dígitos».

## Contexto y planteamiento del problema

El paso 7 exige que una conversación produzca un requerimiento que pase la verificación de
calidad. Hay que reemplazar la simulación del elicitador (N2, N3, N5 y la verificación de N6)
por el agente real, con Azure OpenAI (`gpt-5-nano`) en N3 y N5 y BGE-M3 en N2.

Al revisar el esqueleto aparecieron cuatro huecos:
- N2 corría antes de que el cliente hablara, así que no podía recuperar el dominio de su
  necesidad (RF-04).
- El retorno N6→N5 por defectos de calidad no tenía límite.
- La suficiencia de N4 era más estrecha que la guía eli-006 y que el RNF-08.
- Faltaba una forma reproducible de verificar la condición de terminado.

Las mediciones con el modelo real mostraron además un problema que el diseño debía resolver: el
modelo, con el contexto de dominio a la vista, copiaba en el registro reglas típicas del dominio
que el cliente nunca dijo.

La decisión afecta a:
- `src/multiagente/agentes/elicitador/`, `src/multiagente/llm/` y `src/multiagente/orquestador/`;
- `src/multiagente/interfaces/cliente_simulado.py`;
- `prompts/elicitador/` y `evaluacion/`.

## Factores de decisión

- RF-01 a RF-08: conversación, preguntas estratégicas, registro, contexto recuperado, historias,
  formato del Anexo A, verificación de calidad y aprobación humana.
- RNF-01 (menos de 15 s por turno), RNF-08 (una pregunta por turno, lenguaje de negocio,
  confirmación antes de cerrar) y RNF-10 (costo acotado).
- eli-006, regla 4: no inventar; lo que el cliente no dijo no se completa con supuestos.
- Decisión 11 de `CLAUDE.md`: los prompts viven versionados en `prompts/`.
- Solo cinco nodos invocan un modelo.

## Opciones consideradas

- A. N3 en una sola llamada que extrae y pregunta, con el contexto de dominio a la vista.
- B. N3 en dos llamadas dentro del mismo nodo: extracción sin contexto de dominio y pregunta con
  el contexto recuperado, más verificaciones deterministas de fidelidad.
- C. Subir el esfuerzo de razonamiento de N3 a `medium`.

## Resultado de la decisión

Opción elegida: «B». La A copiaba reglas del dominio al registro en tres de cinco corridas. La C
superó el RNF-01: 12 a 23 s por llamada, y una agotó 4.000 tokens solo en razonamiento.

### Decisiones del equipo (antes de implementar)

1. **La necesidad entra en la apertura.**
   - `EntradaSesion` lleva `cliente`, `proyecto` y `necesidad`, y N1 registra la necesidad como
     primer turno del cliente.
   - N3 espera solo si hay `pregunta_pendiente`. Al abrir la sesión y tras un rechazo formula
     sin esperar.
   - `Conversacion.turnos_procesados` distingue una respuesta nueva de una ya procesada.
   - La topología no cambia.
2. **Suficiencia según eli-006 y RNF-08.** N4 cierra cuando hay rol, funcionalidad, beneficio,
   reglas, datos de entrada y de salida, al menos una excepción y la confirmación del resumen.
   La confirmación solo vale con el registro completo.
3. **Límite de correcciones con escalamiento.**
   - N6 devuelve a N5 los defectos hasta `MAX_CORRECCIONES_CALIDAD` (2 por defecto).
   - Al agotarlo, pausa igual y muestra los defectos al analista, que aprueba o rechaza.
   - Los defectos aceptados quedan en `Requerimientos.defectos_escalados`.
4. **Verificación reproducible.** Prueba `nube` con un cliente simulado por modelo sobre un caso
   sintético y un script de consola para una persona.

### Decisiones de implementación

5. **Salida estructurada estricta.**
   - Chat Completions con `response_format` `json_schema` estricto, generado con el ayudante
     público `pydantic_function_tool`.
   - Los modelos de salida usan tipos planos; después se validan con los esquemas del Anexo A.
   - Una salida que incumple el esquema o una regla del nodo se reintenta una vez, con los
     problemas a la vista del modelo (`problemas_intento_anterior`). Si vuelve a fallar, el
     error se propaga y la sesión se reanuda desde su último punto de control.
   - Los fallos son errores tipados que conservan la respuesta medida, porque se cobra igual.
6. **N3 en dos llamadas.**
   - La extracción (`prompts/elicitador/extraccion.md`) ve el registro, la pregunta anterior y
     la respuesta, sin contexto de dominio. Devuelve solo lo que la respuesta aporta o corrige.
   - La pregunta (`prompts/elicitador/dialogo.md`) ve el contexto de N2, el registro y las
     observaciones del revisor.
   - Cuando el cliente acaba de completar todo, no se pide pregunta: el sistema muestra el
     resumen.
7. **Fidelidad determinística** (`agentes/elicitador/fidelidad.py`).
   - Un texto entra al registro, o a la precondición, la regla y los datos de N5, solo si al
     menos el 60 % de sus raíces (cinco primeras letras, sin tildes) aparecen en lo que dijo el
     cliente.
   - Solo hay preguntas abiertas si el cliente dijo no saber algo.
   - Es una heurística: puede descartar una paráfrasis legítima. En ese caso el resumen no la
     muestra y el cliente la echa en falta.
8. **Confirmación exacta.**
   - El resumen que confirma el cliente lo arma el código con el registro, así que confirma
     exactamente lo que se va a sintetizar.
   - En la respuesta que confirma, los cambios solo cuentan si los respalda esa misma respuesta,
     y las listas solo suman. Así una paráfrasis del modelo no reabre la confirmación, pero «Sí,
     y además…» sí la reabre.
   - El rechazo en N6 reinicia la confirmación y vuelve a N3 con la observación.
9. **Verificación de calidad del RF-07 sin modelo** (`agentes/elicitador/calidad.py`).
   - Aplica las señales que eli-005 declara detectables y los antipatrones de eli-009:
     - marcadores de pendiente;
     - cuantificadores vagos y comparativos sin referencia;
     - generalizaciones y opcionalidad encubierta;
     - QUIERO en infinitivo y singular, y rol concreto;
     - al menos dos escenarios, uno de error, y escenarios sin detalles de implementación;
     - trazabilidad historia–requerimiento y referencias al contexto.
   - Criterios de interpretación:
     - la palabra suelta «pendiente» no se marca, porque es legítima en el dominio tributario
       («saldo pendiente»);
     - los títulos repetidos se admiten, porque varios RF de una historia la reproducen;
     - en los escenarios se admiten los nombres de los datos declarados.
   - La consistencia semántica, la corrección y la factibilidad quedan para el analista.
10. **Defectos que requieren al cliente.** Las preguntas abiertas y los marcadores de pendiente
    escalan al analista sin intentar la corrección automática: N5 no puede resolverlos sin
    inventar (eli-009). Si N4 cerró por límite de turnos, un campo obligatorio sin respaldo se
    llena con «Por confirmar con el cliente.», que la verificación escala.
11. **Campos deterministas en código.**
    - Identificadores `HU-01` y `RF-nn`, y versión `0.<síntesis>`.
    - Proyecto de la sesión, autor «Agente elicitador» y título igual a la historia.
    - Prioridad heredada de la historia y nombres de datos como identificadores
      (`numero_predial`).
12. **Referencias al contexto (RF-04).** Los fragmentos llegan al modelo con etiquetas
    `F1…Fn`. N5 cita las que usó y el código las traduce a referencias estables
    (`dom-002 v1.0 · …`) en `Requerimientos.referencias`.
13. **Configuración.**
    - `ESFUERZO_N3_DIALOGO=low` y `MAX_TOKENS_N3_DIALOGO=4000`; las dos llamadas de N3 usan los
      mismos valores.
    - `ESFUERZO_N5_SINTESIS=low` y `MAX_TOKENS_N5_SINTESIS=8000`. Con `medium`, N5 tardaba de 32
      a 110 s y agregaba más contenido no dicho.
14. **Traza provisional.**
    - Cada llamada, también la fallida, va a `RegistroLlamada`: nodo, prompt y versión, huella,
      tokens con el razonamiento aparte, costo en `Decimal` y latencia.
    - El script la escribe en `docs/mediciones/paso-07-elicitador.jsonl`, sin el contenido de los
      mensajes. La tabla `ejecuciones` y Langfuse quedan para el paso 13.
15. **Cliente simulado** (`interfaces/cliente_simulado.py`). No es un agente del sistema: ocupa el
    lugar de la persona con un caso de `evaluacion/casos/` y esfuerzo `medium`. Con `minimal` o
    `low` confirmaba resúmenes incompletos.

### Mediciones (2026-10-08 y 2026-10-09)

Caso sintético de mutación de propietario, despliegue Global Standard de `gpt-5-nano` en South
Central US.

| Diseño | Resultado |
|---|---|
| N3 en una llamada, N5 `medium` | Pasó 1 de 5. Copió reglas del dominio al registro, mostró un resumen que no presentó y N5 tardó de 32 a 110 s |
| N3 en dos llamadas, N5 `low` | 6 de 7 corridas `nube` llegaron a N6 sin defectos. Las 5 corridas del script terminaron en N6, incluido el camino con pausa, reanudación, rechazo y aprobación |

Diseño final, por llamada:

| Nodo | Latencia media | Máxima | Razonamiento medio | Entrada en caché |
|---|---|---|---|---|
| N3 (cada una de sus dos llamadas) | 3,7 s | 7,8 s | 314 tokens | 69 % |
| N5 | 10,0 s | 10,8 s | 672 tokens | 87 % |

- **RNF-01.** Los turnos de diálogo, con sus dos llamadas, duran de 3 a 9 s. El turno que cierra
  la elicitación incluye la síntesis y midió entre 11 y 15,3 s. La interfaz (paso 12) debe
  acusar la confirmación antes de sintetizar.
- **Costo.** El sistema gasta entre 0,002 y 0,005 USD por elicitación, de 3 a 7 turnos, sin
  contar el cliente simulado.
- **Gasto total del paso en mediciones.** Unos 0,16 USD.
- **Recuperación.** La necesidad real del cliente recupera su documento de dominio en primer
  lugar, con similitud de 0,53 a 0,68. El umbral de 0,37 no se recalibra.

### Consecuencias

- **Favorable:**
  - una conversación produce requerimientos del Anexo A fieles a lo que dijo el cliente, que
    pasan la verificación de calidad y llegan al analista con sus referencias al contexto;
  - el costo por elicitación es de milésimas de dólar.
- **Favorable:** las verificaciones deterministas valen para cualquier modelo:
  - fidelidad;
  - confirmación exacta;
  - una pregunta por turno;
  - calidad del RF-07.

  Un modelo mayor las cumpliría con menos reintentos.
- **Desfavorable: el modelo es inferior al perfil asignado.** La arquitectura asigna a N3 y N5 el
  perfil «intermedio» (Tabla 3), y `gpt-5-nano` es el económico. La variabilidad observada
  (extracciones incompletas, preguntas compuestas, una síntesis fallida) es coherente con esa
  diferencia. El benchmark del paso 15 debe comparar con `gpt-5-mini`; cambiarlo es editar
  `.env` y las tarifas.
- **Desfavorable: las heurísticas pueden equivocarse.** El respaldo léxico y las señales de error
  pueden descartar o dejar pasar casos límite. Lo acotan la confirmación del cliente y la
  revisión del analista.
- **Desfavorable: una necesidad por conversación.** N5 puede partirla en varios RF, pero el
  backlog multihistoria se difiere.
- **Desfavorable: una falla sin reproducir.** En 1 de 7 corridas `nube`, N5 no logró una
  síntesis con respaldo y la sesión quedó detenida en N5, reanudable. La hipótesis es un
  registro incompleto por límite de turnos, que ahora se declara «Por confirmar». La prueba
  imprime la conversación si vuelve a ocurrir.
- **Hallazgo sobre el Anexo A.** La verificación encuentra en el backlog oficial las historias 3
  y 4 sin infinitivo y las historias 1 y 10 con dos capacidades. El RF-27 solo incumple el
  infinitivo.

### Confirmación

- `pytest`: 224 pruebas unitarias. Incluyen:
  - la calidad con los ejemplos oficiales y una señal inyectada por regla;
  - la fidelidad con los casos reales de las corridas;
  - las dos llamadas de N3;
  - el escalamiento;
  - una conversación completa N1→N6 con modelo falso.
- `pytest -m integracion`: 27. `pytest -m "embeddings and not nube"`: 17. Incluyen N2 con
  BGE-M3: la necesidad recupera dom-002 o dom-003 y la guía eli-006.
- `pytest -m nube tests/integracion/test_elicitador_nube.py`: es la condición de terminado.
  Exige:
  - N6 sin defectos;
  - referencias contenidas en el contexto recuperado;
  - una pregunta por turno;
  - N3 por debajo de 15 s.
- `python scripts/conversar_elicitador.py --simulado evaluacion/casos/elicitacion-mutacion.md`.
  Con `--pausar-tras`, `--sesion`, `--rechazar` y `--aprobar` reproduce el camino humano completo.

## Análisis de las opciones

### Opción A · N3 en una llamada
- Favorable, porque cuesta una llamada por turno.
- Desfavorable, porque mezcla lo que dijo el cliente con lo que sabe del dominio. Se midió en
  cinco corridas.

### Opción B · N3 en dos llamadas con verificaciones deterministas
- Favorable, porque la extracción no ve de dónde copiar y el código garantiza fidelidad y
  confirmación.
- Desfavorable, porque son dos llamadas por turno, aunque la mayor parte de la entrada va en
  caché.

### Opción C · Más razonamiento
- Desfavorable, porque supera el RNF-01 y no elimina la fuente de la copia.
