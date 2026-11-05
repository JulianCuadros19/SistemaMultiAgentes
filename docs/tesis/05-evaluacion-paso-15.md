# Texto de la evaluación para el documento de tesis

Texto listo para llevar al documento, redactado como él: voz impersonal, tiempo pasado, coma decimal y cifras con su
unidad. La fuente es `docs/evaluacion/informe-objetivo-4.md`.

**Cuando este archivo y `01-correcciones.md` o `02-avances.md` traten lo mismo, manda este archivo.** El Resumen y el Abstract
están en `01-correcciones.md`, C-01 a C-03.

**Antes de entregar:**
- **`[Tabla A]`, `[Tabla B]`…:** son tablas nuevas. Se numeran al insertarlas en el documento.
- **La sección 5.3 es nueva.** Las actuales 5.3 a 5.6 pasan a ser 5.4 a 5.7.

---

## 1.6.4 Fase 4: actividades y entregables

**Agregar a las actividades de 1.6.4.1:**

- Comparar el sistema con dos líneas base de un solo modelo de lenguaje, mediante pruebas de aceptación de referencia
  comunes a todos los enfoques.

**Reemplazar en los entregables de 1.6.4.2:**

- Informe de evaluación con métricas y conclusiones.
- Producto del sistema multiagente de IA empaquetado en contenedores, ejecutable en la infraestructura de Realtix con los
  modelos de lenguaje de Azure OpenAI, y un despliegue de demostración en Azure con datos sintéticos.
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

## Capítulo 4: sección nueva, después de «Empaquetado en contenedores con Azure OpenAI»

### Despliegue de demostración en Azure

Para compartir el sistema mediante un enlace público se desplegó la misma composición de contenedores en una máquina virtual
de Azure, con 4 vCPU, 16 GiB de memoria y Ubuntu 24.04, pagada con créditos de estudiante. Se descartaron los servicios
administrados de contenedores, porque no ofrecen el Docker del anfitrión con que la aplicación crea el entorno aislado.

Un proxy, definido en un archivo aparte de la composición de la entrega, publica la interfaz web con TLS y contraseña. La base
de datos, el servicio de representaciones vectoriales y el socket de Docker no quedaron expuestos. Como cada sesión consume
crédito, se limitó su presupuesto a 1 USD y la máquina se apaga cuando no se usa.

La verificación se hizo desde fuera de la máquina: sin contraseña, la web respondió 401; los puertos de la base de datos, de la
aplicación y de los embeddings no respondieron, y un módulo real quedó validado en la primera versión en 3,15 minutos, por
0,198 USD. Tras un reinicio, el enlace volvió en 32 segundos y conservó la sesión, y también volvió al detener e iniciar la máquina desde el portal. La decisión quedó
en el ADR-0020.

---

## Capítulo 5: párrafo inicial

**Reemplazar por:**

Este capítulo presenta la evaluación del desempeño del sistema multiagente. Se describen el diseño de la evaluación con su plan
de pruebas, los resultados de las corridas de extremo a extremo, la comparación con un solo modelo de lenguaje, el desempeño del
agente tester, las métricas de la generación aumentada por recuperación, el cumplimiento de los requerimientos no funcionales y
los hallazgos que orientaron los ajustes iterativos.

---

## 5.1 Diseño de la evaluación

**En el primer párrafo:** «con seis niveles» pasa a «con once niveles». Lo demás de la Tabla 24 está en `01-correcciones.md`, C-28.

**Agregar al final de la sección:**

La tasa de errores medida con el tester del propio sistema no permitía comparar enfoques, porque cada uno tendría sus propias
pruebas y el tester juzga contra los requerimientos que el mismo sistema elicitó. Por eso se agregó un segundo instrumento:
**pruebas de aceptación de referencia**, en adelante el oráculo, escritas desde la ficha de cada caso sintético, que describe lo
que sabe el cliente simulado, y comunes a todos los enfoques. Cada prueba verificó solo lo que la ficha dice sin ambigüedad: ejemplos con cifras, reglas, rangos y mensajes textuales. El oráculo
se validó antes de medir: en cada caso, una implementación de control pasó todas las verificaciones y cada uno de los 35
mutantes, variantes con un defecto a propósito, falló al menos una. Un autor revisó las verificaciones frente a
cada ficha.

