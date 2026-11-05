# Informe de evaluación del objetivo 4

Evaluación del sistema multiagente con métricas de tiempo, costo y tasa de errores, contrastadas con los
requerimientos no funcionales y con el desarrollo independiente de un modelo de lenguaje. Paso 15 del plan
de trabajo, 5 de noviembre de 2026. El diseño está en el ADR-0019.

## 1. Conclusión

- **El sistema opera dentro de su límite de tiempo por módulo y de su presupuesto,** con una excepción: un turno de diálogo de
  16,2 s frente a los 15 s del RNF-01.
- **El sistema no entrega menos errores que un modelo de lenguaje solo.** Con las mismas pruebas de
  referencia, la tasa de errores es de 3,4 % en el sistema y de 5,4 % en el modelo con diálogo, y queda
  empatada caso a caso (mejor en 2, peor en 2 e igual en 5). La hipótesis H1 no se sostiene.
- **El sistema cuesta y tarda el doble o más,** en los nueve casos: 0,358 USD y 5,9 min por módulo, frente a
  0,170 USD y 2,9 min del LLM con diálogo, y 0,104 USD y 2,5 min del LLM de un solo prompt.
- **Con la información completa, un modelo solo no falló ninguna verificación:** 90 de 90. En estos módulos
  pequeños, escribir el código no es el cuello de botella. Los errores nacen al transmitir la información.
- **Lo que el sistema agrega no es corrección del código, sino lo que rodea al código:** requerimientos
  formales y trazables, diseño de un catálogo cerrado, validación independiente con reporte, ciclo de
  corrección, puntos de control humano y control de costo. Un modelo solo no produce nada de eso.
- **Frente al modelo con la misma información, el sistema deja código con menos hallazgos:** 3 de 12 implementaciones con
  hallazgos, frente a 10 de 15, y ninguna entrega lista con pruebas en rojo, frente a 3 de 15. Otras mediciones no marcan
  diferencia o van en contra (sección 3.6).

La evaluación mide el sistema, no busca demostrar su superioridad: el resultado es mixto y se reporta tal cual.

## 2. Diseño

### 2.1 Por qué se compara con un modelo de lenguaje

La comparación con desarrollo humano no se hizo. Realtix no puede compartir sus desarrollos por el acuerdo
de confidencialidad. Una implementación hecha por los autores no sería independiente, porque construyeron el
sistema y conocen los casos. El código abierto de repositorios públicos tampoco sirve, porque no implementa
estas fichas ni trae tiempos ni costos. Por eso, el ahorro frente al trabajo humano no se cuantifica y queda
como recomendación.

La pregunta que sí se responde es qué aporta la arquitectura multiagente frente a un solo modelo de lenguaje.

### 2.2 Enfoques

Los tres usan `gpt-6.1-sol` para escribir el código, de modo que la diferencia sale de la arquitectura.

| Enfoque | Qué recibe | Corridas |
|---|---|---|
| **Sistema multiagente** | La necesidad; conversa con un cliente simulado. Un analista simulado decide en los puntos de control | 12 (9 casos; 3 de ellos, dos veces) |
| **LLM con diálogo** | La necesidad; conversa con el mismo cliente simulado y entrega todo en una respuesta | 15 (3 casos × 3 y 6 casos × 1) |
| **LLM de un solo prompt** | En un mensaje, lo que sabe el cliente | 9 (9 casos × 1) |

El LLM con diálogo tiene la misma información que el sistema. El de un solo prompt tiene la información
completa, que es el mejor caso para un modelo solo, y en la práctica supone que alguien ya hizo la elicitación.

### 2.3 Casos

Nueve casos sintéticos, sin datos de Realtix, que cubren las seis arquitecturas del catálogo.

