# Texto de la evaluación para el documento de tesis

Texto listo para llevar al documento, redactado como él: voz impersonal, tiempo pasado, coma decimal y cifras con su
unidad. La fuente es `docs/evaluacion/informe-objetivo-4.md`.

**Cuando este archivo y `01-correcciones.md` o `02-avances.md` traten lo mismo, manda este archivo.** En especial, reemplaza
lo que esos dos dicen de 5.2 a 5.6, 6.4, 6.5, las conclusiones y las recomendaciones.

**Antes de entregar:**
- **`[CONFIRMAR]`:** marca lo que depende de una acción de los autores. Si no se hizo, se quita la frase o se dice que no
  se hizo.
- **`[Tabla A]`, `[Tabla B]`…:** son tablas nuevas. Se numeran al insertarlas en el documento.
- **La sección 5.3 es nueva.** Las actuales 5.3 a 5.6 pasan a ser 5.4 a 5.7.

---

## 1.6.4 Fase 4: actividades y entregables

**Agregar a las actividades de 1.6.4.1:**

- Comparar el sistema con dos líneas base de un solo modelo de lenguaje, mediante pruebas de aceptación de referencia
  comunes a todos los enfoques.

**Reemplazar en los entregables de 1.6.4.2:**

- Informe de evaluación con métricas y conclusiones.
- Producto en local del sistema multiagente de IA, empaquetado en contenedores, y un despliegue de demostración en Azure
  con datos sintéticos.
- Manual y documentos técnicos del sistema multiagente de IA.

---

## 3.8 Vista de despliegue

**Reemplazar el párrafo de las plataformas de nube por:**

Las plataformas de nube que resume la Tabla 38 del Anexo H se tomaron como referencia de las capacidades de un entorno de
producción de agentes. El sistema se concibió para desplegarse en la infraestructura de la empresa, con los modelos de
lenguaje de Azure OpenAI y el modelo de representaciones vectoriales dentro de la composición. Para compartirlo con datos
sintéticos se agregó además un despliegue de demostración en una máquina virtual de Azure, descrito en el capítulo 4, que no
sustituye la entrega en la infraestructura de la empresa.

---

## Capítulo 4: sección nueva, antes de «Producto obtenido»

### Despliegue de demostración en Azure

Para compartir el sistema mediante un enlace público se desplegó la misma composición de contenedores en una máquina virtual
de Azure, con 4 vCPU, 16 GiB de memoria y Ubuntu 24.04, pagada con créditos de estudiante. Se descartaron los servicios
administrados de contenedores, porque no ofrecen el Docker del anfitrión con que la aplicación crea el entorno aislado.

Un proxy, definido en un archivo aparte de la composición de la entrega, publica la interfaz web con TLS y contraseña. La base
de datos, el servicio de representaciones vectoriales y el socket de Docker no quedaron expuestos. Como cada sesión consume
crédito, se limitó su presupuesto a 1 USD y la máquina se apaga cuando no se usa.

La verificación se hizo desde fuera de la máquina: sin contraseña, la web respondió 401; los puertos de la base de datos, de la
aplicación y de los embeddings no respondieron, y un módulo real quedó validado en la primera versión en 3,15 minutos, por
0,198 USD. Tras un reinicio, el enlace volvió en 32 segundos y conservó la sesión. La decisión quedó en el ADR-0020.

---

## 5.1 Diseño de la evaluación

**Agregar al final de la sección:**

La tasa de errores medida con el tester del propio sistema no permite comparar enfoques, porque cada uno tendría sus propias
pruebas y el tester juzga contra los requerimientos que el mismo sistema elicitó. Por eso se agregó una segunda vara:
**pruebas de aceptación de referencia**, escritas desde la ficha de cada caso sintético y comunes a todos los enfoques. Cada
prueba verifica solo lo que la ficha dice sin ambigüedad: ejemplos con cifras, reglas, rangos y mensajes textuales. El oráculo
se validó antes de medir: en cada caso, una implementación de control pasó todas las verificaciones y cada uno de los 35
mutantes, variantes con un defecto a propósito, falló al menos una. `[CONFIRMAR: un autor revisó las verificaciones frente a
cada ficha.]`