La comparación se realizó con código generado por un solo modelo de lenguaje. Se decidió así porque Realtix no pudo compartir su
código, por el acuerdo de confidencialidad, y porque el código abierto de repositorios públicos no implementa estas fichas ni
registra tiempos ni costos. El código generado es, además, una referencia repetible, medible e independiente de los autores, que
construyeron el sistema y conocían los casos. Así, la evaluación respondió a la misma pregunta que plantea el estado del arte: qué
aporta la arquitectura multiagente frente a un solo modelo de lenguaje.

Se compararon tres enfoques, todos con el mismo modelo para escribir el código, de modo que la diferencia saliera de la
arquitectura:

- **Sistema multiagente:** los cuatro agentes y el orquestador, con un cliente simulado y un analista simulado.
- **Modelo con diálogo:** un solo modelo que conversó con el mismo cliente simulado y entregó todo en una respuesta, con la
  misma información que el sistema.
- **Modelo de un solo prompt:** un solo modelo que recibió en un mensaje lo que sabe el cliente, sin diálogo. Es el mejor caso
  para un modelo solo, porque supone que alguien ya hizo la elicitación.

Antes de medir se planteó como hipótesis que el sistema tendría menos errores que un solo modelo de lenguaje.

Se usaron nueve casos sintéticos, sin datos de Realtix, que cubren las seis arquitecturas del catálogo. Tres se eligieron antes
de medir; los otros seis fueron el primer caso de cada arquitectura, por número, sin mirar su resultado. Las pruebas de esos seis
se versionaron antes de abrir sus implementaciones y de correr las líneas base; de dos de ellos ya se conocían hallazgos del tester, no
su código.

**Niveles que se agregan a la Tabla 24.** Con ellos y con los de C-28, queda en once:

| Nivel | Qué verifica | Casos y corridas | Criterio |
|---|---|---|---|
| Comparación con líneas base | Errores, tiempo, costo y calidad del código, con un mismo oráculo y las mismas reglas | 9 casos; 36 implementaciones de los 3 enfoques | Descriptivo, sin criterio de aprobación |
| Tester frente al oráculo | Coincidencia del veredicto con las pruebas de referencia | 21 versiones de módulos reales | Descriptivo |
| Métricas RAGs | Fidelidad y relevancias | 20 sesiones, 60 muestras | Descriptivo |
| Despliegue en Azure | Flujo completo en la nube | 1 módulo real | Módulo validado en la revisión final |

---

## 5.2 Resultados de las corridas de extremo a extremo

**Conservar lo que dice de la integración, la Tabla 25 y el párrafo que la sigue.** En ese texto y en el título de la tabla,
«corrida final» pasa a «verificación posterior a los ajustes de robustez», porque ya no fue la última corrida.

**Agregar al final de la sección:**

La corrida ampliada recorrió 20 casos sintéticos con el flujo completo, de tres a cuatro por arquitectura, en tres momentos. En la
línea base, 10 de 19 módulos quedaron validados en la primera versión. Tras los ajustes de la primera salida descritos en el
capítulo 4, los 20 módulos quedaron validados, 18 de ellos en la primera versión. En la última corrida, con el sistema final, 16
módulos quedaron validados, 11 de ellos en la primera versión, y 4 sesiones escalaron a la revisión final. El tiempo del sistema fue de 6,6 minutos de media, con un máximo de
10,3, frente a los 20 del RNF-01. El costo fue de 0,403 dólares de media por módulo, de 0,181 a 0,690, y de 0,391 por módulo
validado. La arquitectura elegida coincidió con la esperada en los 20 casos.