| Caso | Tema | Arquitectura | Verificaciones | Mutantes |
|---|---|---|---|---|
| 01 | Comisiones de corretaje | ARQ-01 | 9 | 4 |
| 02 | Reajuste del canon | ARQ-01 | 9 | 3 |
| 04 | Contratos de arrendamiento | ARQ-02 | 13 | 5 |
| 07 | Conciliación del recaudo | ARQ-03 | 9 | 4 |
| 10 | Tarifa del impuesto predial | ARQ-04 | 10 | 4 |
| 12 | Dígito de verificación del NIT | ARQ-04 | 10 | 3 |
| 14 | Escaneos de expedientes | ARQ-05 | 11 | 5 |
| 16 | Simulador de amortización | ARQ-05 | 10 | 3 |
| 17 | Trámites catastrales | ARQ-06 | 9 | 4 |
| **Total** | | | **90** | **35** |

**Selección:** 02, 12 y 16 se eligieron antes de medir. Los otros seis son el primer caso de cada arquitectura,
por número y sin mirar su resultado. Por esa regla entró el caso 14, en el que el sistema escaló.

### 2.4 Oráculo

La tasa de errores se mide con **pruebas de aceptación de referencia**, las mismas para los tres enfoques e
independientes de las que cada uno escribe para sí.

- **Solo lo que la ficha dice sin ambigüedad:** ejemplos con cifras, reglas, rangos y mensajes textuales. Cada
  `interfaz.md` lista qué verifica cada prueba, de qué frase sale y qué queda fuera.
- **Validado antes de medir:** cada control pasa todas las verificaciones y cada uno de los 35 mutantes falla
  al menos una.
- **Fijado antes de ver las salidas:** las pruebas de los seis casos nuevos se versionaron (`fdcba8f`) antes de
  abrir sus salidas y de correr las líneas base. La corrida ampliada del sistema ya estaba hecha. De los casos
  10 y 14 ya se conocían hallazgos del tester, no su código.
- **Adaptadores:** cada implementación se conecta con un adaptador que solo traduce la interfaz. Una verificación
  automática rechaza los que hacen aritmética o calculan por su cuenta.

## 3. Resultados de la comparación

### 3.1 Por enfoque

| Métrica | Sistema | LLM con diálogo | LLM de un solo prompt |
|---|---|---|---|
| Corridas | 12 | 15 | 9 |
| Verificaciones que pasan | 115 de 119 | 140 de 148 | 90 de 90 |
| **Tasa de errores** | **3,4 %** | **5,4 %** | **0,0 %** |
| Entregas sin ningún error | 9 de 12 | 13 de 15 | 9 de 9 |
| **Costo medio por módulo** | **0,358 USD** | **0,170 USD** | **0,104 USD** |
| **Tiempo medio de máquina** | **5,9 min** | **2,9 min** | **2,5 min** |
| Entregas con pruebas propias que fallan | 1 de 12 | 3 de 15 | 2 de 9 |
| Hallazgos de Ruff por entrega | 0,3 | 1,2 | 1,0 |

El costo no cuenta al cliente simulado, y el tiempo no cuenta su latencia.

**Las pruebas propias que fallan no señalan errores del código.** Las seis entregas pasan todas las
verificaciones de referencia:
- **LLM, cinco entregas:** lo que falla es, en su mayoría, el valor que esperaba la prueba que escribió el modelo,
  como `assert '8' == '7'`. Un modelo solo no ejecuta lo que entrega, así que no lo nota, y su `USO.md` no lo
  advierte. Quien recibe el módulo ve pruebas en rojo y debe averiguar si falla el código o la prueba.
- **Sistema, una entrega:** `sistema-02-1` es la sesión escalada por el escenario imposible del caso 02. El tester
  rechazó sus tres versiones, y N17 no permite aprobarla.

### 3.2 Por caso

Tasa de errores; entre paréntesis, las verificaciones que pasan.

| Caso | Sistema | LLM con diálogo | LLM de un solo prompt |
|---|---|---|---|
| 01 | 0,0 % (9 de 9) | 0,0 % (9 de 9) | 0,0 % (9 de 9) |
| 02 | 5,6 % (17 de 18) | 0,0 % (27 de 27) | 0,0 % (9 de 9) |
| 04 | 7,7 % (12 de 13) | 0,0 % (13 de 13) | 0,0 % (13 de 13) |
| 07 | 0,0 % (9 de 9) | 0,0 % (9 de 9) | 0,0 % (9 de 9) |
| 10 | 0,0 % (10 de 10) | 0,0 % (10 de 10) | 0,0 % (10 de 10) |
| 12 | 0,0 % (20 de 20) | 0,0 % (30 de 30) | 0,0 % (10 de 10) |
| 14 | 0,0 % (11 de 11) | 9,1 % (10 de 11) | 0,0 % (11 de 11) |
| 16 | 10,0 % (18 de 20) | 23,3 % (23 de 30) | 0,0 % (10 de 10) |
| 17 | 0,0 % (9 de 9) | 0,0 % (9 de 9) | 0,0 % (9 de 9) |

