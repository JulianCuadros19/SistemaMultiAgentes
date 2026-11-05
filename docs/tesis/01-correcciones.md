# Correcciones al documento de tesis

**Versión contrastada:** «Trabajo de Grado - Sistema Multiagente Realtix», 112 páginas, exportada
el 4 de noviembre de 2026. Las páginas son las impresas al pie.

**Formato de cada entrada:**
- dónde está;
- lo que dice hoy, citado tal cual;
- lo que debe decir;
- por qué.

Las cifras vienen de `03-cifras.md`. Cuando una corrección pide texto nuevo largo, remite a
`02-avances.md`.

## Qué cambió desde esa versión, en una lista

- **Requerimientos:** son 39, no 38. Se agregó el RF-39, enmiendas desde la validación final, y el
  RF-38 admite tres destinos (ADR-0015).
- **Modelos de lenguaje:** son solo los desplegados en Azure OpenAI. El RF-37 y el RNF-06 ya no
  piden modelos locales (ADR-0017, requerimientos 1.3).
- **Presupuesto y traza:** el presupuesto por módulo existe y detiene la ejecución. La traza por
  nodo vive en PostgreSQL, y Langfuse salió del stack (ADR-0016).
- **Cifras del sistema:**
  - 17 registros de decisión, no 14;
  - 840 pruebas automatizadas, no 582;
  - 187 fragmentos, no 186.
- **Evaluación:** se hizo una corrida ampliada de 20 casos. En la línea base se validaron 10 de 19
  módulos en la primera versión; en la final, 20 de 20, 18 en la primera.
- **Entrega:** el sistema se entrega en contenedores, con un solo comando, verificado desde un clon
  limpio (ADR-0017).

## Preliminares

### C-01 · Resumen, p. 14, tercer párrafo

- **Dice hoy:** «Para ello se especificaron 38 requerimientos funcionales y diez no funcionales, se
  diseñó un grafo de diecisiete nodos en LangGraph con tres aprobaciones humanas y cuatro bases de
  conocimiento, se implementaron los agentes con modelos remotos y representaciones vectoriales
  locales, y se evaluó el sistema con un plan de pruebas de seis niveles.»
- **Debe decir:** «Para ello se especificaron 39 requerimientos funcionales y diez no funcionales, se
  diseñó un grafo de diecisiete nodos en LangGraph con tres aprobaciones humanas y cuatro bases de
  conocimiento, se implementaron los agentes con los modelos de lenguaje desplegados en Azure OpenAI
  y representaciones vectoriales locales, y se evaluó el sistema con un plan de pruebas de siete
  niveles.»
- **Por qué:**
  - RF-39 (ADR-0015);
  - Azure OpenAI como único proveedor (ADR-0017);
  - el plan gana el nivel de la entrega en contenedores (C-28).

### C-02 · Resumen, p. 14, cuarto párrafo

- **Dice hoy:** «Se obtuvo un producto mínimo viable que se ejecuta en la infraestructura de la
  empresa: nueve de nueve corridas de integración produjeron un módulo validado en 2,7 a 14,3
  minutos, frente a un límite de 20, con un costo de 0,16 a 0,37 dólares por módulo y turnos de
  hasta 4,8 segundos. El tester detectó los dieciséis defectos inyectados sin rechazos falsos, se
  aprobaron 582 pruebas automatizadas y, de los diez requerimientos no funcionales, seis se
  cumplieron y cuatro de forma parcial.»
- **Debe decir** (propuesta): «Se obtuvo un producto mínimo viable, empaquetado en contenedores, que
  se ejecuta en la infraestructura de la empresa. En la corrida final sobre veinte casos
  sintéticos, los veinte módulos quedaron validados, dieciocho en la primera versión, en 5,3 minutos
  de media y 13,2 como máximo, frente a un límite de 20, con un costo medio de 0,34 dólares por
  módulo y turnos de hasta 9,4 segundos. El tester detectó los 21 defectos inyectados sin rechazar
  los controles, se aprobaron 840 pruebas automatizadas y, de los diez requerimientos no
  funcionales, ocho se cumplieron y dos de forma parcial.»
- **Por qué:**
  - corrida final del ADR-0015;
  - corpus del tester ampliado en el ADR-0015;
  - pruebas al cierre del paso 14;
  - Tabla 27 actualizada (C-30). «Ocho y dos» supone que el RNF-04 sigue parcial: ver la decisión
    pendiente de C-30.

### C-03 · Abstract, p. 15, párrafos tercero y cuarto

- **Dice hoy:** «To this end, 38 functional and ten non-functional requirements were specified, a
  seventeen-node graph was designed in LangGraph with three human approvals and four knowledge
  bases, the agents were implemented with remote models and local embeddings, and the system was
  evaluated with a six-level test plan.» Y: «The result is a minimum viable product that runs on
  the company's infrastructure: nine out of nine integration runs produced a validated module in
  2.7 to 14.3 minutes, against a 20-minute limit, at a cost of 0.16 to 0.37 dollars per module and
  with turns of up to 4.8 seconds.»