La generación de código concentró el 44,8 % del costo, la selección y parametrización de la arquitectura el 27,1 %, el diálogo el
18,2 %, la síntesis el 9,3 % y el veredicto el 0,7 %.

**[Tabla A]. Criterios de calidad de la primera salida en la corrida ampliada**

| Criterio | Meta | Corrida anterior | Última corrida | ¿Cumple? |
|---|---|---|---|---|
| Validados en la primera versión | al menos 15 de 19 | 18 de 20 | 11 de 20 | no |
| Primeros intentos del desarrollador rechazados | como máximo 2 de 29 | 7 de 23 | 4 de 35 | no |
| Sesiones escaladas | 0 | 0 | 4 | no |
| Costo medio por módulo validado | como máximo 0,35 USD | 0,342 USD | 0,391 USD | no |
| Hallazgos de pruebas que simulan el efecto | 0 | 0 | 0 | sí |
| Turnos sin exploración | como máximo 211 | 210 | 205 | sí |
| Resúmenes confirmados | al menos 17 de 20 | 16 | 19 | sí |

Fuente: Elaboración propia.

El retroceso frente a la corrida anterior no se debió a un cambio en los modelos ni en los prompts, que fueron los mismos. La causa
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

Para medir con cifras lo que el sistema agrega, se reunieron las mediciones de la [Tabla H]. Las de calidad del código salen de las reglas
basadas en la ISO/IEC 25010 de su base de conocimiento: se fijaron antes de calcularlas y se reportan todas, también las que no favorecen al
sistema. Son exploratorias y usan detectores aproximados.

**[Tabla H]. Mediciones del aporte del sistema**

| Medición | Sistema multiagente | Modelo con diálogo | Modelo de un solo prompt |
|---|---|---|---|
| Implementaciones con hallazgos de estilo | 3 de 12 | 10 de 15 | 4 de 9 |
| Hallazgos de estilo de severidad media | 0 | 2 | 1 |
| Pruebas propias en rojo en una entrega que queda como lista | 0 de 12 | 3 de 15 | 2 de 9 |
| Peor implementación frente al oráculo | 80 % | 30 % | 100 % |
| Requerimientos formales por sesión | 2,25 | 0 | 0 |
| Casos de aceptación con veredicto propio, por sesión | 8,25 | 0 | 0 |
| Complejidad ciclomática media por función | 2,00 | 2,78 | 2,49 |
| Complejidad ciclomática máxima, por implementación | 5,75 | 6,00 | 5,67 |
| Proporción de pruebas que esperan un rechazo | 45 % | 31 % | 36 % |
| Pruebas que esperan un rechazo, por implementación | 8,9 | 6,9 | 10,4 |
| Usos no deterministas en las pruebas, por implementación | 0,25 | 0,07 | 0,22 |
| Nombres privados importados de otro módulo, por implementación | 0 | 0,07 | 0 |
| Usos de punto flotante en dinero, credenciales en el código, sentencias `global` y recursos fuera de `with` | 0 | 0 | 0 |
| Funciones de prueba por implementación | 19,8 | 23,1 | 27,6 |
| Líneas de código por implementación | 298 | 180 | 208 |
| Módulos por implementación | 4,5 | 1,7 | 1,8 |

Fuente: Elaboración propia.

Frente al modelo con diálogo, el único que parte de la misma información, el sistema tuvo menos implementaciones con hallazgos de estilo, ninguna
entrega lista con pruebas en rojo y una peor implementación mucho menos grave, y el ciclo de corrección bajó su tasa de errores de 9,2 % en la
primera versión a 3,4 % en la final, aunque esa mejora provino de un solo caso. La complejidad media por función fue menor en 8 de 9 casos frente al
modelo con diálogo y en los 9 frente al de un solo prompt, y la proporción de pruebas que esperan un rechazo fue mayor en 7 y en 6 casos,
respectivamente. El tester no revisa esta última regla, de modo que el sistema no tenía ahí una ventaja de entrada. El sobrecosto frente al modelo
con diálogo fue de 0,19 dólares y 3 minutos por módulo.

