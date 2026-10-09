---
estado: aceptada
fecha: 2026-10-09
decisores: [Julián Andrés Cuadros Muñoz, Laura Catalina Riveros Flórez]
modifica: ADR-0008 (fidelidad de N3 con números en letras)
---

# ADR-0013 · Integración de extremo a extremo: persona real, cliente simulado y costo por módulo

## Contexto y planteamiento del problema

El paso 11 exige que un módulo completo salga aprobado por el tester. Hasta ahora, los pasos 7 a
10 habían probado cada agente por separado, con los vecinos fijos o simulados:
- ninguna sesión había recorrido el flujo con los cuatro agentes reales;
- el ciclo de corrección N10–N15 nunca había corrido entre el desarrollador real y el tester real.

Además, el paso tenía tres pendientes:
- medir cuántas iteraciones gasta el umbral 0 de hallazgos Media con módulos reales (ADR-0012);
- estimar el costo por módulo, la unidad de trabajo del modelo de costos;
- verificar el RNF-01: 15 s por turno de diálogo y 20 min por módulo.

El flujo final lo opera una persona real: el cliente conversa con el elicitador, y las personas
deciden en N6, N9 y N17. La verificación debe ser, además, repetible y medible.

La decisión afecta a:
- `src/multiagente/agentes/`, `src/multiagente/interfaces/` y `src/multiagente/orquestador/`;
- `scripts/`, `tests/integracion/` y `evaluacion/casos/`.

## Factores de decisión

- RF-26 a RF-28, RF-38, RNF-01, RNF-09 y RNF-10.
- Decisiones 1 y 4 de `CLAUDE.md`: el desarrollador no tiene RAG y los agentes solo se comunican
  por el estado.
- Lo aprendido en los pasos 7 a 10:
  - verificar en código lo verificable;
  - no ocultar las fallas reintentando hasta que pase.

## Opciones consideradas

- A. Solo una persona real opera el flujo; la condición se verifica con sus sesiones.
- B. Persona real en el script y, para la prueba repetible, un cliente simulado con casos
  sintéticos, como en el paso 7.
- C. Solo el cliente simulado.

## Resultado de la decisión

Opción elegida: «B», por decisión del equipo:
- La A no deja una prueba repetible y su medición depende de la disponibilidad de las personas.
- La C no ejercita el flujo que usará Realtix.

### Decisiones del equipo

1. **Persona real y tres casos.**
   - El script `producir_modulo.py` permite a una persona operar el flujo completo como cliente y
     revisora.
   - Para la prueba, el cliente simulado corre tres casos con tres corridas cada uno.
2. **Corrección de la fidelidad de N3.** Un número en letras cuenta como el mismo número en
   cifras (ver Mediciones).
3. **Analista simulado en N6.** Si N6 llega con defectos escalados, rechaza una vez y pasa los
   defectos y las preguntas abiertas como observaciones. Si vuelven, porque el cliente no lo sabe,
   aprueba, y los defectos quedan en `defectos_escalados`. Es lo que haría la persona.
4. **Falla de un nodo en la prueba.** La sesión se reanuda una vez desde su último punto de
   control, como lo haría el operador con `--sesion` (RF-28), y la reanudación se reporta. El
   sistema no cambia: N10 sigue con un reintento (ADR-0011).

### Decisiones de implementación

5. **Fábrica de servicios** (`agentes/servicios.py`). `crear_servicios` arma los cuatro agentes
   reales:
   - el elicitador, el arquitecto y el tester comparten la conexión, el vectorizador y el cliente;
   - el desarrollador recibe solo el cliente, sin conexión ni recuperador.
6. **Presentación de los puntos de control** (`interfaces/consola.py`).
   - Las funciones de N6 y N9 se movieron sin cambios desde los scripts de los pasos 7 y 8.
   - `mostrar_validacion` presenta N17: los archivos y el reporte del tester.
   - Una prueba las ejercita con los datos reales de cada pausa.
7. **Validación de cada versión** (`orquestador.ejecucion.validaciones`).
   - El estado solo guarda la validación vigente.
   - Las anteriores se leen de los puntos de control guardados tras cada N14.
   - Así se sabe qué reglas rechazaron cada versión (RF-33).
8. **Script del flujo completo** (`scripts/producir_modulo.py`).
   - **Modo por defecto: persona real.** PostgreSQL guarda la sesión; `/salir` la pausa y
     `--sesion` la reanuda, también tras la falla de un nodo.
   - **`--simulado CASO`:** con `--aprobar` y `--rechazar PUNTO OBSERVACION`.
   - **`--salida`:** escribe cada versión y su `REPORTE_VALIDACION.md` para revisar el código antes
     de decidir en N17.
   - **Traza:** `docs/mediciones/paso-11-extremo-a-extremo.jsonl`.
   - **Resumen:** versiones con sus reglas, iteraciones, turnos, tiempo y costo por nodo. Suma
     también las llamadas de procesos anteriores de la misma sesión.