Costo y tiempo medios por caso:

| Caso | Sistema | LLM con diálogo | LLM de un solo prompt |
|---|---|---|---|
| 01 | 0,181 USD · 3,3 min | 0,099 USD · 1,7 min | 0,065 USD · 1,6 min |
| 02 | 0,261 USD · 4,4 min | 0,165 USD · 2,6 min | 0,068 USD · 1,7 min |
| 04 | 0,353 USD · 6,1 min | 0,222 USD · 3,7 min | 0,153 USD · 3,7 min |
| 07 | 0,377 USD · 7,0 min | 0,229 USD · 4,7 min | 0,120 USD · 2,9 min |
| 10 | 0,390 USD · 6,2 min | 0,148 USD · 2,8 min | 0,092 USD · 2,3 min |
| 12 | 0,312 USD · 5,3 min | 0,152 USD · 2,8 min | 0,093 USD · 2,3 min |
| 14 | 0,690 USD · 10,3 min | 0,165 USD · 3,0 min | 0,150 USD · 3,8 min |
| 16 | 0,384 USD · 5,8 min | 0,180 USD · 3,0 min | 0,089 USD · 2,0 min |
| 17 | 0,393 USD · 6,7 min | 0,204 USD · 3,2 min | 0,102 USD · 2,4 min |

### 3.3 Comparación caso a caso

Prueba de signos sobre los nueve casos. Es exploratoria, con muestra pequeña y casos no aleatorios.

| El sistema frente a | Magnitud | Mayor en | Menor en | Empates | Valor p |
|---|---|---|---|---|---|
| LLM con diálogo | Costo | 9 | 0 | 0 | 0,004 |
| LLM con diálogo | Tiempo | 9 | 0 | 0 | 0,004 |
| LLM con diálogo | Errores | 2 | 2 | 5 | 1,000 |
| LLM de un solo prompt | Costo | 9 | 0 | 0 | 0,004 |
| LLM de un solo prompt | Tiempo | 9 | 0 | 0 | 0,004 |
| LLM de un solo prompt | Errores | 3 | 0 | 6 | 0,250 |

### 3.4 De dónde vienen los errores

| Implementación | Lo que falla | Dónde se perdió |
|---|---|---|
| Sistema, caso 02, corrida 2 | Cambia el mensaje exacto del cliente | La síntesis parafraseó el mensaje en el escenario |
| Sistema, caso 04 | No conserva el registro de cambios de estado | La síntesis cambió «queda registrado» por «se devuelve» |
| Sistema, caso 16, corrida 1 | Sin herramienta de terminal, y rechaza tasas como 9,75 % | El requerimiento estaba bien: el diseño pasó la tasa a fracción con dos decimales y no declaró la terminal |
| LLM con diálogo, caso 14 | No trata los espacios como separadores | El dato no aparece en su conversación con el cliente |
| LLM con diálogo, caso 16, corrida 3 | Valida los datos, pero no calcula | El cliente no definió el redondeo, y el modelo lo dejó pendiente en vez de calcular |

- **Ningún error de una versión final nace de escribir mal una regla que el desarrollador tenía clara.** El único
  caso así fue una fórmula mal escrita en la v1 del caso 12, corrida 2 del sistema, y la detuvo el tester.
- **Cada paso añadido es un lugar donde se puede perder información.** El sistema transmite lo que dijo el cliente
  por el registro, los requerimientos, la especificación y el código.
- **Lo que mueve el error del LLM con diálogo es una sola corrida:** sin el caso 16, corrida 3, su tasa baja a
  0,7 %, por debajo del sistema. Esto impide atribuirle al sistema una ventaja.