Los demás resultados matizan esa lectura. La complejidad máxima no cambió, lo que indica que la media bajó sobre todo por tener más funciones
pequeñas. El sistema escribió más código y menos pruebas, y tuvo algo más de usos no deterministas en sus pruebas que el modelo con diálogo. En usos de
punto flotante en dinero, credenciales, sentencias `global` y recursos fuera de `with` no hubo diferencia: ningún enfoque los presentó, de modo que un
modelo capaz ya cumple esas reglas sin el sistema.

---

## 5.4 Desempeño del agente tester (antes 5.3)

**Reemplazar la Tabla 26 y su texto por:**

Con el conjunto de defectos inyectados, ampliado a 21 defectos y 3 controles y con el agente vigente, el tester detectó los 63 defectos
de las tres corridas y aprobó los 9 controles. Tomando como caso positivo la detección de un defecto, la matriz de confusión arrojó los
valores de la Tabla 26.

**Tabla 26. Métricas del agente tester sobre los defectos inyectados**

| Indicador | Valor en las tres corridas |
|---|---|
| Defectos inyectados | 63, 21 por corrida |
| Defectos detectados, verdaderos positivos | 63 |
| Defectos no detectados, falsos negativos | 0 |
| Controles aprobados, verdaderos negativos | 9 |
| Rechazos de código correcto, falsos positivos | 0 |
| Precisión | 1,00 |
| Sensibilidad o recall | 1,00 |
| F1-score | 1,00 |
| Exactitud | 1,00 |

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

**Conservar los dos párrafos actuales,** con el segundo en pasado: «se miden» pasa a «se midieron». **Agregar:**

Se midieron sobre las 20 sesiones de la última corrida ampliada, con una muestra por sesión y por agente y, como juez, un modelo de lenguaje
que esos agentes no usan.

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
Un autor revisó una muestra de cinco juicios del modelo y los validó.

---

## 5.6 Cumplimiento de los requerimientos no funcionales (antes 5.5)

**Filas que cambian en la Tabla 27:**

| Requerimiento | Evidencia | Estado |
|---|---|---|
| RNF-01 Eficiencia de desempeño | Módulos en un máximo de 10,3 min frente a 20. Turnos de hasta 12,4 s, salvo uno de 16,2 s, en una de 20 sesiones, frente a 15 s | Cumplido parcialmente |
| RNF-02 Fiabilidad | Estado persistido en PostgreSQL después de cada paso, con reanudación tras una caída y retoma de sesiones en otro proceso; en Azure, el sistema volvió tras un reinicio en 32 s con sus datos | Cumplido |
| RNF-07 Compatibilidad | Contenedores con Docker Desktop sobre Windows y WSL2, verificados desde un clon limpio, y en Ubuntu 24.04 en Azure; macOS no se verificó | Cumplido parcialmente |
| RNF-10 Adecuación funcional | Costo registrado por nodo y por sesión en PostgreSQL; presupuesto por módulo, de 1,50 USD por defecto, que pausa la sesión hasta que una persona lo amplía o la cierra, con 0,391 USD de media por módulo validado | Cumplido |

**Las demás filas están en `01-correcciones.md`, C-30. El texto que sigue a la tabla debe decir:**

De los diez requerimientos no funcionales, siete se cumplieron y tres de forma parcial: el RNF-01, porque un turno de diálogo llegó a 16,2
segundos frente a 15; el RNF-04, porque los fragmentos recuperados viajan en los prompts que procesa Azure OpenAI, y el RNF-07, porque el
despliegue no se verificó en macOS. El RF-37 se cumplió con su enunciado vigente: el sistema se entrega en contenedores y completa el flujo de
extremo a extremo con los modelos de Azure OpenAI y las representaciones vectoriales locales.