- **Debe decir:** la traducción de C-01 y C-02. Por ejemplo:
  - «39 functional and ten non-functional requirements»;
  - «the agents were implemented with the language models deployed on Azure OpenAI and local
    embeddings»;
  - «a seven-level test plan»;
  - «in the final run on twenty synthetic cases, all twenty modules were validated, eighteen in the
    first version, in 5.3 minutes on average and 13.2 at most, at an average cost of 0.34 dollars
    per module and with turns of up to 9.4 seconds»;
  - «the tester detected all 21 injected defects without rejecting the controls, 840 automated
    tests passed and, of the ten non-functional requirements, eight were met and two partially».
- **Por qué:** coherencia con el resumen.

### C-04 · Introducción, «Alcance y limitaciones», p. 19

- **Dice hoy:** «El proyecto entregó un producto mínimo viable de un sistema multiagente, ejecutable
  en la infraestructura de Realtix, con inferencia mediante modelos de lenguaje remotos y con
  representaciones vectoriales generadas localmente, compuesto por cuatro agentes funcionales y un
  orquestador que coordina su flujo de trabajo.»
- **Debe decir:** «…ejecutable en la infraestructura de Realtix, empaquetado en contenedores, con
  inferencia mediante los modelos de lenguaje desplegados en Azure OpenAI y con representaciones
  vectoriales generadas localmente…»
- **Por qué:** ADR-0017.

### C-05 · 1.6.4.2 Entregables, p. 48

- **Dice hoy:** «Producto en local del sistema multiagente de IA entregado a Realtix.»
- **Debe decir:** «Producto del sistema multiagente de IA empaquetado en contenedores, ejecutable en
  la infraestructura de Realtix con los modelos de lenguaje de Azure OpenAI.»
- **Por qué:** el equipo descartó los modelos de lenguaje locales (ADR-0017). Si «en local» se
  quiso decir «en la infraestructura de la empresa», basta aclararlo así.

## Capítulo 2

### C-06 · 2.4, p. 53

- **Dice hoy:** «Se especificaron 38 requerimientos funcionales, organizados en siete componentes que
  reflejan la separación de responsabilidades del sistema.»
- **Debe decir:** «Se especificaron 39 requerimientos funcionales…»
- **Por qué:** RF-39 (ADR-0015).

### C-07 · Tabla 18, pp. 53 y 54

- **Hoy suma 38 requerimientos:** orquestador 3 y operación 6, con el RF-38.
- **Debe:** agregar el RF-39.
- **Dónde va el RF-39:**
  - en el documento de requerimientos, el RF-38 y el RF-39 están en la sección «Orquestador y flujo
    iterativo»;
  - la tesis ubicó el RF-38 en «Operación».
- **Recomendación:** poner el RF-39 en «Orquestador y flujo iterativo», que pasa de 3 a 4. El
  alcance de esa fila agrega «…y enmiendas de los requerimientos desde la validación final». El
  total queda en 39.

### C-08 · 2.4, p. 54

- **Dice hoy:** «Siguiendo esta misma ficha se especificaron los 37 requerimientos funcionales
  restantes. La Tabla 32 del Anexo C presenta los 38 con su identificador, componente y enunciado,
  y sus criterios de aceptación completos se conservan en el documento de requerimientos.»
- **Debe decir:** «…se especificaron los 38 requerimientos funcionales restantes. La Tabla 32 del
  Anexo C presenta los 39…»

### C-09 · 2.6, p. 55

- **Dice hoy:** «…los 38 requerimientos funcionales con sus criterios de aceptación, los diez no
  funcionales…»
- **Debe decir:** «…los 39 requerimientos funcionales…». Al final de la sección, una oración: «Durante
  el desarrollo, el documento se actualizó a las versiones 1.1 (ADR-0004), 1.2 (ADR-0015) y 1.3
  (ADR-0017).»

## Capítulo 3

### C-10 · 3.3, p. 57

- **Dice hoy:** «El nodo de decisión devuelve el módulo al desarrollador mientras queden intentos, con
  un máximo configurable de tres, o lo envía a la revisión humana final, donde una persona aprueba
  el módulo, lo devuelve al desarrollador o al arquitecto, o cierra la sesión.»
- **Debe decir:** «…donde una persona aprueba el módulo, lo devuelve al desarrollador o al arquitecto,
  pide al elicitador una enmienda de los requerimientos con una regla nueva o cierra la sesión. La
  enmienda recorre la síntesis, la aprobación de los requerimientos y el plan de pruebas, y vuelve
  a la generación con el mismo diseño.»
- **Por qué:** RF-39 (ADR-0015).

### C-11 · Figura 8, p. 58

- **Hoy no tiene el camino de la enmienda ni la pausa por presupuesto.**
- **Debe:** agregar las aristas N17 → N5, N6 → N5 y N16 → N10, una marca de presupuesto en N3, N5,
  N8, N10 y N14, y cambiar la etiqueta del retorno de N17. El detalle y el diagrama de referencia
  están en `04-arquitectura-final.md`, secciones 2 y 9.

### C-12 · 3.3, pp. 58 y 59

- **Dice hoy:** «…ciclos evaluador y optimizador entre N3 y N4 y entre N10 y N15, una bifurcación en
  paralelo tras N6, en la que el plan de pruebas de N16 se elaboró mientras trabajaba el arquitecto,
  e intervención humana en N6, N9 y N17.»