No se hizo una comparación con desarrollo humano. Realtix no pudo compartir sus desarrollos por el acuerdo de
confidencialidad, y una implementación hecha por los autores no habría sido independiente, porque construyeron el sistema y
conocían los casos. Tampoco sirvió el código abierto de repositorios públicos, que no implementa estas fichas ni registra
tiempos ni costos. La evaluación respondió entonces a otra pregunta, la misma que plantea el estado del arte: qué aporta la
arquitectura multiagente frente a un solo modelo de lenguaje.

Se compararon tres enfoques, todos con el mismo modelo para escribir el código, de modo que la diferencia saliera de la
arquitectura:

- **Sistema multiagente:** los cuatro agentes y el orquestador, con un cliente simulado y un analista simulado.
- **Modelo con diálogo:** un solo modelo que conversó con el mismo cliente simulado y entregó todo en una respuesta, con la
  misma información que el sistema.
- **Modelo de un solo prompt:** un solo modelo que recibió en un mensaje lo que sabe el cliente, sin diálogo. Es el mejor caso
  para un modelo solo, porque supone que alguien ya hizo la elicitación.

Se usaron nueve casos sintéticos, sin datos de Realtix, que cubren las seis arquitecturas del catálogo. Tres se eligieron antes
de medir; los otros seis fueron el primer caso de cada arquitectura, por número, sin mirar su resultado. Las pruebas de esos seis
se versionaron antes de abrir sus implementaciones y de correr las líneas base; de dos de ellos ya se conocían hallazgos del tester, no
su código.

**Niveles que se agregan a la Tabla 24:**

| Nivel | Qué verifica | Casos y corridas | Criterio |
|---|---|---|---|
| Corrida ampliada | Flujo completo sobre todas las arquitecturas | 20 casos sintéticos, 1 corrida | Criterios fijados en el ADR-0015 |
| Comparación con líneas base | Errores, tiempo y costo con un mismo oráculo | 9 casos; 36 implementaciones de los 3 enfoques | Descriptivo, sin criterio de aprobación |
| Tester frente al oráculo | Coincidencia del veredicto con las pruebas de referencia | 21 versiones de módulos reales | Descriptivo |
| Métricas RAGs | Fidelidad y relevancias | 20 sesiones, 60 muestras | Descriptivo |
| Despliegue en Azure | Flujo completo en la nube | 1 módulo real | Módulo validado en la revisión final |

---

## 5.2 Resultados de las corridas de extremo a extremo

**Reemplazar la Tabla 25 y su texto por:**

La corrida ampliada recorrió 20 casos sintéticos con el flujo completo. Dieciséis módulos quedaron validados, 11 de ellos en la
primera versión, y 4 sesiones escalaron a la revisión final. El tiempo del sistema fue de 6,6 minutos de media, con un máximo de
10,3, frente a los 20 del RNF-01. El costo fue de 0,403 dólares de media por módulo, de 0,181 a 0,690, y de 0,391 por módulo
validado. La arquitectura elegida coincidió con la esperada en los 20 casos.

La generación de código concentró el 44,8 % del costo, la selección y parametrización de la arquitectura el 27,1 %, el diálogo el
18,2 %, la síntesis el 9,3 % y el veredicto el 0,7 %.

**[Tabla A]. Criterios de calidad de la primera salida en la corrida ampliada**

| Criterio | Meta | Corrida previa | Corrida ampliada | ¿Cumple? |
|---|---|---|---|---|
| Validados en la primera versión | al menos 15 de 19 | 18 de 20 | 11 de 20 | no |
| Primeros intentos del desarrollador rechazados | como máximo 2 de 29 | 7 de 23 | 4 de 35 | no |
| Sesiones escaladas | 0 | 0 | 4 | no |
| Costo medio por módulo validado | como máximo 0,35 USD | 0,342 USD | 0,391 USD | no |
| Hallazgos de pruebas que simulan el efecto | 0 | 0 | 0 | sí |
| Turnos sin exploración | como máximo 211 | 210 | 205 | sí |
| Resúmenes confirmados | al menos 17 de 20 | 16 | 19 | sí |

Fuente: Elaboración propia.