---

## 5.7 Hallazgos y ajustes iterativos (antes 5.6)

**Además de lo que indica C-31, agregar al final:**

La última corrida dejó tres hallazgos más. El principal es que nada revisa los escenarios de aceptación del elicitador antes de generar el
código: en cuatro casos, un escenario defectuoso impidió validar el módulo en la primera versión, y en dos de ellos el defecto llegó al código,
con una fecha fija en producción en uno y un mensaje provisional en otro, y esos módulos quedaron validados. La revisión humana final debería
detectarlos, pero en esta corrida la hizo un analista simulado que aprueba sin leer. El segundo es la variabilidad del juez del tester, que
cambió de veredicto en 3 de 124 rejuicios de una prueba idéntica. El tercero es que un escenario imposible consume todo el ciclo de corrección
antes de escalar, porque el desarrollador no tiene cómo reportarlo. Estas correcciones no se aplicaron durante la medición, para no alterar lo
medido, y quedaron como recomendaciones.

---

## 6.4 Resultados de la evaluación del desempeño

**Reemplazar la sección por:**

El cuarto objetivo aplicó el plan de pruebas del capítulo 5. Los módulos se produjeron en un máximo de 10,3 minutos frente al límite de 20,
y el costo medio fue de 0,403 dólares por módulo. Un turno de diálogo superó los 15 segundos del RNF-01, con 16,2 segundos, en una de 20
sesiones. La arquitectura elegida coincidió con la esperada en los 20 casos. Las decisiones que se tomaron para mejorar la elicitación
cumplieron su objetivo, con 19 resúmenes confirmados frente a 16, pero la validación en la primera versión bajó de 18 a 11 de 20. De los diez requerimientos no funcionales, siete se cumplieron y tres de
forma parcial.

La comparación con un solo modelo de lenguaje fue el resultado más importante, y no favoreció al sistema en lo que se esperaba. Con las
mismas pruebas, la tasa de errores fue de 3,4 % en el sistema, de 5,4 % en el modelo con diálogo y de 0,0 % en el modelo de un solo prompt,
y el sistema costó y tardó cerca del doble que el modelo con diálogo, y más aún frente al de un solo prompt. Se valora como un hallazgo y no como un fracaso, porque precisó dónde está el valor de la
arquitectura: en módulos de este tamaño, un modelo capaz escribe bien el código si tiene la información; lo difícil es conseguirla,
conservarla y demostrar que el resultado cumple. Ahí aportó el sistema, con requerimientos trazables, diseño de un catálogo cerrado,
validación independiente y control humano. Frente al modelo con diálogo, además, tuvo menos implementaciones con hallazgos de estilo, 3 de 12 frente a
10 de 15, ninguna entrega lista con pruebas en rojo, frente a 3 de 15, y menor complejidad media por función, 2,00 frente a 2,78, a cambio de 0,19
dólares y 3 minutos más por módulo. También mostró sus debilidades: la información se perdió en la síntesis y en el diseño, y el
tester, que con defectos inyectados alcanzó 1,00, bajó a una exactitud de 0,52 frente al oráculo.

La evaluación tiene limitaciones. Los casos son sintéticos y los módulos pequeños, de modo que con módulos mayores el resultado podría ser
otro. Seis de los nueve casos tienen una sola corrida por enfoque, y la variabilidad es alta: un mismo caso escaló en una corrida y se validó
en la primera versión en otra. El modelo de comparación es muy capaz. El oráculo no lo elaboró un tercero independiente, aunque un autor lo revisó frente a cada ficha, y el analista simulado no
permite medir el valor de los puntos de control humano. Finalmente, como la comparación se hizo con código generado, porque Realtix no pudo compartir el suyo,
el ahorro frente al trabajo manual queda por cuantificar.

**Agregar al final de la sección, con la tabla de indicadores que hoy solo aparece en la lista de tablas:**