- **Debe decir:** agregar al final «…e intervención humana en N6, N9 y N17, con retornos desde N17 al
  desarrollador, al arquitecto o, mediante una enmienda, al elicitador».

### C-13 · 3.4, p. 60, referencia rota

- **Dice hoy:** «A modo de ejemplo, la ¡Error! No se encuentra el origen de la referencia. reproduce
  el prompt de sistema del nodo de diálogo del agente elicitador en su versión vigente al cierre del
  desarrollo…»
- **Debe:** reinsertar la figura «Prompt de sistema del nodo de diálogo del agente elicitador», con
  la versión 1.10 (`prompts/elicitador/dialogo.md`), y rehacer la referencia. Si no, reescribir la
  oración para remitir al Anexo F.
- **Por qué:**
  - la figura ya no existe en el cuerpo, y la lista de figuras la conserva como «¡Error! Marcador no
    definido» (C-45);
  - la misma referencia rota está en el Anexo F (C-44).

### C-14 · 3.4, p. 60

- **Dice hoy:** «Los prompts de sistema de cada agente se versionan como activos del repositorio y se
  registran en las trazas de observabilidad de cada ejecución…»
- **Debe decir:** «…y cada llamada al modelo registra el identificador y la versión de su prompt en la
  traza por nodo que guarda PostgreSQL…»
- **Por qué:** ADR-0016, tabla `llamadas_modelo`.

### C-15 · 3.6, p. 62

- **Dice hoy:** «Así, el modelo de cada nodo puede sustituirse por configuración, incluso por uno de
  ejecución local, sin modificar el código. La inferencia se realizó con modelos remotos, mientras
  que las representaciones vectoriales se generaron con un modelo local, lo que elimina el costo
  por token de una indexación que se repite durante el afinamiento y evita enviar el corpus de
  dominio a un proveedor externo.»
- **Debe decir:** «Así, el modelo de cada nodo, o su versión, puede sustituirse editando la
  configuración, sin modificar el código. Los modelos de lenguaje son los desplegados en Azure
  OpenAI, único proveedor de modelos de lenguaje del sistema, mientras que las representaciones
  vectoriales se generan con un modelo local, lo que elimina el costo por token de una indexación
  que se repite durante el afinamiento y evita enviar el corpus de dominio a un proveedor externo.»
- **Por qué:** ADR-0017 y RNF-06 de los requerimientos 1.3.

### C-16 · 3.7, p. 62

- **Dice hoy:** «…contexto recuperado y control de iteraciones y costo.» Y, en el modelo de datos:
  «…ejecuciones con su traza de consumo…»
- **Debe decir:**
  - «…contexto recuperado y control de iteraciones, costo acumulado, presupuesto y sus
    ampliaciones.»;
  - «…ejecuciones de cada nodo y llamadas al modelo, con sus tokens, costo y latencia…».
- **Agregar una oración:** «La partición de requerimientos conserva además las enmiendas pedidas
  desde la revisión final.»
- **Por qué:** ADR-0015 y ADR-0016.

### C-17 · 3.8, pp. 62 y 63

- **Dice hoy:** «El sistema se diseñó para entregarse en contenedores orquestados con un archivo de
  composición único, que comprende el servicio de aplicación con el orquestador, los agentes y la
  capa de operación por consola y web, la base de datos con su extensión vectorial, la generación
  local de las representaciones vectoriales y el entorno aislado de ejecución de código; la
  inferencia se resuelve con modelos remotos a través de la capa de acceso de la sección 3.6.»
- **Debe decir:** «El sistema se entrega en contenedores orquestados con un archivo de composición
  único, que comprende el servicio de aplicación con el orquestador, los agentes y la capa de
  operación por consola y web, la base de datos con su extensión vectorial, la generación local de
  las representaciones vectoriales, la ingesta de las bases de conocimiento y el entorno aislado de
  ejecución de código. Los modelos de lenguaje son los desplegados en Azure OpenAI, a los que se
  accede por la capa de la sección 3.6. Un solo comando levanta la composición, y la interfaz web
  se publica solo en la máquina donde corre. La aplicación crea el entorno aislado mediante el
  Docker del anfitrión.»
- **Por qué:** ADR-0017. La vista completa está en `04-arquitectura-final.md`, sección 7.

### C-18 · 3.9, p. 63

- **Dice hoy:** «Durante el desarrollo, el registro de decisión ADR-0004 actualizó la arquitectura
  con los nodos N16 y N17 y adoptó el término especificación de diseño en lugar de contrato de
  diseño, cambios que se reflejan en este capítulo.»
- **Debe decir:** agregar después «Los registros ADR-0015 a ADR-0017 llevaron la arquitectura a su
  versión 1.5: enmiendas de los requerimientos desde la revisión final, presupuesto por módulo con
  pausa y traza por nodo, y entrega en contenedores con Azure OpenAI como único proveedor de
  modelos de lenguaje.»

## Capítulo 4

### C-19 · Introducción del capítulo, p. 64

- **Debe:** agregar a la enumeración de contenidos «la calidad de la primera salida y las enmiendas,
  el control de costo y la traza por nodo, y el empaquetado en contenedores».