El retroceso frente a la corrida previa no se debió a un cambio en los modelos ni en los prompts, que fueron los mismos. La causa
principal fueron escenarios de aceptación defectuosos del elicitador en cuatro casos, que contradecían las reglas, inventaban datos o
incluían una pregunta abierta; se estima que, sin ellos, 15 de 20 módulos habrían quedado validados en la primera versión. Se sumó que el juez del tester cambió de veredicto
en 3 de 124 rejuicios de una prueba idéntica. Una corrida adicional de tres casos terminó sin escalamientos, lo que muestra la
variabilidad de estas mediciones.

---

## 5.3 Comparación con un solo modelo de lenguaje (sección nueva)

**[Tabla B]. Comparación de los enfoques con las pruebas de aceptación de referencia**

| Métrica | Sistema multiagente | Modelo con diálogo | Modelo de un solo prompt |
|---|---|---|---|
| Implementaciones evaluadas | 12 | 15 | 9 |
| Verificaciones aprobadas | 115 de 119 | 140 de 148 | 90 de 90 |
| Tasa de errores | 3,4 % | 5,4 % | 0,0 % |
| Implementaciones sin errores | 9 de 12 | 13 de 15 | 9 de 9 |
| Costo medio por módulo | 0,358 USD | 0,170 USD | 0,104 USD |
| Tiempo medio de máquina | 5,9 min | 2,9 min | 2,5 min |
| Implementaciones con pruebas propias que fallan | 1 de 12 | 3 de 15 | 2 de 9 |
| Hallazgos de estilo por implementación | 0,3 | 1,2 | 1,0 |

Fuente: Elaboración propia.

**[Tabla C]. Tasa de errores por caso**

| Caso | Arquitectura | Sistema multiagente | Modelo con diálogo | Modelo de un solo prompt |
|---|---|---|---|---|
| Comisiones de corretaje | ARQ-01 | 0,0 % | 0,0 % | 0,0 % |
| Reajuste del canon | ARQ-01 | 5,6 % | 0,0 % | 0,0 % |
| Contratos de arrendamiento | ARQ-02 | 7,7 % | 0,0 % | 0,0 % |
| Conciliación del recaudo | ARQ-03 | 0,0 % | 0,0 % | 0,0 % |
| Tarifa del impuesto predial | ARQ-04 | 0,0 % | 0,0 % | 0,0 % |
| Dígito de verificación del NIT | ARQ-04 | 0,0 % | 0,0 % | 0,0 % |
| Escaneos de expedientes | ARQ-05 | 0,0 % | 9,1 % | 0,0 % |
| Simulador de amortización | ARQ-05 | 10,0 % | 23,3 % | 0,0 % |
| Trámites catastrales | ARQ-06 | 0,0 % | 0,0 % | 0,0 % |

Fuente: Elaboración propia.

La hipótesis de que el sistema tendría menos errores que un modelo solo no se sostuvo. La diferencia frente al modelo con diálogo
fue pequeña y dependió de una sola corrida, en la que el modelo dejó el cálculo pendiente porque el cliente no definió el redondeo;
sin ella, su tasa bajó a 0,7 %. Caso a caso, el sistema fue mejor en 2, peor en 2 e igual en 5. En cambio, costó y tardó más en los nueve
casos frente a cada línea base (prueba de signos, exploratoria, p = 0,004): cerca del doble que el modelo con diálogo, y 3,4 veces el costo y
2,4 veces el tiempo del modelo de un solo prompt.

El análisis de los errores fue más revelador que su cantidad. El modelo de un solo prompt no falló ninguna verificación, lo que
indica que, en módulos de este tamaño y con la información completa, escribir el código no fue el cuello de botella. Los errores
de las versiones finales del sistema se originaron antes de la generación: la síntesis parafraseó un mensaje textual del cliente y
cambió «queda registrado» por «se devuelve», y el diseño convirtió una tasa porcentual en una fracción con dos decimales y omitió la
herramienta de terminal. Cada paso añadido a la cadena fue también un lugar donde se pudo perder información. El único error de
código claro, una fórmula mal escrita en una primera versión, lo detuvo el tester antes de la entrega.

Lo que el sistema agregó no fue corrección del código, sino lo que la rodea, como resume la [Tabla D].

**[Tabla D]. Entregables de cada enfoque**