La [Tabla G] resume el cumplimiento de los indicadores de cada objetivo específico.

**[Tabla G]. Cumplimiento de los indicadores por objetivo específico**

| Objetivo específico | Indicador | Estado |
|---|---|---|
| OE1. Definir metas y requerimientos | 100 % del documento aprobado | Cumplido, con acta |
| OE2. Diseñar la arquitectura | 100 % del documento aprobado | Cumplido, con acta |
| OE3. Desarrollar los agentes | 100 % del producto mínimo viable funcional | Cumplido: los cuatro agentes y el orquestador operan de extremo a extremo; en la última corrida, 16 de 20 módulos quedaron validados y 4 escalaron a la revisión humana |
| OE4. Evaluar el desempeño | 90 % de aplicación de las pruebas | Cumplido: se aplicaron los once niveles del plan |

Fuente: Elaboración propia.

---

## 6.5 Impactos del proyecto

**Reemplazar la primera frase del ámbito económico por:**

En el ámbito económico, un módulo costó en promedio 0,40 dólares de inferencia y entre 3,3 y 10,3 minutos de tiempo del sistema, de modo que
cien módulos costarían cerca de 40 dólares de inferencia; es cerca del doble de lo que costaría un solo modelo con diálogo, y a cambio se
obtienen los artefactos y los controles de la [Tabla D].

---

## 7. Conclusiones

**Reemplazar el párrafo de la evaluación por:**

La evaluación confirmó que el sistema opera dentro de su límite de tiempo por módulo y de su presupuesto, con la excepción de un turno
de diálogo, pero no que produzca menos errores que un solo modelo de lenguaje: en módulos pequeños y con un modelo capaz, ambos enfoques escribieron código
correcto cuando tuvieron la información, y el sistema costó el doble o más. El valor de la arquitectura multiagente no estuvo en la corrección del
código, sino en lo que la rodea: convertir una conversación en requerimientos trazables, elegir el diseño de un catálogo cerrado, validar de
forma independiente y dejar la decisión final en manos de una persona. Frente a un modelo con la misma información, eso se tradujo además en menos
hallazgos de estilo y en ninguna entrega lista con pruebas en rojo. También quedó claro su principal riesgo: cada paso de la cadena puede
perder información, y un validador solo es tan bueno como los requerimientos contra los que juzga. En conjunto, el producto mínimo viable
constituye para Realtix un activo tecnológico propio y una base verificable para incorporar IA generativa a su fábrica de software, en línea
con la colaboración entre personas e IA que promueve la Industria 5.0 [2].

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
- Comparar el sistema con desarrollos de Realtix, si la empresa llega a compartirlos, para cuantificar el ahorro de tiempo y de costo, y comparar de forma
  sistemática los modelos asignados a cada nodo.
- Ampliar el conjunto de defectos inyectados y los casos de prueba con casos reales anonimizados.
- Filtrar la colección de dominio de negocio cuando la necesidad no pertenezca al dominio.
- Reducir las fallas del primer intento del agente desarrollador, guardando las salidas rechazadas para su diagnóstico y reforzando su prompt.
- Con datos reales de Realtix, emplear despliegues de zona de datos de EE. UU. y evaluar qué fragmentos de las bases de conocimiento pueden
  enviarse en los prompts.
- Completar el acceso remoto a la interfaz web con un enlace por sesión para el cliente, y verificar el despliegue en macOS.
- Alinear el sistema con la ISO/IEC 27090:2026 [85], en particular frente a la inyección de prompts en las respuestas del cliente y la exposición
  de los datos de las bases de conocimiento.

---

## Anexo D: entradas nuevas, en el formato de la Tabla 34

Las de los ADR-0015 a ADR-0017 están en `02-avances.md`, sección 7.

### ADR-0018. Rediseño de la interfaz web por etapas