### C-20 · 4.2, p. 65

- **Dice hoy:** «Todas las invocaciones se dirigieron a modelos remotos a través de esta capa,
  mientras que la generación de las representaciones vectoriales se resolvió de forma local, como
  se describe en la sección 4.6.»
- **Debe decir:** «Todas las invocaciones se dirigieron a los despliegues de Azure OpenAI a través de
  esta capa…»
- **Opcional:** agregar a la Tabla 20 la versión de cada modelo:
  - gpt-5.4-mini 2026-03-17;
  - gpt-5 2025-08-07;
  - gpt-6.1-sol 2026-09-29;
  - gpt-6-luna 2026-09-22.

  Todos son Global Standard, en South Central US.

### C-21 · 4.3 y Tabla 21, p. 65

- **Dice hoy:** «Las decisiones tomadas durante el desarrollo se documentaron en catorce registros de
  decisión arquitectónica, que la Tabla 21 lista por su nombre.»
- **Debe decir:** «…en diecisiete registros…». Además, agregar tres filas:
  - ADR-0015 «Calidad de la primera salida y enmiendas de los requerimientos desde N17»;
  - ADR-0016 «Control de costo y traza por nodo»;
  - ADR-0017 «Entrega en contenedores con Azure OpenAI».

### C-22 · 4.6, p. 66

- **Dice hoy:** «…sobre un corpus de 36 documentos segmentados en 186 fragmentos…»
- **Debe decir:** «…en 187 fragmentos…»
- **Por qué:** la regla CAL-FS-006 (ADR-0015) sumó uno a criterios de calidad. Quedan 62 de
  elicitación, 40 de dominio, 33 de arquitecturas y 52 de criterios.

### C-23 · 4.7, pp. 67 y 68

- **Debe:** al final de cada subsección de agente, o en la sección nueva de C-27, agregar los
  cambios del ADR-0015 por agente.
- **Fuente:** `02-avances.md`, sección 3.3.
- **Lo que dice hoy:** sigue siendo cierto, con una precisión en 4.7.4. El juez sigue valorando
  únicamente las pruebas, pero ahora ve las interfaces y el modelo de datos de la especificación y
  confirma cada rechazo con una segunda opinión.

### C-24 · 4.9, p. 69

- **Debe:** agregar las capacidades posteriores a esa versión:
  - pedir una enmienda en la revisión final;
  - la pausa por presupuesto, con su ampliación;
  - la página «Traza por nodo» y el comando `multiagente traza`;
  - la operación con la composición: web en `http://127.0.0.1:8000/` y consola con `docker compose
    run`.
- **Fuente:** `02-avances.md`, sección 6.

### C-25 · 4.11, p. 70

- **Dice hoy:** «En la última ejecución registrada se aprobaron 507 pruebas unitarias, 30 pruebas de
  integración, 19 pruebas de representaciones vectoriales y 26 pruebas del entorno aislado, que en
  conjunto suman 582 pruebas.»
- **Debe decir:** «…se aprobaron 754 pruebas unitarias, 34 pruebas de integración, 19 pruebas de
  representaciones vectoriales y 33 pruebas del entorno aislado, que en conjunto suman 840
  pruebas.»
- **Por qué:** cierre del paso 14 (ADR-0017).

### C-26 · 4.13, p. 71

- **Dice hoy:** «Quedaron fuera de esta etapa el presupuesto configurable que detiene la ejecución, el
  acceso remoto con autenticación y la comparación sistemática de modelos de lenguaje, previstos
  para versiones posteriores del sistema.»
- **Debe decir:** «El sistema incorporó después el presupuesto que detiene la ejecución y la traza por
  nodo, y se empaquetó en contenedores con un solo comando de arranque. Quedaron fuera el acceso
  remoto con autenticación, que el equipo dejó como trabajo futuro, y la comparación con el
  desarrollo manual, con un modelo único y entre modelos para cada nodo, prevista para la fase de
  evaluación.»
- **Por qué:** ADR-0016 y ADR-0017. El paso 15 sigue pendiente.

### C-27 · Secciones nuevas del capítulo 4

Después de la 4.10 y antes de «Pruebas automatizadas», agregar tres secciones:
- «Calidad de la primera salida y enmiendas desde la revisión final»;
- «Control de costo y traza por nodo»;
- «Empaquetado en contenedores con Azure OpenAI».

El material está en `02-avances.md`, secciones 3 a 5. La numeración de las secciones siguientes se
corre.

## Capítulo 5

### C-28 · 5.1 y Tabla 24, pp. 72 y 73

- **Dice hoy:** «Estas corridas partieron de tres casos sintéticos del dominio catastral, sin datos de
  Realtix: el cálculo del avalúo, la liquidación por lotes y el registro de mutaciones.»
- **Debe:** agregar «A ellas se sumó una corrida ampliada sobre veinte casos sintéticos nuevos, de
  tres a cuatro por arquitectura del catálogo, sin datos de Realtix, con una línea base y una
  corrida final.»