| Entregable | Sistema multiagente | Un solo modelo |
|---|---|---|
| Código, pruebas y documentación de uso | Sí | Sí |
| Historias de usuario y requerimientos formales | Sí | No |
| Registro de decisión y especificación de diseño | Sí | No |
| Plan de pruebas de aceptación y reporte de validación | Sí | No |
| Validación independiente con veredicto | Sí | No |
| Ejecución en un entorno aislado antes de entregar | Sí | No |
| Puntos de control humano | Tres | Ninguno |
| Traza de costo por nodo y presupuesto por módulo | Sí | No |

Fuente: Elaboración propia.

Un modelo solo entregó en cinco de 24 implementaciones pruebas propias que fallaban, sin advertirlo. Las cinco pasaron todas las
verificaciones de referencia: el código estaba bien y lo que fallaba era, en su mayoría, el valor que esperaba la prueba escrita por
el modelo, que no ejecuta lo que entrega. Aun así, quien recibe el módulo ve pruebas en rojo sin aviso y debe averiguar si falla el
código o la prueba. Tampoco hubo nada que le impidiera entregar, en una corrida, un módulo que dejaba el cálculo pendiente. En el sistema, la
única implementación con pruebas que fallaban fue la del escenario imposible del reajuste del canon: el tester rechazó sus tres
versiones y la sesión escaló a la revisión final con su reporte, sin poder aprobarse. Esa diferencia de gobierno, y no la de errores, es lo que
puede justificar el mayor costo, que sigue siendo de centavos de dólar por módulo.

---

## 5.4 Desempeño del agente tester (antes 5.3)

**Reemplazar la Tabla 26 y su texto por:**

Con el conjunto de defectos inyectados, ampliado a 21 defectos y 3 controles y con el agente vigente, el tester detectó los 63 defectos
de las tres corridas y aprobó los 9 controles.

**Tabla 26. Métricas del agente tester sobre los defectos inyectados**

| Indicador | Valor en las tres corridas |
|---|---|
| Defectos detectados, verdaderos positivos | 63 |
| Defectos no detectados, falsos negativos | 0 |
| Controles aprobados, verdaderos negativos | 9 |
| Rechazos de código correcto, falsos positivos | 0 |
| Precisión, sensibilidad, F1 y exactitud | 1,00 |

Fuente: Elaboración propia con base en [55].

Estos valores corresponden a defectos conocidos de antemano. Para medirlo en módulos reales, cada una de las 21 versiones que dictaminó en
los casos de referencia se contrastó también con las pruebas de referencia, tomando como positivo que estas fallaran.

**[Tabla E]. Matriz de confusión del tester frente a las pruebas de referencia**

| | Con error de referencia | Sin error de referencia |
|---|---|---|
| El tester rechaza | 4 | 8 |
| El tester aprueba | 2 | 7 |

Fuente: Elaboración propia con base en [55].

La exactitud fue de 0,52, la precisión de 0,33, la sensibilidad de 0,67 y el F1 de 0,44. Estas cifras deben leerse con cuidado, porque los
dos instrumentos no miden lo mismo: el tester juzgó el módulo y sus pruebas frente a los requerimientos que elicitó el sistema, mientras que
las pruebas de referencia juzgaron solo el comportamiento frente a la ficha.

De los ocho rechazos sin error de referencia, dos fueron justificados, porque las pruebas del módulo fallaban en la capa HTTP, que el
oráculo no cubre; tres se debieron a un escenario imposible escrito por el elicitador, y tres, a pruebas débiles y a un escenario que no se
podía observar. Los dos aprobados con error partían de un requerimiento que ya había perdido la regla, y el tester no ve lo que se perdió al
elicitar. Si los dos rechazos justificados se cuentan como aciertos, la exactitud sube a 0,62, la precisión a 0,50, la sensibilidad a 0,75 y
el F1 a 0,60.

La principal lección es que el 1,00 con defectos inyectados no se trasladó a módulos reales: el tester es tan bueno como los requerimientos
contra los que juzga.

---

## 5.5 Métricas de la generación aumentada por recuperación (antes 5.4)

**Reemplazar la sección por:**