**Estado y fecha.** Aceptada el 05/11/2026. Ajustó el ADR-0014 en la presentación de la web.

**Contexto y problema.** La web del ADR-0014 cumplía sus funciones, pero cada página era una sola columna plana. La sesión mostraba solo la
pausa pendiente, sin los requerimientos ni el diseño aprobados y sin indicar en qué punto del flujo estaba. El panel mezclaba todas las sesiones,
la vista del cliente nombraba al agente con un término que el cliente no tenía por qué conocer, y la trazabilidad y la traza se mostraban como
texto plano. El equipo pidió un diseño más propio, profesional y limpio, sin cambiar las funciones.

**Opciones consideradas.**
- Para la sesión: A. Etapas en la misma página, con pestañas que son anclas. B. Una página por etapa. C. La página plana, con secciones plegables.
- Para la trazabilidad y la traza: A. Un conversor propio del Markdown que escriben los generadores. B. Una biblioteca de Markdown. C. Plantillas
  HTML propias, armadas desde el estado.
- Para la tipografía: A. Una familia libre servida por la aplicación. B. Las fuentes del sistema.

**Decisión.** Se eligió la opción A en los tres casos. La sesión se organizó en cinco etapas, conversación, requerimientos, diseño, desarrollo y
pruebas, y aprobación final, con una línea del flujo que marca con rombos los tres puntos de control humano. Se ve una etapa a la vez, y cada una
conserva lo ya aprobado. El panel agrupó las sesiones según quién debe actuar, y la vista del cliente mostró su avance en cuatro pasos y presentó
al elicitador como «Equipo». La tipografía fue IBM Plex, con licencia libre y servida por la aplicación, sin recursos de terceros.

**Consecuencias.** Favorables: el recorrido de la sesión, sus puntos de control y lo que espera se leen de un vistazo; el panel separa lo que exige
al equipo, sin dependencias nuevas de Python. Desfavorables: hay más código de plantillas y estilos, y el conversor debe aprender cualquier sintaxis
nueva de los documentos.

**Verificación.** Se aprobaron 771 pruebas unitarias, 34 de integración, 19 de representaciones vectoriales y 33 del entorno aislado. Se revisaron
capturas en claro, en oscuro y a 390 píxeles de ancho con Edge, y el contraste de cada par de texto y fondo superó 4,5:1. No se verificaron Firefox,
Safari ni un lector de pantalla.

### ADR-0019. Casos de referencia y líneas base del objetivo 4

**Estado y fecha.** Aceptada el 05/11/2026. Ajustó el ADR-0001, con el subpaquete de evaluación.

**Contexto y problema.** La tasa de errores se medía con el tester del propio sistema, contra los requerimientos que el mismo sistema elicitó, lo que
no permitía comparar enfoques. Además, quedaban sin calcular las métricas RAGs y sin medir las decisiones 37 a 39 del ADR-0015.

**Opciones consideradas.**
- Para el oráculo: A. Pruebas de aceptación de referencia escritas desde la ficha de cada caso. B. El tester del sistema, con los requerimientos de una
  de sus corridas. C. Un juez de modelo que leyera la ficha y el código.
- Para la referencia de comparación: A. El código de Realtix. B. Una implementación de los autores. C. Código abierto de repositorios públicos. D. Código
  generado por un solo modelo de lenguaje.
- Para el modelo de comparación: A. Que conversara con el mismo cliente simulado. B. Que recibiera en un mensaje lo que sabe el cliente. C. Que recibiera
  los requerimientos aprobados por el analista.

**Decisión.** Se eligió la opción A para el oráculo, porque el tester mide contra los requerimientos del propio sistema y un juez de modelo no ejecuta el
código. Como referencia de comparación se eligió la opción D: Realtix no pudo compartir su código, por el acuerdo de confidencialidad; una implementación de
los autores no habría sido independiente, y el código abierto no implementa estas fichas ni registra tiempos ni costos. Se usaron como líneas base las
opciones A y B del modelo de comparación, con el mismo modelo del agente desarrollador. Después de ver esos resultados se agregaron mediciones exploratorias de
la calidad del código, con las reglas de la base de conocimiento y fijadas antes de calcularlas. Se usaron nueve casos sintéticos, con las seis arquitecturas, y un tope de 17 USD para todo el paso.