- **Tabla 24:**
  - «582 pruebas en la última ejecución» → «840 pruebas en la última ejecución».
  - Nivel «Desempeño del tester»: agregar que el corpus se amplió a 21 defectos y 3 controles en el
    ADR-0015.
  - Nivel «Corrida final de evaluación»:
    - debe decir «Corrida ampliada de evaluación»;
    - qué verifica: el flujo completo sobre necesidades variadas, antes y después del pulido del
      ADR-0015;
    - casos: 20 casos sintéticos, con una corrida de línea base y una corrida final;
    - criterio: los fijados antes de medir (`03-cifras.md`, sección 8).

    La corrida de 3 casos queda en el texto como la verificación posterior a los ajustes de
    robustez.
  - Nivel nuevo, «Entrega en contenedores»:
    - qué verifica: el sistema completo desde un clon limpio;
    - casos: un caso con el analista simulado;
    - criterio: módulo validado con los modelos de Azure OpenAI.

### C-29 · 5.2, Tabla 25 y 5.3, pp. 73 y 74

**5.2:** conservar la integración y la corrida de 3 casos y agregar los resultados de la corrida
ampliada:
- una tabla con la línea base y la final;
- la tabla de criterios;
- la tabla por caso, si cabe.

Están en `03-cifras.md`, sección 8, y en `02-avances.md`, secciones 2 y 3.5.

**5.3:**
- **Dice hoy:** «Para medir la capacidad del tester de detectar errores se inyectaron dieciséis
  defectos conocidos en el código evaluado y se ejecutó la validación en tres corridas.»
- **Debe:** agregar la medición del ADR-0015.
  - Con el corpus ampliado a 21 defectos y 3 controles, en tres corridas, el tester detectó 63 de 63
    defectos y aprobó 9 de 9 controles. Las métricas de la Tabla 26 se mantienen en 1,00.
  - Al rejuzgar las 49 versiones reales guardadas, coincidió con su veredicto original en 40.

### C-30 · 5.5 y Tabla 27, pp. 75 y 76

**Filas de la Tabla 27:**

| Requerimiento | Evidencia nueva | Estado |
|---|---|---|
| RNF-01 | Agregar: «en la corrida final de 20 casos, media de 5,3 min y máximo de 13,2 min por módulo; turno más largo de 9,4 s» | Cumplido |
| RNF-03 | «26 pruebas del entorno aislado» → «33»; además, en la entrega, el entorno aislado corre sin red y sin root también cuando lo crea la aplicación en contenedor | Cumplido |
| RNF-04 | Sin cambios en la evidencia. Precisar que los prompts se procesan en Azure OpenAI, dentro de su límite de cumplimiento | Decisión del equipo: se recomienda mantener «Cumplido parcialmente» |
| RNF-05 | «en su versión 1.2» → las versiones vigentes: diálogo 1.10, extracción 1.7, síntesis 1.9, enmienda 1.0, selección 1.2, parametrización 1.6, generación 1.9 y veredicto 1.2 | Cumplido |
| RNF-06 | «Capa de acceso agnóstica al proveedor sobre la API de OpenAI v1; el modelo, el esfuerzo de razonamiento y el límite de salida de cada nodo se configuran sin tocar el código, y el modelo de N3 y N5 se cambió durante el desarrollo editando solo la configuración (ADR-0009)» | Cumplido |
| RNF-07 | «El sistema completo corre en contenedores con Docker Desktop sobre Windows y WSL2, verificado desde un clon limpio, con la web accesible desde Ubuntu y desde Windows; macOS no se verificó» | Cumplido parcialmente |
| RNF-09 | Agregar «o, con una enmienda, al elicitador» | Cumplido |
| RNF-10 | «Costo registrado por nodo y por sesión en PostgreSQL; presupuesto de 1,50 USD por módulo que pausa la sesión antes del siguiente nodo con modelo hasta que una persona lo amplía o la cierra, verificado con una sesión real que se detuvo al superarlo» | Cumplido |

**Texto que sigue a la tabla:**
- **Dice hoy:** «De los diez requerimientos no funcionales, seis se cumplieron y cuatro de forma
  parcial. Las limitaciones se deben a que la inferencia se realizó con modelos remotos, lo que deja
  sin verificar la operación íntegra con modelos locales y hace que los fragmentos recuperados
  viajen en los prompts enviados al proveedor; a que la compatibilidad solo se verificó en Ubuntu
  sobre WSL2, y a que el presupuesto configurable quedó pendiente. Por el uso de modelos remotos, el
  RF-37, que exige operar sin dependencia de proveedores de nube, también se cumplió de forma
  parcial.»
- **Debe decir:** «De los diez requerimientos no funcionales, ocho se cumplieron y dos de forma
  parcial: el RNF-04, porque los fragmentos recuperados viajan en los prompts que procesa Azure
  OpenAI, y el RNF-07, porque el despliegue no se verificó en macOS. El RF-37 se cumplió con su
  enunciado vigente: el sistema se entrega en contenedores y completa el flujo de extremo a extremo
  con los modelos de Azure OpenAI y las representaciones vectoriales locales.»
- **Por qué:**
  - ADR-0016;
  - ADR-0017;
  - RF-37 y RNF-06 de los requerimientos 1.3.