9. **Turnos y cierre de la elicitación.** Se miden aparte:
   - **turno:** la respuesta del cliente hasta la siguiente pregunta (RNF-01, 15 s);
   - **cierre:** la respuesta que confirma el resumen, que incluye la síntesis y la verificación
     (N5 y N6).

   Mezclarlos daba un «turno» de 18,7 s que en realidad era la síntesis.
10. **Prueba de terminado** (`tests/integracion/test_extremo_a_extremo_nube.py`). Una sesión por
    caso con los cuatro agentes reales e `InMemorySaver` con el serializador propio, que ejercita
    la lista blanca con artefactos reales. Exige:
    - N17 con veredicto aprobado dentro del límite de iteraciones;
    - un caso del plan de N16 por escenario, cada uno cumplido con su prueba como evidencia;
    - ningún hallazgo Alta ni Media;
    - fase `VALIDADO` con las aprobaciones registradas;
    - 20 min o menos de tiempo del sistema.
11. **Casos sintéticos** `elicitacion-avaluo.md` (02) y `elicitacion-liquidacion-lotes.md` (03).
    Tienen las reglas de sus casos de diseño y no contienen datos de Realtix.

### Mediciones (2026-10-09)

Modelos: `gpt-5.4-mini` en N3 y N5, `gpt-5` en N8, `gpt-6.1-sol` en N10, `gpt-6-luna` en N14 y
`gpt-5.4-mini` como cliente simulado.

**Corridas de diagnóstico.**
- **Primera corrida, por script, con mutación:** ARQ-01, 4 módulos, aprobado en la versión 1, en
  3,7 min y por 0,25 USD.
- **Primera ejecución de la prueba:**
  - lotes y mutación aprobados; mutación necesitó dos versiones porque el tester rechazó la v1
    con 5 hallazgos CAL-FS-002 (pruebas que fallaban);
  - avalúo se detuvo en N6 con una pregunta abierta.
- **Defecto encontrado en N3.** Al reproducir el avalúo hasta N6, el cliente rechazó el mismo
  resumen seis veces seguidas: «falta indicar que la vigencia debe ser de cuatro dígitos».
  - Se reprodujo la llamada sobre el turno guardado: el modelo escribía `4 dígitos` y el filtro de
    fidelidad lo descartaba, porque el cliente había dicho «cuatro».
  - **Corrección:** `fidelidad.raices` equipara los números en letras con sus cifras, de cero a
    veinte, las decenas, cien y mil. «Uno» y «una» se omiten, porque casi siempre son artículos,
    y los compuestos no se reconocen.
- **Segunda ejecución,** con la política inicial de N6 (fallar si los defectos vuelven tras un
  rechazo):
  - avalúo aprobado;
  - lotes detenido en N10: el primer intento no importaba las excepciones declaradas y el
    reintento degeneró un archivo de pruebas;
  - mutación detenida en N6: la pregunta abierta sobre los estados del seguimiento volvió, porque
    el caso no los define.

  De ahí salen las decisiones 3 y 4.

**Condición de terminado: tres ejecuciones, nueve corridas, nueve aprobadas.**

| Ejecución | Caso | Arquitectura | Módulos | Casos del plan | Versiones | Tiempo del sistema | Costo |
|---|---|---|---|---|---|---|---|
| 1 | Avalúo | ARQ-01 | 4 | 3 | 1 | 2,9 min | 0,177 USD |
| 1 | Lotes | ARQ-03 | 8 | 5 | 1 | 5,7 min | 0,369 USD |
| 1 | Mutación | ARQ-01 | 2 | 3 | 1 | 5,3 min | 0,272 USD |
| 2 | Avalúo | ARQ-02 | 4 | 3 | 1 | 3,9 min | 0,238 USD |
| 2 | Lotes | ARQ-03 | 7 | 4 | 1 | 4,0 min | 0,271 USD |
| 2 | Mutación | ARQ-01 | 4 | 5 | 1 | 14,3 min | 0,238 USD |
| 3 | Avalúo | ARQ-01 | 2 | 3 | 1 | 2,7 min | 0,157 USD |
| 3 | Lotes | ARQ-03 | 8 | 4 | 1 | 5,4 min | 0,331 USD |
| 3 | Mutación | ARQ-04 | 4 | 3 | 2 | 5,7 min | 0,346 USD |