### 3.5 Lo que entrega cada enfoque

| Entregable | Sistema | LLM solo |
|---|---|---|
| Código, pruebas y documentación de uso | Sí | Sí |
| Historias de usuario y requerimientos formales (Anexo A) | Sí | No |
| Registro de decisión y especificación de diseño (Anexo B) | Sí | No |
| Plan de pruebas de aceptación y reporte de validación | Sí | No |
| Validación independiente con veredicto | Sí | No |
| Ejecución en un entorno aislado antes de entregar | Sí | No |
| Puntos de control humano | Tres | Ninguno |
| Traza de costo por nodo y presupuesto por módulo | Sí | No |

### 3.6 Mediciones del aporte del sistema

Reúne con cifras lo que el sistema agrega. Las reglas de calidad se fijaron y se versionaron antes de calcularlas (`b55405e`), y sus
detectores, antes de medir (`f0c5255`). Se reportan todas. Son exploratorias, con detectores aproximados, y se regeneran con
`python scripts/calidad_estatica.py`.

**De métricas ya fijadas o de resultados existentes:**

| Medición | Sistema | LLM con diálogo | LLM de un solo prompt |
|---|---|---|---|
| Implementaciones con hallazgos de Ruff | 3 de 12 | 10 de 15 | 4 de 9 |
| Hallazgos de severidad media | 0 | 2 | 1 |
| Pruebas propias en rojo en una entrega que queda como lista | 0 de 12 | 3 de 15 | 2 de 9 |
| Peor implementación frente al oráculo | 80 % | 30 % | 100 % |
| Requerimientos formales por sesión | 2,25 | 0 | 0 |
| Casos de aceptación con veredicto propio, por sesión | 8,25 | 0 | 0 |
| Pruebas propias ejecutadas por implementación | 46 | 79 | 78 |

**Ciclo de corrección:** la tasa de errores del sistema frente al oráculo baja de 9,2 % en la primera versión (108 de 119) a 3,4 % en la
final (115 de 119). Toda la mejora viene del caso 12.

**De las reglas de calidad,** media por implementación:

| Regla y métrica | Mejor | Sistema | LLM con diálogo | LLM de un solo prompt | Frente al diálogo: mejor, peor, igual | Frente a un prompt: mejor, peor, igual |
|---|---|---:|---:|---:|---:|---:|
| CAL-FS-005, usos de `float` monetario | menos | 0 | 0 | 0 | 0, 0, 9 | 0, 0, 9 |
| CAL-SG-001, credenciales en el código | menos | 0 | 0 | 0 | 0, 0, 9 | 0, 0, 9 |
| CAL-MT-003, complejidad media por función | menos | 2,00 | 2,78 | 2,49 | 8, 1, 0 | 9, 0, 0 |
| CAL-MT-003, complejidad máxima | menos | 5,75 | 6,00 | 5,67 | 4, 4, 1 | 2, 3, 4 |
| CAL-MT-010, nombres privados importados | menos | 0 | 0,07 | 0 | 1, 0, 8 | 0, 0, 9 |
| CAL-FB-001, sentencias `global` | menos | 0 | 0 | 0 | 0, 0, 9 | 0, 0, 9 |
| CAL-FB-003, recursos fuera de `with` | menos | 0 | 0 | 0 | 0, 0, 9 | 0, 0, 9 |
| CAL-FB-004, usos no deterministas en las pruebas | menos | 0,25 | 0,07 | 0,22 | 0, 2, 7 | 0, 1, 8 |
| CAL-FS-004, pruebas que esperan un rechazo | más | 8,92 | 6,93 | 10,44 | 6, 2, 1 | 5, 4, 0 |
| CAL-FS-004, proporción de pruebas de rechazo | más | 45 % | 31 % | 36 % | 7, 2, 0 | 6, 3, 0 |
| Contexto, módulos | — | 4,50 | 1,67 | 1,78 | | |
| Contexto, líneas de código | — | 298 | 180 | 208 | | |
| Contexto, líneas de pruebas | — | 183 | 215 | 278 | | |
| Contexto, funciones de prueba | — | 19,75 | 23,07 | 27,56 | | |