**Decisión pendiente del equipo.** El RNF-04 dice que la información de dominio debe permanecer bajo
control de la empresa y que los embeddings se generan localmente.
- **Lo que se cumple:** los embeddings son locales.
- **Lo que no:** los fragmentos que se inyectan en los prompts salen al recurso de Azure OpenAI.
- **Recomendación:** mantenerlo como «Cumplido parcialmente», con esa explicación. Si el equipo
  considera que el recurso de Azure de la empresa cumple «bajo control de la empresa», pasaría a
  «Cumplido» y el conteo quedaría en nueve y uno.

### C-31 · 5.6, p. 76

- **Dice hoy:** «El primero es sistemático: en los tres casos de la corrida final, el nodo de
  generación de código necesitó dos intentos, porque el primero fue rechazado por incluir un
  archivo requirements.txt, lo que duplicó el costo de ese nodo; la solución propuesta es indicar en
  el prompt del desarrollador que no genere ese archivo, que la exportación ya produce. Queda
  pendiente, además, que el primer intento también puede fallar por excepciones sin importar o por
  sangría incorrecta.»
- **Debe decir:** «…; la solución se aplicó: el desarrollador dejó de escribir ese archivo, que el
  sistema genera al exportar (ADR-0014).» Y agregar los hallazgos de la corrida ampliada:
  - los primeros intentos rechazados del desarrollador bajaron de 7 de 29 a 7 de 23, sin alcanzar
    la meta de 2 de 29;
  - las causas restantes son una respuesta incompleta (3), funciones con `self` en el diseño (2) y
    estilo (2);
  - el cierre de la elicitación pasó de 30 s en 3 casos, con un máximo de 51 s.
- **Fuente:** `02-avances.md`, sección 3.6.

## Capítulo 6

### C-32 · 6.1, p. 77

- **Dice hoy:** «…y se especificaron 38 requerimientos funcionales en siete componentes…». Y: «Como
  aspecto por mejorar, la especificación inicial no anticipó la revisión humana final ni el plan de
  pruebas independiente, que se incorporaron durante el desarrollo mediante el registro ADR-0004,
  con el RF-38 y los nodos N16 y N17; además, el presupuesto que limita el costo por módulo,
  previsto en el RNF-10, no alcanzó a implementarse.»
- **Debe decir:**
  - «…39 requerimientos funcionales…»;
  - «…mediante el registro ADR-0004, con el RF-38 y los nodos N16 y N17, y tampoco las enmiendas de
    los requerimientos desde la revisión final, que agregó el ADR-0015 con el RF-39. El presupuesto
    del RNF-10 se implementó en el paso 13 (ADR-0016).»

### C-33 · 6.2, pp. 77 y 78

- **Dice hoy:** «…concentraron el 51 % y el 31 % del costo, como se había previsto.» Y: «En contraste,
  dos decisiones se cumplieron solo en parte: los fragmentos recuperados viajan en los prompts
  enviados al modelo remoto, lo que limita la confidencialidad del RNF-04, y la operación íntegra
  con modelos locales, prevista por el RNF-06, no se verificó.»
- **Debe decir:**
  - agregar «…y, en la corrida final de veinte casos, el 41 % y el 27 %»;
  - la oración final: «En contraste, una decisión se cumplió solo en parte: los fragmentos
    recuperados viajan en los prompts que procesa Azure OpenAI, lo que limita la confidencialidad
    del RNF-04. La operación con modelos locales, que preveía la versión inicial del RNF-06, se
    descartó al fijar Azure OpenAI como único proveedor de modelos de lenguaje (ADR-0017).»
- **Opcional:** mencionar como segundo cambio estructural las aristas de la enmienda (ADR-0015).

### C-34 · 6.3, p. 78

- **Dice hoy:**
  - «…las bases de conocimiento con 36 documentos y 186 fragmentos…»;
  - «…produjeron un módulo validado en nueve de nueve corridas.»;
  - «El sistema aprobó 582 pruebas automatizadas, y las decisiones del desarrollo quedaron
    documentadas en catorce registros de decisión arquitectónica.»;
  - «Como debilidades, el agente desarrollador falló al primer intento en cinco de las nueve
    generaciones de la integración…»
- **Debe decir:**
  - «…187 fragmentos…»;
  - «…en nueve de nueve corridas de integración y, tras el pulido del ADR-0015, en veinte de veinte
    casos de la corrida ampliada final.»;
  - «…840 pruebas… diecisiete registros…»;
  - en las debilidades, agregar «…y en la corrida final, en 7 de 23 primeros intentos, de ellos 3
    por una respuesta incompleta».

### C-35 · 6.4, pp. 78 y 79

- **Dice hoy:** «Los módulos se validaron en 2,7 a 14,3 minutos frente al límite de 20, los turnos de
  diálogo no superaron 4,8 segundos frente al máximo de 15 y el costo de inferencia fue de 0,16 a
  0,37 dólares por módulo, con una media de 0,27.» Y: «Los resultados de tiempo son buenos y tienen
  holgura: el módulo más lento consumió el 72 % del tiempo permitido y el turno más largo, cerca de
  un tercio del máximo.»