Las tres dimensiones de RAGs [66] de la Tabla 14 se midieron sobre las 20 sesiones de la corrida ampliada, con una muestra por sesión y por
agente y, como juez, un modelo de lenguaje que esos agentes no usan.

**[Tabla F]. Métricas RAGs por colección**

| Colección | Agente | Fidelidad | Relevancia de la respuesta | Relevancia del contexto |
|---|---|---|---|---|
| Elicitación | Elicitador | 0,81 | 0,56 | 0,57 |
| Dominio de negocio | Elicitador | 0,81 | 0,56 | 0,10 |
| Arquitecturas de referencia | Arquitecto | 0,84 | 0,51 | 0,67 |
| Criterios de calidad | Tester | 0,47 | 0,37 | 0,42 |

Fuente: Elaboración propia con base en [66].

La fidelidad del elicitador y del arquitecto fue alta. La del tester está subestimada: sus afirmaciones más frecuentes provienen de la
ejecución de las pruebas, que no se le entregó al juez; al apartarlas con un filtro de texto aproximado, subió a cerca de 0,68. La
relevancia del contexto del dominio de negocio fue la más baja, porque el corpus es catastral y tributario y varios casos no lo son, y
porque el elicitador solo puede tomar terminología de esa colección. Es la base de conocimiento que más ajustes requiere.
`[CONFIRMAR: un autor revisó una muestra de cinco juicios del modelo.]`

---

## 5.6 Cumplimiento de los requerimientos no funcionales (antes 5.5)

**Filas que cambian en la Tabla 27:**

| Requerimiento | Evidencia | Estado |
|---|---|---|
| RNF-01 Eficiencia de desempeño | Módulos en un máximo de 10,3 min frente a 20. Turnos de hasta 12,4 s, salvo uno de 16,2 s, en una de 20 sesiones, frente a 15 s | Cumplido parcialmente |
| RNF-02 Fiabilidad | Estado persistido y reanudable; en Azure, el sistema volvió tras un reinicio en 32 s con sus datos | Cumplido |
| RNF-07 Compatibilidad | Windows con WSL2 y Ubuntu 24.04 en Azure; macOS sin verificar | Cumplido parcialmente |
| RNF-10 Adecuación funcional | Presupuesto configurable que detiene la ejecución, con 0,391 USD de media por módulo validado | Cumplido |

---

## 6.4 Resultados de la evaluación del desempeño

**Reemplazar la sección por:**

El cuarto objetivo aplicó el plan de pruebas del capítulo 5. Los módulos se produjeron en un máximo de 10,3 minutos frente al límite de 20,
y el costo medio fue de 0,403 dólares por módulo. Un turno de diálogo superó los 15 segundos del RNF-01, con 16,2 segundos, en una de 20
sesiones. La arquitectura elegida coincidió con la esperada en los 20 casos. Las decisiones que se tomaron para mejorar la elicitación
cumplieron su objetivo, con 19 resúmenes confirmados frente a 16, pero la validación en la primera versión bajó de 18 a 11 de 20.

La comparación con un solo modelo de lenguaje fue el resultado más importante, y no favoreció al sistema en lo que se esperaba. Con las
mismas pruebas, la tasa de errores fue de 3,4 % en el sistema, de 5,4 % en el modelo con diálogo y de 0,0 % en el modelo de un solo prompt,
y el sistema costó y tardó cerca del doble que el modelo con diálogo, y más aún frente al de un solo prompt. Se valora como un hallazgo y no como un fracaso, porque precisó dónde está el valor de la
arquitectura: en módulos de este tamaño, un modelo capaz escribe bien el código si tiene la información; lo difícil es conseguirla,
conservarla y demostrar que el resultado cumple. Ahí aportó el sistema, con requerimientos trazables, diseño de un catálogo cerrado,
validación independiente y control humano, y ahí mismo mostró sus debilidades: la información se perdió en la síntesis y en el diseño, y el
tester, que con defectos inyectados alcanzó 1,00, bajó a una exactitud de 0,52 frente al oráculo.