**Lectura:**
- **A favor:** menos implementaciones con hallazgos, ninguna entrega lista con pruebas en rojo, una peor implementación menos grave que la del
  LLM con diálogo, menor complejidad media y mayor proporción de pruebas de rechazo. El tester no revisa CAL-FS-004, así que ahí el sistema no tenía
  ventaja de entrada.
- **Sin diferencia:** en dinero, credenciales, `global` y recursos, ningún enfoque tiene hallazgos, así que un modelo capaz ya cumple esas reglas.
  La complejidad máxima también empata.
- **En contra o con matiz:** el sistema escribe más código y menos pruebas, y tiene algo más de usos no deterministas en las pruebas. La complejidad
  media baja sobre todo por tener más funciones pequeñas, y el LLM de un solo prompt escribe más pruebas de rechazo en cantidad.
- **Sobrecosto frente al LLM con diálogo:** 0,19 USD y 3,0 min por módulo, además de la razón de dos a uno. El LLM de un solo prompt es un techo: supone
  que alguien ya hizo la elicitación.
- **No evaluables en un modelo solo,** porque exigen especificación o requerimientos: CAL-AR-001 a CAL-AR-005, CAL-MT-005, CAL-MT-006, CAL-MT-008,
  CAL-FS-001 y CAL-SG-005.
- **Revisión a mano de dos implementaciones,** `sistema-16-2` y `modelo-unico-16-1`: módulos, pruebas, líneas y complejidad coinciden. También se revisaron
  todas las aperturas de recursos, 13, todas con `with`.
- **Límite del detector de dinero:** no ve uniones de tipos. La palabra `float` aparece en el código 0 veces en el sistema, 2 en el LLM con diálogo y 8 en el
  de un solo prompt, como tipo de entrada aceptado o en promedios, y esas implementaciones pasan el oráculo.

## 4. Desempeño del tester

### 4.1 Con defectos inyectados (Tabla 26)

Corpus de 21 defectos y 3 controles, en 3 corridas, por 0,04 USD.

| | Defecto | Sin defecto |
|---|---|---|
| Rechaza | 63 | 0 |
| Aprueba | 0 | 9 |

Exactitud, precisión, sensibilidad y F1 de 1,00. Por caso, el juez de N14 tuvo 5 rechazos falsos en 261 casos
juzgados (1,9 %), que no cambiaron el veredicto de ninguna variante.

### 4.2 Frente al oráculo, en módulos reales

Cada versión que el tester dictaminó en los casos de referencia, 21 en total. Lo positivo es que el oráculo falle.

| | Con error de referencia | Sin error de referencia |
|---|---|---|
| Rechaza | 4 | 8 |
| Aprueba | 2 | 7 |

Exactitud 0,52, precisión 0,33, sensibilidad 0,67 y F1 0,44.

**Cómo leerla.** El tester y el oráculo no miden lo mismo: el tester juzga el módulo y sus pruebas frente a los
requerimientos que elicitó el sistema; el oráculo, solo el comportamiento frente a la ficha.

| Celda | Versiones | Causa |
|---|---|---|
| Rechazos sin error | Caso 10, v1 y v2 | **Justificados:** pruebas que fallan en la capa HTTP, que el oráculo no cubre |
| | Caso 02, corrida 1, v1 a v3 | Un escenario imposible escrito por el elicitador |
| | Caso 14, v1 a v3 | Pruebas débiles y un escenario de tarea programada que no se puede observar |
| Aprobados con error | Caso 02, corrida 2; caso 04 | El requerimiento ya venía mal: el tester no ve lo que se perdió al elicitar |

Si los dos rechazos del caso 10 se cuentan como aciertos, quedan exactitud 0,62, precisión 0,50, sensibilidad 0,75
y F1 0,60. La muestra es pequeña y descriptiva, pero alcanza para matizar el 1,00 del corpus.

### 4.3 Estabilidad del juez

En la corrida ampliada, el juez cambió de veredicto en 3 de 124 rejuicios de una prueba idéntica, siempre hacia el
rechazo y aun con la segunda opinión. Eso hizo escalar el caso 16 y alargó el caso 20.