- **Debe decir:**
  - agregar los resultados de la corrida final: veinte de veinte validados, dieciocho en la primera
    versión, frente a diez de diecinueve en la línea base; 5,3 minutos de media y 13,2 como máximo;
    turnos de hasta 9,4 segundos; 0,342 dólares de media por módulo, de 0,18 a 0,87;
  - con esas cifras, el módulo más lento consumió el 66 % del tiempo permitido y el turno más largo,
    el 63 % del máximo;
  - «seis se cumplieron y cuatro de forma parcial» → «ocho se cumplieron y dos de forma parcial».
- **Las limitaciones siguen vigentes:**
  - casos sintéticos;
  - métricas RAGs sin calcular;
  - sin comparación con el desarrollo manual.

  Agregar que la comparación es el paso 15.

### C-36 · 6.5, p. 79

- **Dice hoy:** «En el ámbito económico, un módulo validado costó en promedio 0,27 dólares de
  inferencia y entre 2,7 y 14,3 minutos de tiempo del sistema, de modo que cien módulos costarían
  cerca de 27 dólares de inferencia…». Y: «…un activo propio que reúne 38 requerimientos, un grafo
  de diecisiete nodos, catorce registros de decisión, cuatro bases de conocimiento y 582 pruebas
  automatizadas…»
- **Debe decir:**
  - «…un módulo validado costó en promedio 0,342 dólares de inferencia en la corrida final y 5,3
    minutos de tiempo del sistema, de modo que cien módulos costarían cerca de 34 dólares…»;
  - «…39 requerimientos, un grafo de diecisiete nodos, diecisiete registros de decisión, cuatro bases
    de conocimiento y 840 pruebas automatizadas, empaquetado en contenedores…».
- **Opcional:** mencionar que el presupuesto por módulo, de 1,50 dólares por defecto, acota el gasto
  de cada sesión.

## Capítulo 7

### C-37 · Conclusiones, p. 81

- **Dice hoy:** «El objetivo general se cumplió: el sistema automatizó la cadena que va de la
  conversación con el cliente al código validado y produjo un módulo validado en nueve de nueve
  corridas de integración, dentro de los umbrales de tiempo.»
- **Debe decir:** «…y produjo un módulo validado en nueve de nueve corridas de integración y en veinte
  de veinte casos de la corrida ampliada final, dieciocho en la primera versión, dentro de los
  umbrales de tiempo.»
- **Opcional:**
  - **Párrafo nuevo:** la mejora de la primera salida vino de dar al arquitecto y al tester la
    noción de escenario ejecutable. Con ella, la primera versión pasó al tester en 18 de 20 casos,
    frente a 10 de 19.
  - **Cambio en el párrafo de la evaluación:** «modelos remotos» → «modelos de un único proveedor».

## Capítulo 8

### C-38 · Recomendaciones, p. 82

- **Quitar** «Implementar el presupuesto configurable que detenga la ejecución al alcanzar un costo
  máximo por módulo, para completar el RNF-10.» Ya está hecho (ADR-0016).
- **Quitar** «Verificar la operación íntegra con modelos de ejecución local, de modo que se cumplan
  el RF-37 y el RNF-06 y que los fragmentos de las bases de conocimiento no salgan de la empresa.»
  El equipo lo descartó (ADR-0017). En su lugar, si se quiere: «Con datos reales de Realtix,
  emplear despliegues de zona de datos de EE. UU. y evaluar qué fragmentos de las bases de
  conocimiento pueden enviarse en los prompts.»
- **Actualizar** «Reducir las fallas del primer intento del agente desarrollador, guardando las
  salidas rechazadas para su diagnóstico y reforzando su prompt.» Precisar que la causa principal
  restante es la respuesta incompleta, en 3 de 23 primeros intentos.
- **Mantener:**
  - «Incorporar autenticación para el acceso remoto…»;
  - la comparación con el desarrollo manual, que es el paso 15;
  - las métricas RAGs;
  - la ISO/IEC 27090.
- **Agregar:**
  - medir las decisiones 37 a 39 del ADR-0015;
  - resolver dónde queda lo que el cliente pide en los resultados;
  - plantear mejor las necesidades dirigidas por eventos.

## Anexos

### C-39 · Anexo C, p. 95

- **Dice hoy:** «El presente anexo consolida los 38 requerimientos funcionales y los diez
  requerimientos no funcionales especificados en el documento de requerimientos, en su versión
  actualizada por el registro de decisión ADR-0004.»
- **Debe decir:** «…los 39 requerimientos funcionales… en su versión 1.3, actualizada por los
  registros ADR-0004, ADR-0015 y ADR-0017.»

### C-40 · Tabla 32 del Anexo C, p. 96

**RF-37:**
- **Dice hoy:** «Entregar el sistema empaquetado en contenedores, capaz de operar sin dependencia de
  proveedores de nube.»
- **Debe decir:** «Entregar el sistema empaquetado en contenedores, capaz de operar de extremo a
  extremo con los modelos de lenguaje desplegados en Azure OpenAI y con el modelo de
  representaciones vectoriales ejecutado localmente.»

**RF-38:**
- **Dice hoy:** «Permitir que una persona revise el código y el reporte de validación, ejecute pruebas
  propias y decida aprobar el módulo, devolverlo con observaciones o cerrar la sesión.»
- **Debe decir:** «…y decida aprobar el módulo, devolverlo con observaciones al desarrollador o al
  arquitecto, pedir una enmienda de los requerimientos o cerrar la sesión.»