- Cada arquitectura elegida está entre las candidatas de arq-003 para su caso.
- Ninguna corrida necesitó el rechazo en N6, la aprobación con defectos ni la reanudación: las
  decisiones 3 y 4 no se ejercitaron.

**Ciclo de corrección y umbral 0.** De los 14 módulos que llegaron al tester en todas las
corridas, incluida la de persona real, 11 salieron aprobados en la versión 1 y 3 en la versión 2.
Ninguno escaló.
- Los tres rechazos del tester se debieron a hallazgos Alta:
  - 5 pruebas que fallaban (CAL-FS-002);
  - un docstring incompleto (CAL-MT-001);
  - tres pruebas que el juez de N14 marcó porque no verificaban su escenario (CAL-FS-001).
- **Ningún hallazgo Media rechazó un módulo:** el prompt 1.1 de N10 (ADR-0012) eliminó las
  importaciones privadas y sin uso que traía el paso 9. El único hallazgo Media (CAL-SG-008, en la
  corrida con persona real) llegó junto con tres Alta.
- Los hallazgos Baja (estilo, CAL-MT-009) aparecen en 4 de 9 corridas y no bloquean.

**Costo por módulo** (sin el cliente simulado):
- de 0,157 a 0,369 USD, con una media de 0,267 USD;
- por caso, en media: avalúo 0,191, mutación 0,285 y lotes 0,324 USD.

| Nodo | Modelo | Costo medio por módulo | Participación |
|---|---|---|---|
| N10 | gpt-6.1-sol | 0,136 USD | 51 % |
| N8 | gpt-5 | 0,081 USD | 31 % |
| N3 | gpt-5.4-mini | 0,038 USD | 14 % |
| N5 | gpt-5.4-mini | 0,011 USD | 4 % |
| N14 | gpt-6-luna | 0,001 USD | 0,4 % |

**Tiempo** (RNF-01).
- **Por módulo:** de 2,7 a 14,3 min, con mediana de 5,3 min. Todo dentro de 20 min.
  - El máximo se debe a N10: dos llamadas que sumaron 727 s.
  - En las demás corridas, N10 sumó de 56 a 243 s por módulo.
- **Turnos de diálogo:** 90 de 91 tardaron menos de 15 s, con máximos por corrida de 3,5 a 6,4 s.
  - Un turno tardó 51,0 s. Su N3 sumó 84,6 s en 19 llamadas, frente a 19 a 62 s en las demás
    corridas: fue la latencia de una llamada al servicio.
- **Cierre de la elicitación:** de 6,2 a 16,3 s.

**N10 al primer intento.** 5 de las 9 primeras generaciones fallaron la verificación
estructural, y el reintento las corrigió todas. Hubo dos causas:
- **Excepción declarada sin definir ni importar:** 3 veces, la misma causa del único reintento
  del paso 9.
- **Sangría rota:** 2 veces. Es la degeneración que el paso 9 vio con esfuerzo `low` y que sigue
  con `medium`, con menos frecuencia.

Contando las corridas de diagnóstico, la sangría rota apareció en 4 salidas:
- en 3 era un archivo de pruebas, en la línea 25 o 45, y en 2 de ellas faltaba además `USO.md`;
- en 1 de las 4, el reintento también falló.

**Otros reintentos:** uno de N8 (un módulo sin requerimientos asignados) y uno de N3.

**Gasto del paso:** cerca de 4,9 USD.
- 2,61 USD en las nueve corridas de la condición de terminado, de ellos 0,21 USD del cliente
  simulado.
- 0,41 USD en la corrida con persona real.
- El resto en el diagnóstico.

**Corrida con persona real** (sesión `e076fd72-c5d5-4d2c-9bf3-4bf90bd61913`). Julián operó el
flujo completo por consola, como cliente y como revisor en los tres puntos de control, con una
necesidad propia fuera del dominio catastral: un microservicio de búsqueda binaria.
- **Elicitación:** 9 respuestas del cliente.
  - En N6 rechazó con una observación: control de errores para entradas inválidas y prioridad
    media.
  - El flujo volvió al diálogo, se sintetizó de nuevo y aprobó. Quedó un RF con 3 escenarios.
- **Diseño:** ARQ-05 con 4 módulos, aprobado en N9.
- **Ciclo de corrección:**
  - **v1:** el tester la rechazó. El juez marcó los tres casos (CAL-FS-001, Alta: pruebas que
    pasan sin verificar su escenario), y se sumaron un generador pseudoaleatorio (CAL-SG-008,
    Media, S311) y dos hallazgos de estilo.
  - **v2:** corrigió los seis defectos y salió aprobada.
- **Aprobación final (RF-38):**
  - En N17 rechazó con una observación: cambiar el número de nodos de 15 a 20.
  - La v3 cambió solo eso, en una llamada de 6,9 s y 0,026 USD, y el tester la aprobó.
  - La aprobó en N17: fase `validado`.