La evaluación tiene limitaciones. Los casos son sintéticos y los módulos pequeños, de modo que con módulos mayores el resultado podría ser
otro. Seis de los nueve casos tienen una sola corrida por enfoque, y la variabilidad es alta: un mismo caso escaló en una corrida y se validó
en la primera versión en otra. El modelo de comparación es muy capaz. El oráculo lo escribió el propio equipo, y el analista simulado no
permite medir el valor de los puntos de control humano. Finalmente, no se comparó el sistema con desarrollo humano, por lo que el ahorro frente
al trabajo manual no quedó cuantificado.

---

## 6.5 Impactos del proyecto

**Reemplazar la primera frase del ámbito económico por:**

En el ámbito económico, un módulo costó en promedio 0,40 dólares de inferencia y entre 3,3 y 10,3 minutos de tiempo del sistema, de modo que
cien módulos costarían cerca de 40 dólares de inferencia; es cerca del doble de lo que costaría un solo modelo con diálogo, y a cambio se
obtienen los artefactos y los controles de la [Tabla D]. El ahorro frente al desarrollo manual, en cambio, queda por medir.

---

## 7. Conclusiones

**Reemplazar el párrafo de la evaluación por:**

La evaluación confirmó que el sistema opera dentro de sus umbrales de tiempo y de costo, con la excepción de un turno de diálogo, pero
no que produzca menos errores que un solo modelo de lenguaje: en módulos pequeños y con un modelo capaz, ambos enfoques escribieron código
correcto cuando tuvieron la información, y el sistema costó el doble o más. El valor de la arquitectura multiagente no estuvo en la corrección del
código, sino en lo que la rodea: convertir una conversación en requerimientos trazables, elegir el diseño de un catálogo cerrado, validar de
forma independiente y dejar la decisión final en manos de una persona. También quedó claro su principal riesgo: cada paso de la cadena puede
perder información, y un validador solo es tan bueno como los requerimientos contra los que juzga.

---

## 8. Recomendaciones

**Reemplazar la lista por:**

- Verificar la coherencia de los escenarios de aceptación frente a las reglas antes de aprobarlos, y conservar los mensajes textuales del
  cliente, porque ahí se originó la mayor parte de los errores.
- Darle al desarrollador una vía para reportar un escenario imposible, y que el orquestador lo escale de inmediato en vez de agotar el
  ciclo de corrección.
- Conservar el veredicto de las pruebas que no cambian entre versiones, para estabilizar al juez del tester, y detectar en el código valores
  fijados de un escenario.
- Evaluar el sistema con módulos de mayor tamaño, donde la descomposición por agentes podría aportar más, y repetir cada caso más veces.
- Comparar el sistema con el desarrollo humano en casos reales de Realtix, para cuantificar el ahorro de tiempo y de costo, y comparar de forma
  sistemática los modelos asignados a cada nodo.
- Filtrar la colección de dominio de negocio cuando la necesidad no pertenezca al dominio.
- Completar el acceso remoto a la interfaz web con un enlace por sesión para el cliente, y verificar el despliegue en macOS.
- Alinear el sistema con la ISO/IEC 27090:2026 [85], en particular frente a la inyección de prompts en las respuestas del cliente y la exposición
  de los datos de las bases de conocimiento.

---

## Anexo D: entradas nuevas, en el formato de la tabla de registros

**ADR-0018. Rediseño de la interfaz web.** Contexto: las pantallas no mostraban el avance de una sesión por etapas. Decisión: organizar cada sesión
en cinco etapas con la línea del flujo y los tres puntos de control, y agrupar el panel según quién debe actuar. Consecuencia: se usa sin
recursos externos, con fuentes servidas por la aplicación.

**ADR-0019. Casos de referencia y líneas base.** Contexto: la tasa de errores con el tester propio no permitía comparar enfoques. Decisión: un oráculo
común de pruebas de aceptación, en nueve casos, frente a dos líneas base de un solo modelo de lenguaje; se retiró la implementación manual, por no
ser independiente. Consecuencia: el sistema no tuvo menos errores y costó el doble o más, y se precisó dónde está su valor.

**ADR-0020. Despliegue de demostración en Azure.** Contexto: se necesitaba un enlace público. Decisión: una máquina virtual con la misma composición y
un proxy con TLS y contraseña, solo con datos sintéticos. Consecuencia: el enlace funciona sin cambiar el sistema, con una sola contraseña y sin tope
global de gasto.