**Fila nueva, RF-39:**
- **Componente:** el que se elija en C-07.
- **Enunciado:** «Incorporar a los requerimientos vigentes, como una enmienda aprobada por el
  analista, una regla de negocio descubierta en la validación final, sin renumerar requerimientos
  ni escenarios; rehacer el plan de pruebas y corregir el módulo con el mismo diseño.»

### C-41 · Tabla 33 del Anexo C, p. 97

**RNF-06:**
- **Dice hoy:** «La capa de acceso a modelos es agnóstica al proveedor y permite operar íntegramente
  con modelos de ejecución local.»
- **Debe decir:** «La capa de acceso a modelos es agnóstica al proveedor y permite sustituir el modelo
  de cada agente por configuración.»

**RNF-09** (opcional): agregar «…; ante un rechazo, el flujo regresa al agente anterior con
observaciones y, desde la validación final, también al arquitecto o, con una enmienda, al
elicitador.»

### C-42 · Anexo D, pp. 98 a 106

- **Dice hoy:** «El presente anexo detalla los catorce registros de decisión arquitectónica listados
  en la sección 4.3.»
- **Debe decir:** «…los diecisiete registros…»
- **Además:**
  - agregar las entradas de los ADR-0015, ADR-0016 y ADR-0017;
  - ajustar el «Estado y fecha» de las entradas que ellos modificaron.

  Todo está en `02-avances.md`, sección 7.

### C-43 · Anexo E, Tabla 35, p. 107

- **Debe:** reemplazar las responsabilidades de N1, N3, N5, N6, N8, N9, N10, N12, N14, N15, N16 y N17
  por las vigentes (`04-arquitectura-final.md`, sección 1).
- **Agregar una nota:** antes de N3, N5, N8, N10 y N14, la sesión pausa si alcanzó su presupuesto.

### C-44 · Anexo F, p. 108

- **Dice hoy:** «…y los prompts de sistema de los nodos que invocan un modelo de lenguaje, en la
  versión vigente al cierre del desarrollo, salvo el del nodo de diálogo del agente elicitador, que
  se presenta en la ¡Error! No se encuentra el origen de la referencia.»
- **Debe:**
  - reparar la referencia (C-13);
  - incluir los prompts vigentes que el anexo anuncia y que hoy no aparecen.

  Las versiones están en `03-cifras.md`, sección 3, y los textos, en `prompts/<agente>/*.md`.
- **Opcional, en la Tabla 36:**
  - la «segunda opinión» del juez de N14, como verificación de un rechazo;
  - los «recorridos» de los escenarios en N8, como descomposición en pasos verificables.

## Corrección posterior al paso 15

### C-46 · Capítulos 1.6.4, 3.8, 5, 6.4, 6.5, 7 y 8

- **Lo que pasó:** el paso 15 terminó el 5 de noviembre, y `05-evaluacion-paso-15.md` trae el texto de estas secciones.
- **Regla:** donde las entradas C-29 a C-31 y C-35 a C-38 traten lo mismo que ese archivo, manda él.
- **También cambia en C-45, tabla de indicadores:** OE4 queda con los niveles del plan vigente aplicados. La comparación
  con desarrollo humano queda como trabajo futuro.

## Detalles de edición

### C-45 · Listas de tablas y de figuras, pp. 8 y 10

- **El problema:**
  - la lista de tablas conserva «TABLA 28. CUMPLIMIENTO DE LOS INDICADORES POR OBJETIVO
    ESPECÍFICO… ¡ERROR! MARCADOR NO DEFINIDO.»;
  - la de figuras, «FIGURA 9. PROMPT DE SISTEMA DEL NODO DE DIÁLOGO DEL AGENTE ELICITADOR…
    ¡ERROR! MARCADOR NO DEFINIDO.»

  Ninguna de las dos existe en el cuerpo. Por eso, desde ahí, la numeración de las listas va una
  por delante de las leyendas: en el cuerpo, la Tabla 28 es el formato de backlog y la Figura 9,
  la distribución del costo.
- **Las referencias del texto** («Tabla 30», «Tabla 32 del Anexo C», «Tabla 35 del Anexo E»,
  «Tabla 38 del Anexo H», etc.) **coinciden con las leyendas,** no con las listas.
- **Arreglo:**
  - decidir si se reinsertan la figura del prompt (C-13) y la tabla de indicadores;
  - después, actualizar los campos de ambas listas y de las referencias cruzadas.
- **Si se quiere reinsertar la tabla de indicadores** (requerimientos, Tabla 10):

  | Objetivo | Indicador | Estado |
  |---|---|---|
  | OE1 | 100 % del documento aprobado | Cumplido, con acta |
  | OE2 | 100 % del documento aprobado | Cumplido, con acta |
  | OE3 | 100 % del producto mínimo viable funcional | Cumplido: pasos 0 a 14 cerrados y 20 de 20 módulos validados |
  | OE4 | 90 % de aplicación de las pruebas | En curso: los niveles del plan se aplicaron; la comparación con el desarrollo manual y con un modelo único es el paso 15 |

  Que el equipo confirme estos estados antes de publicarlos.