- **Costo:** 0,41 USD en 30 llamadas. N10 costó 0,285 en 4 llamadas, N8 0,056, N5 0,035, N3 0,033
  y N14 0,002.
- **Tiempo:** las llamadas a modelos sumaron 6,5 min, de ellos 4,3 de N10. La sesión duró 26 min
  con la espera humana.
- **Defecto de usabilidad del script, corregido.**
  - Tras elegir aprobar o rechazar, el script pedía `Revisor [Analista]:`, y se tomó por un pedido
    de comentarios.
  - Por eso, en las aprobaciones de la sesión quedaron como revisor la observación, «aprobado» y
    «apruebo».
  - Ahora pide primero las observaciones del rechazo y después el nombre, con una etiqueta
    explícita.
- **Iteraciones:** el contador llegó a 3 de 3. El rechazo en N17 continúa el contador del ciclo
  de corrección (ADR-0006), así que, si el tester hubiera rechazado la v3, la sesión habría
  escalado.

### Consecuencias

- **Favorable:** la condición de terminado se cumple con los cuatro agentes reales en nueve de
  nueve corridas sobre tres casos y cuatro arquitecturas. El ciclo de corrección corrió entre el
  desarrollador y el tester reales, y cerró en dos versiones.
- **Favorable:** el umbral 0 no encarece el ciclo. Los rechazos vienen de hallazgos Alta, que
  importan sea cual sea el umbral.
- **Favorable:** el juez de N14 detectó en un módulo real lo que el paso 10 solo había visto en
  el corpus: pruebas que pasan sin verificar su escenario. El desarrollador las corrigió con la
  retroalimentación.
- **Favorable:** hay costo por módulo para el modelo de costos y el presupuesto del paso 13: de
  0,16 a 0,37 USD, y la mitad es N10.
- **Favorable:** una persona operó el flujo completo por consola, con una necesidad propia y
  rechazos en N6 y en N17, hasta un módulo validado.
- **Desfavorable: N10 falla al primer intento en más de la mitad de las corridas.**
  - El reintento lo absorbe, pero duplica el costo y la latencia de N10.
  - Cuando el reintento también falla, la sesión se detiene hasta que alguien la reanuda.
  - **Propuesta:** guardar la salida rechazada para diagnosticar la sangría rota, y reforzar en
    el prompt la importación de las excepciones declaradas.
- **Desfavorable: la latencia de los servicios varía mucho.** Hubo un turno de 51 s y una
  generación de 727 s. Ninguno rompió los 20 minutos, pero el RNF-01 por turno se incumplió una
  vez.
- **Desfavorable: un defecto que requiere al cliente arrastra a los corregibles.** Cuando escala
  una pregunta abierta, los defectos de redacción (C5) llegan a la persona sin corrección
  automática (ADR-0008).
- **Desfavorable: las decisiones 3 y 4 no se ejercitaron en las corridas simuladas.** La corrida
  con persona real sí ejercitó los retornos de N6 y de N17 con los agentes reales.
- **Desfavorable: un rechazo en N17 consume iteraciones del ciclo de corrección.** En la corrida
  con persona real, el contador llegó al límite. El paso 12 debe mostrar a la persona cuántas
  iteraciones quedan antes de decidir.
- **Desfavorable: el cliente simulado no es una persona.** Los casos sintéticos son pocos y bien
  definidos; el paso 15 medirá con casos de referencia.

### Confirmación

- `pytest`:
  - la fábrica de servicios;
  - la presentación de los tres puntos de control;
  - la carga de los casos;
  - la validación de cada versión desde el historial;
  - la fidelidad con números en letras.
- `pytest -m "nube and embeddings and sandbox" tests/integracion/test_extremo_a_extremo_nube.py`:
  es la condición de terminado.
- `python scripts/producir_modulo.py --salida evaluacion/resultados`: el flujo con persona real.
- `python scripts/producir_modulo.py --simulado evaluacion/casos/<caso>.md --aprobar`.

## Análisis de las opciones

### Opción A · Solo persona real
- Favorable, porque es el uso real del sistema.
- Desfavorable, porque no es repetible ni permite medir varias corridas sin ocupar al equipo.

### Opción B · Persona real y cliente simulado
- Favorable, porque cubre el uso real y deja una prueba repetible con mediciones comparables.
- Desfavorable, porque el cliente simulado es más ordenado que una persona y cuesta un poco más.

### Opción C · Solo cliente simulado
- Favorable, porque es barata y repetible.
- Desfavorable, porque nunca verifica que una persona pueda operar el flujo.