**Consecuencias.** Favorables: los tres enfoques se midieron con el mismo instrumento, las tablas se regeneran desde los resultados guardados y se
precisó dónde está el valor del sistema. Desfavorables: el sistema no tuvo menos errores y costó el doble o más, cada implementación necesitó un adaptador
escrito a mano, seis de los nueve casos tuvieron una sola corrida por enfoque y el ahorro frente al trabajo manual queda por cuantificar.

**Verificación.** En cada caso, la implementación de control pasó todas las verificaciones y cada uno de los 35 mutantes falló al menos una. Los oráculos
de los casos nuevos se versionaron antes de correr las líneas base. Un autor revisó los oráculos frente a las fichas y cinco juicios de las métricas RAGs. Las métricas de calidad se versionaron antes de calcularlas, y sus
resultados se revisaron a mano en dos implementaciones.
Todo el paso costó 16,74 USD de inferencia.

### ADR-0020. Despliegue de demostración en una máquina de Azure

**Estado y fecha.** Aceptada el 05/11/2026. Ajustó el acceso a la web del ADR-0017, solo en la máquina de demostración.

**Contexto y problema.** El ADR-0017 dejó la web solo en la máquina donde corre. El equipo necesitaba un enlace público para compartir el sistema, pagado
con créditos de estudiante y con la máquina apagada mientras no se usara.

**Opciones consideradas.** A. Una máquina virtual con la composición y un proxy con TLS y contraseña. B. Azure Container Apps o Container Instances. C. Solo
un túnel SSH, sin enlace público.

**Decisión.** Se eligió la opción A, porque los servicios administrados no ofrecen el Docker del anfitrión con que la aplicación crea el entorno aislado, y
un túnel no da un enlace público. Se usó una máquina de 4 vCPU y 16 GiB en Central US. Un archivo aparte de la composición agregó el proxy, único servicio
publicado hacia afuera, con TLS automático y una sola contraseña, y bajó el presupuesto de cada sesión a 1 USD. La máquina se apaga desde el portal, sin
apagado automático.

**Consecuencias.** Favorables: el enlace funciona sin cambiar el sistema ni la composición de la entrega. Desfavorables: hay una sola contraseña y ningún
enlace por sesión para el cliente, la clave de Azure OpenAI queda también en esa máquina, no hay un tope global de gasto y, si queda encendida, sigue
cobrando. Solo admite datos sintéticos, de modo que no reemplaza el despliegue en la infraestructura de la empresa con datos reales.

**Verificación.** La composición arrancó desde cero en unos 5 minutos. Desde afuera, la web respondió por HTTPS con certificado, con 401 sin contraseña y 200
con ella, y los puertos de la base de datos, de la aplicación y de las representaciones vectoriales no respondieron. Un módulo real quedó validado en la
primera versión, en 3,15 minutos y por 0,198 USD, y tras un reinicio el enlace volvió en 32 segundos con su sesión. También volvió al detener e iniciar la máquina desde el portal.

### Ajustes a las entradas existentes

Además de los que indica `02-avances.md`, sección 7, agregar en «Estado y fecha»:

| Registro | Agregar |
|---|---|
| ADR-0001 | Ajustada también por el ADR-0019, que agregó el subpaquete de evaluación. |
| ADR-0014 | Ajustada también por el ADR-0018, en la presentación de la web. |
| ADR-0015 | Sus decisiones 37 a 39 se midieron en el ADR-0019. |
| ADR-0017 | Ajustada por el ADR-0020, solo en la máquina de demostración, que agregó acceso remoto con TLS y contraseña. |