## 5. Corrida ampliada: 20 casos, solo el sistema

| Criterio del ADR-0015 | Meta | Corrida final del ADR-0015 | Paso 15 | ¿Cumple? |
|---|---|---|---|---|
| Validados en la v1 | al menos 15 de 19 | 18 de 20 | 11 de 20 | no |
| Primeros intentos de N10 rechazados | como máximo 2 de 29 | 7 de 23 | 4 de 35 | no |
| Sesiones escaladas | 0 | 0 | 4 | no |
| Costo medio por módulo validado | como máximo 0,35 USD | 0,342 | 0,391 | no |
| Hallazgos de pruebas que simulan el efecto | 0 | 0 | 0 | sí |
| Turnos sin exploración | como máximo 211 | 210 | 205 | sí |
| Resúmenes confirmados | al menos 17 de 20 | 16 | 19 | sí |

- **Decisiones 37 a 39:** cumplieron su objetivo. Los resúmenes confirmados suben de 16 a 19, las sesiones en el
  límite de turnos bajan de 5 a 1 y los requerimientos salen más completos, de 43 a 51.
- **El retroceso en la v1** no se debe a un cambio del sistema: los prompts, los modelos y el consumo por nodo son
  los mismos. Causas: escenarios defectuosos de N5 (casos 02, 03, 13 y 19) y el juez. Sin esos cuatro serían 15 de 20.
- **Validados con defecto:** los casos 13 y 19 llevan el defecto del requerimiento al código: uno con una fecha fija
  en producción y otro con un mensaje provisional. El analista simulado aprueba sin leer; una persona debería verlos
  en N17. Esos dos casos no están en el oráculo, así que no entran en la tasa de errores.
- **La corrida adicional** de 02, 12 y 16 salió sin escalar: 2 en la v1 y 1 en la v2, lo que muestra la variabilidad.

## 6. Generación aumentada por recuperación

Las 20 sesiones de la corrida ampliada, por 2,84 USD. Cada métrica va de 0 a 1.

| Colección | Agente | Fidelidad | Relevancia de la respuesta | Relevancia del contexto |
|---|---|---|---|---|
| `elicitacion` | Elicitador | 0,81 | 0,56 | 0,57 |
| `dominio_negocio` | Elicitador | 0,81 | 0,56 | 0,10 |
| `arquitecturas_referencia` | Arquitecto | 0,84 | 0,51 | 0,67 |
| `criterios_calidad` | Tester | 0,47 | 0,37 | 0,42 |

- **`dominio_negocio`:** casi nada de lo recuperado hace falta. El corpus es catastral y tributario, y muchos casos no
  lo son; además, el prompt de N5 solo le permite tomar terminología de ahí.
- **Fidelidad del tester:** el 0,47 subestima. Sus afirmaciones más frecuentes vienen de la ejecución («se ejecutaron
  39 pruebas y todas pasaron»), que no se le entregó al juez. Apartándolas con un filtro de texto aproximado, sube a
  cerca de 0,68. Es un límite del instrumento.
- **Revisión humana de 5 juicios:** un autor los revisó y los validó.

## 7. Requerimientos no funcionales

| Requerimiento | Evidencia | Estado |
|---|---|---|
| RNF-01, tiempo | Módulo: máximo 10,3 min frente a 20. Turno: 16,2 s en una sesión de 20 (caso 05), frente a 15; las demás, hasta 12,4 s | Cumplido en módulos; **un turno lo excede** |
| RNF-02, fiabilidad | Sesiones reanudables; en Azure, el sistema volvió tras un reinicio en 32 s con sus datos | Cumplido |
| RNF-03, entorno aislado | Código generado en contenedor sin red; también en Azure | Cumplido |
| RNF-04, confidencialidad | Embeddings locales a la composición; los prompts se procesan en Azure OpenAI | Cumplido parcialmente |
| RNF-05 y RNF-06, flexibilidad | Modelo de cada nodo por configuración | Cumplido |
| RNF-07, compatibilidad | Windows con WSL2 y Ubuntu 24.04 en Azure; macOS sin verificar | Cumplido parcialmente |
| RNF-08 y RNF-09, interacción y control | Una pregunta por turno y tres puntos de control | Cumplido |
| RNF-10, costo | Presupuesto configurable que detiene la ejecución; 0,391 USD de media por módulo validado | Cumplido |

**Costo por nodo en la corrida ampliada:** N10 44,8 %, N8 27,1 %, N3 18,2 %, N5 9,3 % y N14 0,7 %.

## 8. Hipótesis

| Hipótesis | Cuándo se fijó | Resultado |
|---|---|---|
| **H1:** el sistema tiene menos errores que el modelo único | Antes de medir | **No se sostiene:** 3,4 % frente a 5,4 %, por una sola corrida del modelo, y empate caso a caso |
| **H2:** el sistema cuesta y tarda menos que lo manual | Antes de medir | **Retirada, sin evaluar:** no hubo implementación manual |
| **H3:** los criterios del ADR-0015 con las decisiones 37 a 39 | Antes de medir | **Mixto:** 3 de 7 cumplidos; las tres decisiones cumplen su objetivo |
| **H4:** el sistema cuesta y tarda más que un LLM solo | Exploratoria | **Se sostiene:** el doble o más, en los nueve casos |
| **H5:** el tester detiene defectos que un LLM solo entrega sin aviso | Exploratoria | **En parte:** detuvo el error de fórmula del caso 12 y no dejó aprobar el caso 16, pero aprobó 2 versiones con error |

## 9. Amenazas a la validez

- **Casos sintéticos y módulos pequeños.** Con módulos mayores, el resultado podría ser otro.
- **Poca repetición:** una corrida por enfoque en 6 de los 9 casos. Los modelos son estocásticos: el caso 16 del sistema
  escaló en una corrida y se validó en la v1 en otra.
- **El modelo de comparación es muy capaz.** Con uno menos capaz, la distancia podría crecer.
- **Oráculo del propio equipo,** derivado de las fichas, que el LLM de un solo prompt recibe casi textuales: su 100 % es
  un techo, no una expectativa realista.
- **Alcance del oráculo:** no cubre la capa HTTP, la documentación ni el reintento por etapas.
- **Revisión de los oráculos:** un autor los revisó frente a cada ficha y los validó.
- **Sin personas:** el analista simulado aprueba sin leer, así que no se mide el valor de los puntos de control humano.

## 10. Recomendaciones

1. **Revisar la coherencia de los escenarios en N6,** comparando sus cifras con las reglas, y conservar los mensajes
   textuales del cliente.
2. **Darle a N10 una vía para reportar un escenario imposible,** y a N15 para escalarlo de inmediato.
3. **Conservar el veredicto de una prueba que no cambió,** para evitar que el juez cambie de opinión.
4. **Agregar una regla que detecte en `src/` valores fijados de un escenario.**
5. **Filtrar `dominio_negocio`** cuando la necesidad no pertenezca al dominio.
6. **Comparar con desarrollo humano** en casos reales de Realtix, para cuantificar el ahorro.

## 11. Costo y reproducción

**Costo del paso:** 16,74 USD de inferencia, frente a un tope de 17, incluido el cliente simulado.

| Traza en `docs/mediciones/` | USD |
|---|---|
| `paso-15-corrida-ampliada.jsonl` | 8,8153 |
| `paso-15-modelo-unico.jsonl` | 3,0066 |
| `paso-15-rag.jsonl` | 2,8359 |
| `paso-15-llm-un-prompt.jsonl` | 0,9322 |
| `paso-15-sistema-2.jsonl` | 0,8746 |
| `paso-15-despliegue-azure.jsonl` | 0,2376 |
| `paso-15-tester.jsonl` | 0,0412 |

**Sin costo,** con Docker:

```bash
python scripts/evaluar_referencia.py --oraculo
```

```bash
python scripts/evaluar_referencia.py --manifiesto evaluacion/referencia/implementaciones.json --rehacer
```

```bash
python scripts/tabla_objetivo_4.py
```

```bash
python scripts/matriz_tester_oraculo.py
```
